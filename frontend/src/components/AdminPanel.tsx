import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

interface User {
  id: number
  email: string
  is_active: boolean
  is_approved: boolean
  role: string
}

export default function AdminPanel() {
  const { user, logout } = useAuth()
  const [pendingUsers, setPendingUsers] = useState<User[]>([])
  const [allUsers, setAllUsers] = useState<User[]>([])
  const [stats, setStats] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'pending' | 'all' | 'stats'>('pending')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [userToReject, setUserToReject] = useState<{id: number, email: string} | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [pendingResponse, allUsersResponse, statsResponse] = await Promise.all([
        axios.get(`${API_BASE}/admin/pending`),
        axios.get(`${API_BASE}/admin/users`),
        axios.get(`${API_BASE}/admin/stats`)
      ])
      
      setPendingUsers(pendingResponse.data)
      setAllUsers(allUsersResponse.data)
      setStats(statsResponse.data)
    } catch (err: any) {
      setError('Failed to fetch data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const approveUser = async (userId: number) => {
    try {
      console.log(`🔄 Approving user ${userId}...`)
      const response = await axios.post(`${API_BASE}/admin/approve/${userId}`)
      console.log('✅ Approve response:', response.data)
      setSuccess('User approved successfully')
      await fetchData() // Refresh all data
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      console.error('❌ Approve error:', err)
      setError(`Failed to approve user: ${err.response?.data?.detail || err.message}`)
    }
  }

  const showRejectConfirmation = (userId: number, userEmail: string) => {
    setUserToReject({ id: userId, email: userEmail })
    setShowRejectModal(true)
  }

  const confirmRejectUser = async () => {
    if (!userToReject) return
    
    try {
      console.log(`🔄 Rejecting user ${userToReject.id}...`)
      const response = await axios.post(`${API_BASE}/admin/reject/${userToReject.id}`)
      console.log('✅ Reject response:', response.data)
      setSuccess('User rejected and deleted successfully')
      await fetchData() // Refresh all data
      setTimeout(() => setSuccess(''), 3000)
      setShowRejectModal(false)
      setUserToReject(null)
    } catch (err: any) {
      console.error('❌ Reject error:', err)
      setError(`Failed to reject user: ${err.response?.data?.detail || err.message}`)
    }
  }

  const cancelReject = () => {
    setShowRejectModal(false)
    setUserToReject(null)
  }

  const revokeUser = async (userId: number) => {
    try {
      console.log(`🔄 Revoking user ${userId}...`)
      const response = await axios.post(`${API_BASE}/admin/revoke/${userId}`)
      console.log('✅ Revoke response:', response.data)
      setSuccess('User access revoked successfully')
      await fetchData() // Refresh all data
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      console.error('❌ Revoke error:', err)
      setError(`Failed to revoke user: ${err.response?.data?.detail || err.message}`)
    }
  }

  const deleteUser = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return
    }
    
    try {
      await axios.delete(`${API_BASE}/admin/users/${userId}`)
      setSuccess('User deleted successfully')
      await fetchData() // Refresh all data
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError('Failed to delete user')
      console.error(err)
    }
  }

  if (loading) {
    return <div className="container">Loading...</div>
  }

  return (
    <div className="container">
      <div className="navbar">
        <div className="navbar-content">
          <h1>🔧 Admin Panel</h1>
          <div className="navbar-actions">
            <span>Welcome, {user?.email}</span>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3>📊 System Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ padding: '16px', backgroundColor: '#e8f4fd', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#0066cc' }}>{stats.total_users}</div>
              <div style={{ fontSize: '14px', color: '#666' }}>Total Users</div>
            </div>
            <div style={{ padding: '16px', backgroundColor: '#fff3cd', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#856404' }}>{stats.pending_approval}</div>
              <div style={{ fontSize: '14px', color: '#666' }}>Pending Approval</div>
            </div>
            <div style={{ padding: '16px', backgroundColor: '#d4edda', borderRadius: '8px', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#155724' }}>{stats.approved_users}</div>
              <div style={{ fontSize: '14px', color: '#666' }}>Approved Users</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="card">
        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', borderBottom: '1px solid #dee2e6' }}>
          <button
            onClick={() => setActiveTab('pending')}
            style={{
              padding: '12px 24px',
              border: 'none',
              backgroundColor: activeTab === 'pending' ? '#007bff' : 'transparent',
              color: activeTab === 'pending' ? 'white' : '#666',
              cursor: 'pointer',
              borderRadius: '6px 6px 0 0',
              fontWeight: '500'
            }}
          >
            ⏳ Pending Approvals ({pendingUsers.length})
          </button>
          <button
            onClick={() => setActiveTab('all')}
            style={{
              padding: '12px 24px',
              border: 'none',
              backgroundColor: activeTab === 'all' ? '#007bff' : 'transparent',
              color: activeTab === 'all' ? 'white' : '#666',
              cursor: 'pointer',
              borderRadius: '6px 6px 0 0',
              fontWeight: '500'
            }}
          >
            👥 All Users ({allUsers.length})
          </button>
        </div>

        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}

        {/* Pending Approvals Tab */}
        {activeTab === 'pending' && (
          <div>
            <h3>Pending User Approvals</h3>
            {pendingUsers.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>✅</div>
                <p>No pending user approvals.</p>
              </div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingUsers.map((user) => (
                    <tr key={user.id}>
                      <td>{user.email}</td>
                      <td>
                        <span style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 'bold',
                          backgroundColor: user.role === 'Admin' ? '#dc3545' : user.role === 'Interviewer' ? '#ffc107' : '#28a745',
                          color: 'white'
                        }}>
                          {user.role}
                        </span>
                      </td>
                      <td>
                        <span style={{ color: '#ffc107', fontWeight: 'bold' }}>⏳ Pending</span>
                      </td>
                      <td className="actions">
                        <button 
                          onClick={() => approveUser(user.id)}
                          className="btn-success"
                          style={{ marginRight: '8px' }}
                        >
                          ✅ Approve
                        </button>
                        <button 
                          onClick={() => showRejectConfirmation(user.id, user.email)}
                          className="btn-danger"
                        >
                          ❌ Reject & Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* All Users Tab */}
        {activeTab === 'all' && (
          <div>
            <h3>All Users Management</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {allUsers.map((user) => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        backgroundColor: user.role === 'Admin' ? '#dc3545' : user.role === 'Interviewer' ? '#ffc107' : '#28a745',
                        color: 'white'
                      }}>
                        {user.role}
                      </span>
                    </td>
                    <td>
                      {user.is_approved ? (
                        <span style={{ color: '#28a745', fontWeight: 'bold' }}>✅ Approved</span>
                      ) : (
                        <span style={{ color: '#ffc107', fontWeight: 'bold' }}>⏳ Pending</span>
                      )}
                    </td>
                    <td className="actions">
                      {!user.is_approved ? (
                        <>
                          <button 
                            onClick={() => approveUser(user.id)}
                            className="btn-success"
                            style={{ marginRight: '8px' }}
                          >
                            ✅ Approve
                          </button>
                          <button 
                            onClick={() => showRejectConfirmation(user.id, user.email)}
                            className="btn-danger"
                            style={{ marginRight: '8px' }}
                          >
                            ❌ Reject & Delete
                          </button>
                        </>
                      ) : (
                        <button 
                          onClick={() => revokeUser(user.id)}
                          className="btn-warning"
                          style={{ marginRight: '8px' }}
                        >
                          🔄 Revoke
                        </button>
                      )}
                      {user.id !== user?.id && (
                        <button 
                          onClick={() => deleteUser(user.id)}
                          className="btn-danger"
                        >
                          🗑️ Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rejection Confirmation Modal */}
      {showRejectModal && userToReject && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ 
            width: '450px', 
            padding: '30px',
            borderRadius: '10px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.3)'
          }}>
            <div style={{ textAlign: 'center', marginBottom: '25px' }}>
              <div style={{ 
                fontSize: '48px', 
                marginBottom: '15px',
                color: '#dc3545'
              }}>
                ⚠️
              </div>
              <h3 style={{ 
                margin: '0 0 10px 0', 
                color: '#dc3545',
                fontSize: '24px'
              }}>
                Confirm User Rejection
              </h3>
              <p style={{ 
                color: '#666', 
                fontSize: '16px',
                margin: '0 0 20px 0',
                lineHeight: '1.5'
              }}>
                Are you sure you want to reject this user?
              </p>
            </div>

            <div style={{ 
              backgroundColor: '#f8f9fa', 
              padding: '15px', 
              borderRadius: '8px',
              marginBottom: '25px',
              border: '1px solid #dee2e6'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#495057' }}>
                User Details:
              </div>
              <div style={{ color: '#6c757d', fontSize: '14px' }}>
                <strong>Email:</strong> {userToReject.email}
              </div>
              <div style={{ color: '#6c757d', fontSize: '14px', marginTop: '5px' }}>
                <strong>Action:</strong> Permanent account deletion
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#fff3cd', 
              padding: '15px', 
              borderRadius: '8px',
              marginBottom: '25px',
              border: '1px solid #ffeaa7'
            }}>
              <div style={{ 
                color: '#856404', 
                fontSize: '14px',
                fontWeight: 'bold',
                marginBottom: '8px'
              }}>
                ⚠️ This action cannot be undone!
              </div>
              <div style={{ color: '#856404', fontSize: '13px', lineHeight: '1.4' }}>
                The user account will be permanently deleted and they will no longer be able to access the system.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px' }}>
              <button 
                onClick={cancelReject}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => (e.target as HTMLButtonElement).style.backgroundColor = '#5a6268'}
                onMouseOut={(e) => (e.target as HTMLButtonElement).style.backgroundColor = '#6c757d'}
              >
                Cancel
              </button>
              <button 
                onClick={confirmRejectUser}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s'
                }}
                onMouseOver={(e) => (e.target as HTMLButtonElement).style.backgroundColor = '#c82333'}
                onMouseOut={(e) => (e.target as HTMLButtonElement).style.backgroundColor = '#dc3545'}
              >
                ❌ Reject & Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
