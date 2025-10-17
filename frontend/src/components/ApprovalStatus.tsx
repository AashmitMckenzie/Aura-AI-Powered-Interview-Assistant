import React, { useState } from 'react'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

interface ApprovalStatusProps {
  onClose: () => void
}

export default function ApprovalStatus({ onClose }: ApprovalStatusProps) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const checkStatus = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setLoading(true)
    setError('')
    setStatus(null)

    try {
      const response = await axios.get(`${API_BASE}/auth/check-approval/${email}`)
      setStatus(response.data)
    } catch (err: any) {
      setError('Failed to check approval status')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        maxWidth: '500px',
        width: '90%',
        maxHeight: '80vh',
        overflow: 'auto'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3>🔍 Check Approval Status</h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              color: '#666'
            }}
          >
            ×
          </button>
        </div>

        <form onSubmit={checkStatus}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              required
              style={{ width: '100%' }}
            />
          </div>

          <button type="submit" disabled={loading} style={{ width: '100%', marginBottom: '16px' }}>
            {loading ? 'Checking...' : 'Check Status'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {status && (
          <div style={{
            padding: '16px',
            borderRadius: '8px',
            backgroundColor: status.is_approved ? '#d4edda' : '#fff3cd',
            border: `1px solid ${status.is_approved ? '#c3e6cb' : '#ffeaa7'}`,
            marginTop: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '20px' }}>
                {status.is_approved ? '✅' : '⏳'}
              </span>
              <span style={{
                fontWeight: 'bold',
                color: status.is_approved ? '#155724' : '#856404'
              }}>
                {status.is_approved ? 'Account Approved' : 'Pending Approval'}
              </span>
            </div>
            <p style={{
              margin: 0,
              color: status.is_approved ? '#155724' : '#856404',
              fontSize: '14px'
            }}>
              {status.message}
            </p>
            {!status.is_approved && (
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#856404' }}>
                <p><strong>What happens next?</strong></p>
                <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                  <li>An administrator will review your account</li>
                  <li>You'll be notified once approved</li>
                  <li>You can then log in to the system</li>
                </ul>
              </div>
            )}
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
