import { useState, useEffect } from 'react'

export function useAuth() {
  const [isAuth, setIsAuth] = useState(false)
  const [role, setRole] = useState(null)

  useEffect(() => {
    const auth = localStorage.getItem("auth")
    const userRole = localStorage.getItem("role")
    
    setIsAuth(auth === "true")
    setRole(userRole)
  }, [])

  const login = (userRole) => {
    localStorage.setItem("auth", "true")
    localStorage.setItem("role", userRole)
    setIsAuth(true)
    setRole(userRole)
  }

  const logout = () => {
    localStorage.removeItem("auth")
    localStorage.removeItem("role")
    setIsAuth(false)
    setRole(null)
  }

  return { isAuth, role, login, logout }
}