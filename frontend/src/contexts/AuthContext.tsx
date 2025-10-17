import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

interface User {
  id: number
  email: string
  is_active: boolean
  is_approved: boolean
  role: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, role: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      // Set up axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      // Fetch user info from token
      fetchUserInfo()
    } else {
      setLoading(false)
    }
  }, [token])

  const fetchUserInfo = async () => {
    try {
      const response = await axios.get(`${API_BASE}/users/me`)
      setUser(response.data)
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      // If token is invalid, clear it
      setToken(null)
      localStorage.removeItem('token')
      delete axios.defaults.headers.common['Authorization']
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const params = new URLSearchParams()
      params.append('username', email)
      params.append('password', password)

      const response = await axios.post(`${API_BASE}/auth/login`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token } = response.data
      setToken(access_token)
      localStorage.setItem('token', access_token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      // Fetch user info after successful login
      await fetchUserInfo()
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  const signup = async (email: string, password: string, role: string) => {
    try {
      await axios.post(`${API_BASE}/auth/signup`, {
        email,
        password,
        role
      })
    } catch (error) {
      console.error('Signup failed:', error)
      throw error
    }
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
  }

  return (
    <AuthContext.Provider value={{ user, token, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
