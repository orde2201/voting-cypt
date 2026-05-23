import { useState } from "react"
import { useNavigate } from "react-router-dom"

const API_URL = "http://localhost:8000/login"

export default function Login({ onLoginSuccess }) {
  const [nim, setNim] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async () => {
    setLoading(true)
    
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nim, password })
      })

      const data = await res.json()

      if (data.success) {
        // PASTIKAN INI TERSIMPAN SEMUA
        localStorage.setItem("auth", "true")
        localStorage.setItem("role", data.status) // admin / student
        localStorage.setItem("nim", data.nim)     // ← PENTING! Simpan NIM
        
        console.log("Login berhasil, NIM tersimpan:", data.nim) // Debug
        
        // Panggil callback
        if (onLoginSuccess) {
          onLoginSuccess(data.nim, data.status)
        }
        
        navigate("/")
      } else {
        alert(data.message)
      }
    } catch (error) {
      console.error("Login error:", error)
      alert("Login gagal: " + error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Login</h1>

      <input
        placeholder="NIM"
        value={nim}
        onChange={(e) => setNim(e.target.value)}
      />

      <br />

      <input
        placeholder="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
      />

      <br />

      <button onClick={handleLogin} disabled={loading}>
        {loading ? "Loading..." : "Login"}
      </button>
    </div>
  )
}