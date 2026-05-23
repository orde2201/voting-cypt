import { useState } from "react"
import { useNavigate } from "react-router-dom"

const API_URL = "http://localhost:8000/login"

export default function Login() {
  const [nim, setNim] = useState("")
  const [password, setPassword] = useState("")
  const navigate = useNavigate()

  const handleLogin = async () => {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nim, password })
    })

    const data = await res.json()

    if (data.success) {
      localStorage.setItem("auth", "true")
      navigate("/")
    } else {
      alert(data.message)
    }
  }

  return (
    <div>
      <h1>Login</h1>

      <input
        placeholder="nim"
        onChange={(e) => setNim(e.target.value)}
      />

      <input
        placeholder="password"
        type="password"
        onChange={(e) => setPassword(e.target.value)}
      />

      <button onClick={handleLogin}>Login</button>
    </div>
  )
}