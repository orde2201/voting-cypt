import { Navigate } from "react-router-dom"

export default function AdminRoute({ children }) {
  const role = localStorage.getItem("role")
  const isAuth = localStorage.getItem("auth")

  // belum login
  if (!isAuth) {
    return <Navigate to="/login" replace />
  }

  // bukan admin
  if (role !== "admin") {
    return <h1>403 - Forbidden (Admin Only)</h1>
  }

  // kalau admin → boleh akses
  return children
}