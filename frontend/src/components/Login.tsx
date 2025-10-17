import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ApprovalStatus from './ApprovalStatus'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showApprovalStatus, setShowApprovalStatus] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Login failed'
      
      // Provide more specific error messages
      if (errorMessage.includes('not approved')) {
        setError('Your account is pending admin approval. Please wait for approval or contact an administrator.')
      } else if (errorMessage.includes('Invalid credentials')) {
        setError('Invalid email or password. Please check your credentials and try again.')
      } else {
        setError(errorMessage)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div style={{ maxWidth: '400px', margin: '50px auto' }}>
        <div className="card">
          <h2 style={{ marginBottom: '24px', textAlign: 'center' }}>Login</h2>
          
          {error && <div className="error">{error}</div>}
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <button type="submit" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
          
          <div style={{ textAlign: 'center', marginTop: '16px' }}>
            <p>Don't have an account? <Link to="/signup">Sign up</Link></p>
            <p style={{ marginTop: '8px' }}>
              <button
                type="button"
                onClick={() => setShowApprovalStatus(true)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#007bff',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  fontSize: '14px'
                }}
              >
                Check approval status
              </button>
            </p>
          </div>
        </div>
      </div>

      {showApprovalStatus && (
        <ApprovalStatus onClose={() => setShowApprovalStatus(false)} />
      )}
    </div>
  )
}
