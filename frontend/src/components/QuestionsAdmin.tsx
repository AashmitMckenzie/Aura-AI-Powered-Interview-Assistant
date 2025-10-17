import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

type Question = {
  id: number
  role: string
  level: string
  type: string
  question_text: string
}

const ROLES = [
  'Software Engineer', 'Data Scientist', 'DevOps Engineer', 'Product Manager',
  'Backend Engineer', 'Frontend Engineer', 'ML Engineer', 'QA Engineer'
]
const LEVELS = ['Junior', 'Mid', 'Senior']
const TYPES = ['Technical', 'Behavioral', 'System Design', 'Coding']

export default function QuestionsAdmin() {
  const [items, setItems] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // filters
  const [role, setRole] = useState('')
  const [level, setLevel] = useState('')
  const [qtype, setQtype] = useState('')
  const [q, setQ] = useState('')

  // form state
  const [editId, setEditId] = useState<number | null>(null)
  const [formRole, setFormRole] = useState('Software Engineer')
  const [formLevel, setFormLevel] = useState('Junior')
  const [formType, setFormType] = useState('Technical')
  const [formText, setFormText] = useState('')

  const fetchQuestions = async () => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, string> = {}
      if (role) params.role = role
      if (level) params.level = level
      if (qtype) params.type = qtype
      if (q) params.q = q
      const res = await axios.get(`${API_BASE}/questions/`, { params })
      setItems(res.data)
    } catch (e) {
      setError('Failed to load questions')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQuestions()
  }, [])

  const resetForm = () => {
    setEditId(null)
    setFormRole('Software Engineer')
    setFormLevel('Junior')
    setFormType('Technical')
    setFormText('')
  }

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editId) {
        await axios.put(`${API_BASE}/questions/${editId}`, {
          role: formRole,
          level: formLevel,
          type: formType,
          question_text: formText,
        })
      } else {
        await axios.post(`${API_BASE}/questions/`, {
          role: formRole,
          level: formLevel,
          type: formType,
          question_text: formText,
        })
      }
      resetForm()
      await fetchQuestions()
    } catch (e) {
      setError('Save failed')
      console.error(e)
    }
  }

  const handleEdit = (q: Question) => {
    setEditId(q.id)
    setFormRole(q.role)
    setFormLevel(q.level)
    setFormType(q.type)
    setFormText(q.question_text)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this question?')) return
    try {
      await axios.delete(`${API_BASE}/questions/${id}`)
      setItems(prev => prev.filter(x => x.id !== id))
    } catch (e) {
      setError('Delete failed')
      console.error(e)
    }
  }

  const count = useMemo(() => items.length, [items])

  return (
    <div className="container">
      <div className="card">
        <h2>Questions Admin</h2>
        {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}

        <div className="tabs" style={{ marginTop: 16 }}>
          <div className="tab active">Manage</div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <h3>Filters</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginTop: 12 }}>
            <select value={role} onChange={e => setRole(e.target.value)}>
              <option value="">All Roles</option>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <select value={level} onChange={e => setLevel(e.target.value)}>
              <option value="">All Levels</option>
              {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
            <select value={qtype} onChange={e => setQtype(e.target.value)}>
              <option value="">All Types</option>
              {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input placeholder="Search text" value={q} onChange={e => setQ(e.target.value)} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={fetchQuestions}>Apply</button>
              <button className="btn-secondary" onClick={() => { setRole(''); setLevel(''); setQtype(''); setQ(''); fetchQuestions() }}>Reset</button>
            </div>
          </div>
          <div style={{ marginTop: 8, color: '#666' }}>{count} results</div>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <h3>{editId ? 'Edit Question' : 'Add Question'}</h3>
          <form onSubmit={handleCreateOrUpdate} style={{ display: 'grid', gap: 12, marginTop: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              <select value={formRole} onChange={e => setFormRole(e.target.value)}>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              <select value={formLevel} onChange={e => setFormLevel(e.target.value)}>
                {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
              <select value={formType} onChange={e => setFormType(e.target.value)}>
                {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <textarea value={formText} onChange={e => setFormText(e.target.value)} placeholder="Question text" rows={3} style={{ width: '100%', padding: 8 }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit">{editId ? 'Update' : 'Create'}</button>
              {editId && <button type="button" className="btn-secondary" onClick={resetForm}>Cancel</button>}
            </div>
          </form>
        </div>

        <div className="card" style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: 16 }}>Loading...</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 180 }}>Role</th>
                  <th style={{ width: 120 }}>Level</th>
                  <th style={{ width: 160 }}>Type</th>
                  <th>Text</th>
                  <th style={{ width: 160 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.id}>
                    <td>{it.role}</td>
                    <td>{it.level}</td>
                    <td>{it.type}</td>
                    <td>{it.question_text}</td>
                    <td className="actions">
                      <button className="btn-secondary" onClick={() => handleEdit(it)}>Edit</button>
                      <button className="btn-danger" onClick={() => handleDelete(it.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}


