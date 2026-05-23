/**
 * APP.JSX - Main Application Component
 * 
 * Aplikasi Voting System dengan fitur:
 * - Autentikasi user (Login)
 * - Voting dengan RSA encryption + hashing
 * - Recap hasil voting (hanya untuk admin)
 * - Verifikasi integritas data vote
 * 
 * @version 2.0.0
 * @author Your Team
 */

import { useState, useEffect } from 'react'
import './App.css'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'

import Login from "./login"
import ProtectedRoute from "./ProtectedRoute"
import AdminRoute from "./AdminRoute"

// ================================================================
// MAIN APP COMPONENT
// ================================================================

/**
 * Komponen utama aplikasi yang menangani:
 * - State autentikasi global
 * - Routing antar halaman
 * - Navigasi menu (Vote, Recap, Login/Logout)
 * - Manajemen session (localStorage)
 */
function App() {
  // State management untuk autentikasi
  const [isAuth, setIsAuth] = useState(false)      // Status login (true/false)
  const [role, setRole] = useState(null)           // Role user: 'admin' atau 'student'
  const [userNim, setUserNim] = useState(null)     // NIM user yang sedang login
  const navigate = useNavigate()                    // Hook untuk navigasi programatik

  /**
   * Effect Hook: Cek status autentikasi saat aplikasi pertama kali dimuat
   * Membaca data dari localStorage untuk restore session
   * 
   * Dipanggil sekali saat component mount ([])
   */
  useEffect(() => {
    const checkAuth = () => {
      // Ambil data dari localStorage
      const auth = localStorage.getItem("auth")
      const userRole = localStorage.getItem("role")
      const nim = localStorage.getItem("nim")
      
      console.log("[App] Check Auth - NIM:", nim) // Debugging log
      
      // Update state berdasarkan data yang tersimpan
      setIsAuth(auth === "true")
      setRole(userRole)
      setUserNim(nim)
    }
    
    checkAuth() // Eksekusi pengecekan
  }, []) // Empty dependency array => hanya run sekali

  /**
   * Handle logout: Hapus semua data session dan redirect ke halaman login
   * 
   * Proses:
   * 1. Hapus semua item dari localStorage (auth, role, nim)
   * 2. Reset semua state ke nilai awal
   * 3. Redirect user ke halaman /login
   */
  const handleLogout = () => {
    // Clear localStorage
    localStorage.removeItem("auth")
    localStorage.removeItem("role")
    localStorage.removeItem("nim")
    
    // Reset state
    setIsAuth(false)
    setRole(null)
    setUserNim(null)
    
    // Redirect ke login page
    navigate("/login")
  }

  /**
   * Render komponen dengan JSX
   */
  return (
    <div style={{ padding: "20px" }}>
      {/* ===== NAVIGATION BAR ===== */}
      <nav style={{ marginBottom: "20px" }}>
        {/* Link ke halaman Vote - selalu tersedia untuk user yang sudah login */}
        <Link to="/" style={{ marginRight: "10px" }}>Vote</Link>
        
        {/* Link Recap - HANYA untuk admin (conditional rendering) */}
        {isAuth && role === "admin" && (
          <Link to="/recap" style={{ marginRight: "10px" }}>Recap</Link>
        )}
        
        {/* Conditional rendering untuk Login/Logout button */}
        {!isAuth ? (
          // Tampilkan link Login jika belum login
          <Link to="/login">Login</Link>
        ) : (
          // Tampilkan info user + logout button jika sudah login
          <div style={{ display: "inline", marginLeft: "10px" }}>
            <span style={{ marginRight: "10px" }}>
              👤 {userNim} ({role})  {/* Menampilkan NIM dan role user */}
            </span>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </nav>

      {/* ===== ROUTING CONFIGURATION ===== */}
      <Routes>
        {/* 
          Route: /login 
          - Bisa diakses semua orang (public)
          - Mengirim callback onLoginSuccess untuk update state global
        */}
        <Route path="/login" element={<Login onLoginSuccess={(nim, role) => {
          console.log("[App] Login success callback - NIM:", nim) // Debug
          setIsAuth(true)    // Set status login menjadi true
          setRole(role)      // Simpan role user (admin/student)
          setUserNim(nim)    // Simpan NIM user
          navigate("/")      // Redirect ke halaman utama (Vote)
        }} />} />
        
        {/* 
          Route: / (Vote Form)
          - Protected: Hanya user yang sudah login bisa akses
          - Mengirim userNim sebagai props ke VoteForm
        */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <VoteForm userNim={userNim} />
            </ProtectedRoute>
          }
        />

        {/* 
          Route: /recap (Hasil Voting)
          - Protected + Admin Only: Hanya admin yang bisa akses
          - Menampilkan hasil rekapitulasi suara
        */}
        <Route
          path="/recap"
          element={
            <AdminRoute>
              <Recap />
            </AdminRoute>
          }
        />
      </Routes>
    </div>
  )
}

// ================================================================
// VOTE FORM COMPONENT
// ================================================================

/**
 * Komponen Form Voting
 * 
 * Fitur:
 * - Menampilkan form vote untuk user yang sudah login
 * - NIM otomatis terisi dari session (disabled, tidak bisa diubah)
 * - Cek status vote sebelumnya (mencegah double voting)
 * - Validasi input (nama, NIM, pilihan kandidat)
 * - Komunikasi dengan backend API untuk submit vote
 * 
 * @param {Object} props
 * @param {string} props.userNim - NIM user yang login dari parent component
 */
function VoteForm({ userNim }) {
  // API Endpoints
  const API_VOTE = "http://localhost:8000/vote"                      // Endpoint submit vote
  const API_CHECK_VOTE = "http://localhost:8000/check-vote-status"  // Endpoint cek status vote

  // State management untuk form dan status
  const [formData, setFormData] = useState({
    nama: "",        // Nama lengkap voter
    nim: "",         // NIM (akan diisi otomatis dari userNim)
    kandidat: ""     // Pilihan kandidat (A, B, atau C)
  })
  const [hasVoted, setHasVoted] = useState(false)  // Status apakah sudah vote
  const [loading, setLoading] = useState(false)    // Status loading saat submit
  const [checking, setChecking] = useState(true)   // Status pengecekan vote sebelumnya

  /**
   * Debug: Log userNim yang diterima dari parent
   */
  useEffect(() => {
    console.log("[VoteForm] Received userNim:", userNim)
  }, [userNim])

  /**
   * Effect: Cek apakah user sudah pernah vote sebelumnya
   * 
   * Alur:
   * 1. Jika userNim belum ada, skip pengecekan
   * 2. Panggil API /check-vote-status/{nim}
   * 3. Jika sudah vote, set hasVoted = true (form tidak ditampilkan)
   * 4. Jika belum vote, form tetap ditampilkan
   */
  useEffect(() => {
    const checkVoteStatus = async () => {
      if (!userNim) {
        console.log("[VoteForm] No userNim, skipping vote status check")
        setChecking(false)
        return
      }

      try {
        console.log("[VoteForm] Checking vote status for NIM:", userNim)
        const res = await fetch(`${API_CHECK_VOTE}/${userNim}`)
        const data = await res.json()
        
        if (data.has_voted) {
          setHasVoted(true)  // User sudah vote, form tidak akan ditampilkan
        }
      } catch (err) {
        console.error("[VoteForm] Error checking vote status:", err)
      } finally {
        setChecking(false)  // Selesai pengecekan
      }
    }

    checkVoteStatus()
  }, [userNim]) // Re-run jika userNim berubah

  /**
   * Effect: Set NIM dari user yang login ke form
   * NIM bersifat readonly (tidak bisa diubah) untuk mencegah kecurangan
   */
  useEffect(() => {
    if (userNim) {
      console.log("[VoteForm] Setting NIM in form:", userNim)
      setFormData(prev => ({ ...prev, nim: userNim }))
    }
  }, [userNim])

  /**
   * Handle perubahan input form
   * 
   * @param {Event} e - Event dari input/select element
   * @note NIM tidak bisa diubah (disabled), jadi di-ignore
   */
  const handleChange = (e) => {
    if (e.target.name === "nim") return // NIM tidak boleh diubah
    
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  /**
   * Handle submit form vote
   * 
   * Proses:
   * 1. Prevent default form submission
   * 2. Set loading state true
   * 3. Kirim POST request ke /vote endpoint
   * 4. Handle response (success/error)
   * 5. Tampilkan alert sesuai hasil
   * 6. Reset form jika sukses
   */
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    console.log("[VoteForm] Submitting vote with data:", formData)

    try {
      // Kirim data ke backend
      const res = await fetch(API_VOTE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      })

      const data = await res.json()
      console.log("[VoteForm] Vote response:", data)

      if (data.success) {
        // Vote berhasil
        alert("✅ Vote berhasil dikirim!")
        setHasVoted(true)  // Mark sebagai sudah vote
        setFormData({ ...formData, nama: "", kandidat: "" }) // Reset nama dan kandidat
      } else {
        // Vote gagal - tampilkan pesan error dari server
        alert(`❌ Gagal voting: ${data.message || data.error || "Unknown error"}`)
      }

    } catch (err) {
      console.error("[VoteForm] Vote error:", err)
      alert("❌ Gagal mengirim vote: " + err.message)
    } finally {
      setLoading(false) // Selesai proses, matikan loading state
    }
  }

  // ===== RENDER CONDITIONAL =====
  
  // 1. Sedang melakukan pengecekan status vote
  if (checking) {
    return <h2>Loading...</h2>
  }

  // 2. User sudah melakukan vote sebelumnya
  if (hasVoted) {
    return (
      <div>
        <h1>✅ Terima Kasih!</h1>
        <p>Anda sudah melakukan vote dengan NIM: <strong>{userNim}</strong></p>
        <p>Vote Anda sudah tercatat dan tidak dapat diubah.</p>
      </div>
    )
  }

  // 3. User belum login (userNim tidak ada)
  if (!userNim) {
    return (
      <div>
        <h1>⚠️ Error</h1>
        <p>Anda belum login. Silahkan <Link to="/login">login</Link> terlebih dahulu.</p>
      </div>
    )
  }

  // 4. Tampilkan form vote (default state)
  return (
    <div>
      <h1>🗳️ Voting Form</h1>
      
      <form onSubmit={handleSubmit}>
        {/* Field: Nama Lengkap */}
        <div>
          <label>Nama Lengkap:</label>
          <br />
          <input
            name="nama"
            placeholder="Masukkan nama lengkap"
            value={formData.nama}
            onChange={handleChange}
            required  // Wajib diisi
            style={{ width: "300px", padding: "8px", marginTop: "5px" }}
          />
        </div>
        <br />

        {/* Field: NIM (readonly - tidak bisa diubah) */}
        <div>
          <label>NIM (tidak bisa diubah):</label>
          <br />
          <input
            name="nim"
            placeholder="NIM"
            value={formData.nim}
            disabled  // Tidak bisa diedit
            style={{ width: "300px", padding: "8px", marginTop: "5px", backgroundColor: "#f0f0f0" }}
          />
        </div>
        <br />

        {/* Field: Pilihan Kandidat (dropdown) */}
        <div>
          <label>Pilih Kandidat:</label>
          <br />
          <select
            name="kandidat"
            value={formData.kandidat}
            onChange={handleChange}
            required  // Wajib dipilih
            style={{ width: "300px", padding: "8px", marginTop: "5px" }}
          >
            <option value="">Pilih Kandidat</option>
            <option value="A">Kandidat A</option>
            <option value="B">Kandidat B</option>
            <option value="C">Kandidat C</option>
          </select>
        </div>

        <br />
        
        {/* Submit Button dengan loading state */}
        <button 
          type="submit" 
          disabled={loading}
          style={{ 
            padding: "10px 20px", 
            fontSize: "16px",
            backgroundColor: loading ? "#ccc" : "#007bff",  // Berubah warna saat loading
            color: "white",
            border: "none",
            borderRadius: "5px",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Memproses..." : "Submit Vote"}
        </button>
      </form>
    </div>
  )
}

// ================================================================
// RECAP COMPONENT (ADMIN ONLY)
// ================================================================

/**
 * Komponen Rekapitulasi Hasil Voting
 * 
 * Fitur:
 * - Hanya bisa diakses oleh ADMIN
 * - Menampilkan statistik perolehan suara
 * - Menampilkan vote yang valid, invalid, dan missing hash
 * - Menampilkan detail NIM yang bermasalah
 * - Refresh data secara manual
 * 
 * Keamanan:
 * - Hash verification: Memastikan data vote tidak dimanipulasi
 * - Integrity check: Membandingkan hash dengan database verify_vote
 */
function Recap() {
  const API_RECAP = "http://localhost:8000/recap"

  // State management
  const [data, setData] = useState(null)          // Data hasil recap dari backend
  const [loading, setLoading] = useState(false)   // Status loading saat fetch
  const [showInvalid, setShowInvalid] = useState(false) // Toggle detail error

  /**
   * Fetch data recap dari backend
   * 
   * Proses:
   * 1. Set loading true
   * 2. Panggil API /recap
   * 3. Simpan response ke state
   * 4. Log warning jika ada masalah (invalid/missing hash)
   * 5. Handle error jika gagal
   */
  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch(API_RECAP)
      const json = await res.json()
      setData(json)
      
      // Warning jika ditemukan vote yang bermasalah
      if (json.total_invalid > 0 || json.total_missing_hash > 0) {
        console.warn("[Recap] ⚠️ Ditemukan masalah:", json)
      }
    } catch (err) {
      console.error("[Recap] Error fetching data:", err)
      alert("Gagal mengambil data recap")
    } finally {
      setLoading(false)
    }
  }

  /**
   * Effect: Fetch data saat komponen pertama kali di-mount
   */
  useEffect(() => {
    fetchData()
  }, [])

  // ===== RENDER CONDITIONAL =====
  
  // 1. Loading state
  if (loading) {
    return <h2>Loading...</h2>
  }

  // 2. No data state
  if (!data) {
    return <h2>No data available</h2>
  }

  // 3. Error state dari backend
  if (data.error) {
    return (
      <div>
        <h1>📊 Hasil Voting (Admin Only)</h1>
        <div style={{ color: "red", border: "1px solid red", padding: "20px", borderRadius: "8px" }}>
          <h3>Error: {data.error}</h3>
        </div>
      </div>
    )
  }

  // 4. Tampilkan data recap
  return (
    <div>
      <h1>📊 Hasil Voting (Admin Only)</h1>

      {/* ===== SUMMARY CARDS ===== */}
      {/* Menampilkan statistik ringkas: Total, Valid, Invalid, Missing */}
      <div style={{ display: "flex", gap: "20px", marginBottom: "30px", flexWrap: "wrap" }}>
        <SummaryCard title="Total Vote" value={data.total_votes || 0} color="#3498db" />
        <SummaryCard title="Vote Valid" value={data.total_valid || 0} color="#2ecc71" />
        <SummaryCard title="Vote Invalid" value={data.total_invalid || 0} color="#e74c3c" />
        <SummaryCard title="Hash Missing" value={data.total_missing_hash || 0} color="#f39c12" />
      </div>

      {/* ===== PEROLEHAN SUARA ===== */}
      <h2>Perolehan Suara</h2>
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", marginBottom: "30px" }}>
        <Card label="Kandidat A" value={data.hasil?.A || 0} />
        <Card label="Kandidat B" value={data.hasil?.B || 0} />
        <Card label="Kandidat C" value={data.hasil?.C || 0} />
      </div>

      {/* ===== WARNING SECTION (Jika ada masalah) ===== */}
      {(data.total_invalid > 0 || data.total_missing_hash > 0) && (
        <div style={{ 
          border: "2px solid #e74c3c", 
          padding: "20px", 
          borderRadius: "8px", 
          marginBottom: "20px",
          backgroundColor: "#fee"
        }}>
          <h3 style={{ color: "#e74c3c" }}>⚠️ Peringatan: Ditemukan Masalah!</h3>
          <button 
            onClick={() => setShowInvalid(!showInvalid)}
            style={{ marginBottom: "10px", padding: "5px 10px", cursor: "pointer" }}
          >
            {showInvalid ? "Sembunyikan" : "Lihat Detail"}
          </button>
          
          {/* Tampilkan detail error jika toggle aktif */}
          {showInvalid && (
            <div style={{ marginTop: "10px" }}>
              {/* Hash Mismatch - Hash tidak cocok (data telah dimanipulasi) */}
              {data.invalid_votes?.length > 0 && (
                <>
                  <h4>❌ Vote Invalid (Hash Mismatch):</h4>
                  <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "20px" }}>
                    <thead>
                      <tr>
                        <th style={{ border: "1px solid #ddd", padding: "8px", textAlign: "left" }}>NIM</th>
                        <th style={{ border: "1px solid #ddd", padding: "8px", textAlign: "left" }}>Alasan</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.invalid_votes?.map((inv, idx) => (
                        <tr key={idx}>
                          <td style={{ border: "1px solid #ddd", padding: "8px" }}>{inv.nim}</td>
                          <td style={{ border: "1px solid #ddd", padding: "8px" }}>{inv.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
              
              {/* Missing Hash - Hash tidak ditemukan di database verify_vote */}
              {data.missing_hash?.length > 0 && (
                <>
                  <h4>⚠️ Hash Tidak Ditemukan:</h4>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr>
                        <th style={{ border: "1px solid #ddd", padding: "8px", textAlign: "left" }}>NIM</th>
                        <th style={{ border: "1px solid #ddd", padding: "8px", textAlign: "left" }}>Alasan</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.missing_hash?.map((miss, idx) => (
                        <tr key={idx}>
                          <td style={{ border: "1px solid #ddd", padding: "8px" }}>{miss.nim}</td>
                          <td style={{ border: "1px solid #ddd", padding: "8px" }}>{miss.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ===== REFRESH BUTTON ===== */}
      <button 
        onClick={fetchData} 
        disabled={loading}
        style={{ 
          marginTop: "20px", 
          padding: "10px 20px",
          backgroundColor: "#3498db",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: loading ? "not-allowed" : "pointer"
        }}
      >
        {loading ? "Refreshing..." : "🔄 Refresh Data"}
      </button>
    </div>
  )
}

// ================================================================
// UI COMPONENTS (Presentational)
// ================================================================

/**
 * Komponen SummaryCard - Menampilkan kartu statistik ringkas
 * 
 * @param {Object} props
 * @param {string} props.title - Judul kartu (Total Vote, Vote Valid, etc)
 * @param {number} props.value - Nilai statistik
 * @param {string} props.color - Warna border dan teks
 */
function SummaryCard({ title, value, color }) {
  return (
    <div style={{ 
      border: `2px solid ${color}`, 
      padding: "20px", 
      borderRadius: "8px", 
      minWidth: "120px", 
      textAlign: "center",
      backgroundColor: `${color}10`  // Warna background dengan opacity 10%
    }}>
      <h3 style={{ color: color, margin: 0 }}>{title}</h3>
      <h1 style={{ margin: "10px 0 0 0", color: color }}>{value}</h1>
    </div>
  )
}

/**
 * Komponen Card - Menampilkan perolehan suara per kandidat
 * 
 * @param {Object} props
 * @param {string} props.label - Nama kandidat (Kandidat A, B, C)
 * @param {number} props.value - Jumlah suara yang diperoleh
 */
function Card({ label, value }) {
  return (
    <div style={{ 
      border: "1px solid #ddd", 
      padding: "20px", 
      borderRadius: "8px", 
      minWidth: "120px", 
      textAlign: "center",
      backgroundColor: "#f5f5f5"
    }}>
      <h3>{label}</h3>
      <h1 style={{ color: "#2c3e50" }}>{value}</h1>
    </div>
  )
}

// ================================================================
// EXPORT
// ================================================================

export default App