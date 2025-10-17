import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './components/Login'
import Signup from './components/Signup'
import AdminPanel from './components/AdminPanel'
import QuestionsAdmin from './components/QuestionsAdmin'
import Dashboard from './components/Dashboard'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/admin" element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/questions-admin" element={<ProtectedRoute><QuestionsAdmin /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    </AuthProvider>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  
  if (loading) {
    return <div className="container">Loading...</div>
  }
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

export default App
