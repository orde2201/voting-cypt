import { useState, useEffect } from 'react'
import './App.css'
import { Routes, Route, Link } from 'react-router-dom'

import Login from "./login"
import ProtectedRoute from "./ProtectedRoute"

const API_URL = "http://localhost:8000"

function App() {
  return (
    <div style={{ padding: "20px" }}>
      <nav style={{ marginBottom: "20px" }}>
        <Link to="/" style={{ marginRight: "10px" }}>Vote</Link>
        <Link to="/recap">Recap</Link>
        <Link to="/login" style={{ marginLeft: "10px" }}>Login</Link>
      </nav>

      <Routes>
        {/* LOGIN PAGE (bebas akses) */}
        <Route path="/login" element={<Login />} />

        {/* PROTECTED ROUTES */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <VoteForm />
            </ProtectedRoute>
          }
        />

        <Route
          path="/recap"
          element={
            <ProtectedRoute>
              <Recap />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  )
}

/* ================= VOTE ================= */
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

      alert("Vote berhasil dikirim")

    } catch (err) {
      console.error(err)
      alert("Gagal")
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
        />
        <br />

        <input
          name="nim"
          placeholder="NIM"
          value={formData.nim}
          onChange={handleChange}
        />
        <br />

        <select
          name="kandidat"
          value={formData.kandidat}
          onChange={handleChange}
        >
          <option value="">Pilih</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>

        <br />
        <button type="submit">Submit</button>
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
      <h1>📊 Hasil Voting</h1>

      <h2>Total Vote: {data.total}</h2>

      <div style={{ display: "flex", gap: "20px" }}>
        <Card label="A" value={data.hasil.A || 0} />
        <Card label="B" value={data.hasil.B || 0} />
        <Card label="C" value={data.hasil.C || 0} />
      </div>

      <button onClick={fetchData}>Refresh</button>
    </div>
  )
}

function Card({ label, value }) {
  return (
    <div style={{ border: "1px solid black", padding: "10px" }}>
      <h3>{label}</h3>
      <h1>{value}</h1>
    </div>
  )
}

export default App