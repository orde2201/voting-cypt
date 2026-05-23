import { useState, useEffect } from 'react'
import './App.css'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'

import Login from "./login"
import ProtectedRoute from "./ProtectedRoute"
import AdminRoute from "./AdminRoute"

function App() {
  const [isAuth, setIsAuth] = useState(false)
  const [role, setRole] = useState(null)
  const [userNim, setUserNim] = useState(null) // Simpan NIM user yang login
  const navigate = useNavigate()

  // Cek localStorage saat component mount
  useEffect(() => {
    const checkAuth = () => {
      const auth = localStorage.getItem("auth")
      const userRole = localStorage.getItem("role")
      const nim = localStorage.getItem("nim")
      
      setIsAuth(auth === "true")
      setRole(userRole)
      setUserNim(nim)
    }
    
    checkAuth()
  }, [])

  // Fungsi untuk logout
  const handleLogout = () => {
    localStorage.removeItem("auth")
    localStorage.removeItem("role")
    localStorage.removeItem("nim")
    setIsAuth(false)
    setRole(null)
    setUserNim(null)
    navigate("/login")
  }

  return (
    <div style={{ padding: "20px" }}>
      <nav style={{ marginBottom: "20px" }}>
        <Link to="/" style={{ marginRight: "10px" }}>Vote</Link>
        
        {/* Hanya admin yang bisa lihat link Recap */}
        {isAuth && role === "admin" && (
          <Link to="/recap" style={{ marginRight: "10px" }}>Recap</Link>
        )}
        
        {!isAuth ? (
          <Link to="/login">Login</Link>
        ) : (
          <div style={{ display: "inline", marginLeft: "10px" }}>
            <span style={{ marginRight: "10px" }}>
              👤 {userNim} ({role})
            </span>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </nav>

      <Routes>
        <Route path="/login" element={<Login onLoginSuccess={(nim, role) => {
          // Update state setelah login berhasil
          setIsAuth(true)
          setRole(role)
          setUserNim(nim)
          navigate("/")
        }} />} />
        
        {/* Route untuk voting - semua user yang sudah login bisa akses */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <VoteForm userNim={userNim} />
            </ProtectedRoute>
          }
        />

        {/* Route untuk recap - HANYA ADMIN yang bisa akses */}
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

/* ================= VOTE FORM ================= */
function VoteForm({ userNim }) {
  const API_VOTE = "http://localhost:8000/vote"
  const API_CHECK_VOTE = "http://localhost:8000/check-vote-status"

  const [formData, setFormData] = useState({
    nama: "",
    nim: "",
    kandidat: ""
  })
  const [hasVoted, setHasVoted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)

  // Cek apakah user sudah pernah vote
  useEffect(() => {
    const checkVoteStatus = async () => {
      if (!userNim) {
        setChecking(false)
        return
      }

      try {
        const res = await fetch(`${API_CHECK_VOTE}/${userNim}`)
        const data = await res.json()
        
        if (data.has_voted) {
          setHasVoted(true)
        }
      } catch (err) {
        console.error("Error checking vote status:", err)
      } finally {
        setChecking(false)
      }
    }

    checkVoteStatus()
  }, [userNim])

  // Set NIM dari user yang login (tidak bisa diubah)
  useEffect(() => {
    if (userNim) {
      setFormData(prev => ({ ...prev, nim: userNim }))
    }
  }, [userNim])

  const handleChange = (e) => {
    // NIM tidak bisa diubah, hanya field lain yang bisa
    if (e.target.name === "nim") return
    
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const res = await fetch(API_VOTE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      })

      const data = await res.json()
      console.log(data)

      if (data.success) {
        alert("✅ Vote berhasil dikirim!")
        setHasVoted(true)
        setFormData({ ...formData, nama: "", kandidat: "" })
      } else {
        alert(`❌ Gagal voting: ${data.message || data.error || "Unknown error"}`)
      }

    } catch (err) {
      console.error(err)
      alert("❌ Gagal mengirim vote: " + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (checking) {
    return <h2>Loading...</h2>
  }

  if (hasVoted) {
    return (
      <div>
        <h1>✅ Terima Kasih!</h1>
        <p>Anda sudah melakukan vote dengan NIM: <strong>{userNim}</strong></p>
        <p>Vote Anda sudah tercatat dan tidak dapat diubah.</p>
      </div>
    )
  }

  return (
    <div>
      <h1>🗳️ Voting Form</h1>
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>Nama Lengkap:</label>
          <br />
          <input
            name="nama"
            placeholder="Masukkan nama lengkap"
            value={formData.nama}
            onChange={handleChange}
            required
            style={{ width: "300px", padding: "8px", marginTop: "5px" }}
          />
        </div>
        <br />

        <div>
          <label>NIM (tidak bisa diubah):</label>
          <br />
          <input
            name="nim"
            placeholder="NIM"
            value={formData.nim}
            disabled
            style={{ width: "300px", padding: "8px", marginTop: "5px", backgroundColor: "#f0f0f0" }}
          />
        </div>
        <br />

        <div>
          <label>Pilih Kandidat:</label>
          <br />
          <select
            name="kandidat"
            value={formData.kandidat}
            onChange={handleChange}
            required
            style={{ width: "300px", padding: "8px", marginTop: "5px" }}
          >
            <option value="">Pilih Kandidat</option>
            <option value="A">Kandidat A</option>
            <option value="B">Kandidat B</option>
            <option value="C">Kandidat C</option>
          </select>
        </div>

        <br />
        <button 
          type="submit" 
          disabled={loading}
          style={{ 
            padding: "10px 20px", 
            fontSize: "16px",
            backgroundColor: loading ? "#ccc" : "#007bff",
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

/* ================= RECAP ================= */
function Recap() {
  const API_RECAP = "http://localhost:8000/recap"

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showInvalid, setShowInvalid] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch(API_RECAP)
      const json = await res.json()
      setData(json)
      
      // Jika ada invalid votes, tampilkan warning
      if (json.total_invalid > 0) {
        console.warn("⚠️ Ditemukan vote yang tidak valid:", json.invalid_votes)
      }
    } catch (err) {
      console.error(err)
      alert("Gagal mengambil data recap")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) {
    return <h2>Loading...</h2>
  }

  if (!data) {
    return <h2>No data available</h2>
  }

  // Jika ada error dari backend
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

  return (
    <div>
      <h1>📊 Hasil Voting (Admin Only)</h1>

      {/* Summary Cards */}
      <div style={{ display: "flex", gap: "20px", marginBottom: "30px", flexWrap: "wrap" }}>
        <SummaryCard title="Total Vote" value={data.total_votes || 0} color="#3498db" />
        <SummaryCard title="Vote Valid" value={data.total_valid || 0} color="#2ecc71" />
        <SummaryCard title="Vote Invalid" value={data.total_invalid || 0} color="#e74c3c" />
      </div>

      {/* Hasil Kandidat */}
      <h2>Perolehan Suara</h2>
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", marginBottom: "30px" }}>
        <Card label="Kandidat A" value={data.hasil?.A || 0} />
        <Card label="Kandidat B" value={data.hasil?.B || 0} />
        <Card label="Kandidat C" value={data.hasil?.C || 0} />
      </div>

      {/* Warning jika ada invalid votes */}
      {data.total_invalid > 0 && (
        <div style={{ 
          border: "2px solid #e74c3c", 
          padding: "20px", 
          borderRadius: "8px", 
          marginBottom: "20px",
          backgroundColor: "#fee"
        }}>
          <h3 style={{ color: "#e74c3c" }}>⚠️ Peringatan: Ditemukan {data.total_invalid} Vote Tidak Valid!</h3>
          <button 
            onClick={() => setShowInvalid(!showInvalid)}
            style={{ marginBottom: "10px", padding: "5px 10px", cursor: "pointer" }}
          >
            {showInvalid ? "Sembunyikan" : "Lihat Detail"}
          </button>
          
          {showInvalid && (
            <div style={{ marginTop: "10px" }}>
              <h4>Daftar NIM yang bermasalah:</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
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
            </div>
          )}
        </div>
      )}

      {/* Informasi tambahan */}
      <div style={{ 
        border: "1px solid #ddd", 
        padding: "15px", 
        borderRadius: "8px", 
        marginTop: "20px",
        backgroundColor: "#f9f9f9"
      }}>
        <h4>📋 Informasi:</h4>
        <ul>
          <li>Total vote terdaftar: {data.total_votes || 0}</li>
          <li>Vote yang berhasil didekripsi: {data.total_valid || 0}</li>
          <li>Vote yang gagal/gagal: {data.total_invalid || 0}</li>
        </ul>
      </div>

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

function SummaryCard({ title, value, color }) {
  return (
    <div style={{ 
      border: `2px solid ${color}`, 
      padding: "20px", 
      borderRadius: "8px", 
      minWidth: "120px", 
      textAlign: "center",
      backgroundColor: `${color}10`
    }}>
      <h3 style={{ color: color, margin: 0 }}>{title}</h3>
      <h1 style={{ margin: "10px 0 0 0", color: color }}>{value}</h1>
    </div>
  )
}

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

export default App