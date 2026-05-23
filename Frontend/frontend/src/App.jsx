import { useState, useEffect } from 'react'
import './App.css'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'

import Login from "./login"
import ProtectedRoute from "./ProtectedRoute"
import AdminRoute from "./AdminRoute"

function App() {
  const [isAuth, setIsAuth] = useState(false)
  const [role, setRole] = useState(null)
  const navigate = useNavigate()

  // Cek localStorage saat component mount
  useEffect(() => {
    const checkAuth = () => {
      const auth = localStorage.getItem("auth")
      const userRole = localStorage.getItem("role")
      
      setIsAuth(auth === "true")
      setRole(userRole)
    }
    
    checkAuth()
  }, [])

  // Fungsi untuk logout
  const handleLogout = () => {
    localStorage.removeItem("auth")
    localStorage.removeItem("role")
    setIsAuth(false)
    setRole(null)
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
          <button onClick={handleLogout} style={{ marginLeft: "10px" }}>
            Logout ({role})
          </button>
        )}
      </nav>

      <Routes>
        <Route path="/login" element={<Login onLoginSuccess={() => {
          // Update state setelah login berhasil
          setIsAuth(true)
          setRole(localStorage.getItem("role"))
          navigate("/")
        }} />} />
        
        {/* Route untuk voting - semua user yang sudah login bisa akses */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <VoteForm />
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
function VoteForm() {
  const API_VOTE = "http://localhost:8000/vote"

  const [formData, setFormData] = useState({
    nama: "",
    nim: "",
    kandidat: ""
  })

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const res = await fetch(API_VOTE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      })

      const data = await res.json()
      console.log(data)

      if (data.success) {
        alert("Vote berhasil dikirim")
        setFormData({ nama: "", nim: "", kandidat: "" })
      } else {
        alert(data.message || "Gagal voting")
      }

    } catch (err) {
      console.error(err)
      alert("Gagal mengirim vote")
    }
  }

  return (
    <div>
      <h1>Voting Form</h1>

      <form onSubmit={handleSubmit}>
        <input
          name="nama"
          placeholder="Nama"
          value={formData.nama}
          onChange={handleChange}
          required
        />
        <br />

        <input
          name="nim"
          placeholder="NIM"
          value={formData.nim}
          onChange={handleChange}
          required
        />
        <br />

        <select
          name="kandidat"
          value={formData.kandidat}
          onChange={handleChange}
          required
        >
          <option value="">Pilih Kandidat</option>
          <option value="A">Kandidat A</option>
          <option value="B">Kandidat B</option>
          <option value="C">Kandidat C</option>
        </select>

        <br />
        <button type="submit">Submit Vote</button>
      </form>
    </div>
  )
}

/* ================= RECAP ================= */
function Recap() {
  const API_RECAP = "http://localhost:8000/recap"

  const [data, setData] = useState(null)

  const fetchData = async () => {
    try {
      const res = await fetch(API_RECAP)
      const json = await res.json()
      setData(json)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (!data) {
    return <h2>Loading...</h2>
  }

  return (
    <div>
      <h1>📊 Hasil Voting (Admin Only)</h1>

      <h2>Total Vote: {data.total}</h2>

      <div style={{ display: "flex", gap: "20px" }}>
        <Card label="Kandidat A" value={data.hasil?.A || 0} />
        <Card label="Kandidat B" value={data.hasil?.B || 0} />
        <Card label="Kandidat C" value={data.hasil?.C || 0} />
      </div>

      <button onClick={fetchData}>Refresh Data</button>
    </div>
  )
}

function Card({ label, value }) {
  return (
    <div style={{ border: "1px solid black", padding: "20px", borderRadius: "8px", minWidth: "100px", textAlign: "center" }}>
      <h3>{label}</h3>
      <h1>{value}</h1>
    </div>
  )
}

export default App