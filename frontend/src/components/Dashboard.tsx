import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'

const API_BASE = 'http://127.0.0.1:8000'

// Type definitions remain the same
type TranscriptItem = {
  timestamp_ms: number
  text: string
  sentiment_label?: string
  sentiment_score?: string
  bias_flagged?: boolean
  sentiment_analysis?: {
    label: string
    confidence: number
    polarity_score: number
    explanation?: string
  }
  bias_analysis?: {
    is_biased: boolean
    bias_score: number
    bias_type?: string
    explanation?: string
    suggestions?: string[]
  }
}

type QuestionSelectorQuestion = {
  id: string
  question_number: number
  main_role: string
  sub_role: string
  difficulty: string
  question: string
  source_file: string
  rating?: number
  notes?: string
}

type QuestionSession = {
  questions: QuestionSelectorQuestion[]
  total_questions: number
  difficulty_distribution: Record<string, number>
  session_id: string
}

interface UnifiedAnalysisResponse {
  has_issues: boolean;
  overall_score: number;
  sentiment: {
    label: string;
    confidence: number;
    scores: {
      pos: number;
      neu: number;
      neg: number;
      compound: number;
    };
    status: string;
  };
  bias_detection: {
    is_biased: boolean;
    confidence: number;
    bias_score: number;
    categories: Array<{
      category: string;
      keyword: string;
      context: string;
      confidence: number;
      weight: number;
      description: string;
    }>;
    status: string;
  };
  insights: string[];
  recommendations: string[];
  flagged_items: Array<{
    type: string;
    severity: string;
    confidence: number;
    description: string;
    timestamp: string;
  }>;
  processing_time_ms: number;
  timestamp: string;
}

type QuestionMetadata = {
  main_roles: string[]
  sub_roles_by_main: Record<string, string[]>
  difficulty_levels: string[]
  total_questions: number
}

// Helper functions
const getRatingDescription = (rating: number): string => {
  switch (rating) {
    case 1: return 'Poor - No understanding or incorrect approach'
    case 2: return 'Below Average - Limited understanding with major gaps'
    case 3: return 'Average - Basic understanding with some gaps'
    case 4: return 'Good - Solid understanding with minor gaps'
    case 5: return 'Excellent - Complete understanding with insights'
    default: return 'Not rated'
  }
}

const getSentimentIcon = (label: string): string => {
  switch (label) {
    case 'POSITIVE': return '📈'
    case 'NEGATIVE': return '📉'
    default: return '📊'
  }
}

const getSentimentColor = (label: string): string => {
  switch (label) {
    case 'POSITIVE': return '#28a745'
    case 'NEGATIVE': return '#dc3545'
    default: return '#007bff'
  }
}


const formatTime = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

// Reusable Components
const Navbar = ({ user, logout }: { user: any; logout: () => void }) => (
  <div className="navbar">
    <div className="navbar-content">
      <h1>🎤 Live AI Analysis Dashboard</h1>
      <div className="navbar-actions">
        <span>Welcome, {user?.email}</span>
        {user?.role === 'Admin' && (
          <Link to="/admin" className="btn btn-secondary" style={{ marginRight: '10px' }}>
            Admin Panel
          </Link>
        )}
        <button onClick={logout} className="btn-secondary">Logout</button>
      </div>
    </div>
  </div>
)

const QuestionRatingForm = ({ 
  question, 
  onSave, 
  onCancel 
}: { 
  question: QuestionSelectorQuestion
  onSave: (questionId: string, rating: number, notes: string) => void
  onCancel: () => void 
}) => {
  const [rating, setRating] = useState(question.rating || 0)
  const [notes, setNotes] = useState(question.notes || '')

  const handleSave = () => {
    if (rating > 0) {
      onSave(question.id, rating, notes)
    }
  }

  return (
    <div style={{
      backgroundColor: '#f8f9fa',
      padding: '12px',
      borderRadius: '6px',
      border: '1px solid #dee2e6'
    }}>
      <div style={{ marginBottom: '8px' }}>
        <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>
          Rate the candidate's answer (1-5):
        </label>
        <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
          {[1,2,3,4,5].map(star => (
            <button
              key={star}
              onClick={() => setRating(star)}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                fontSize: '20px',
                color: star <= rating ? '#ffc107' : '#e9ecef',
                cursor: 'pointer',
                padding: '2px'
              }}
            >
              ★
            </button>
          ))}
          <span style={{ fontSize: '12px', marginLeft: '8px', alignSelf: 'center' }}>
            {rating > 0 && `${rating}/5 - ${getRatingDescription(rating)}`}
          </span>
        </div>
      </div>
      
      <div style={{ marginBottom: '12px' }}>
        <label style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', display: 'block' }}>
          Notes (optional):
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add any notes about the candidate's answer..."
          style={{
            width: '100%',
            padding: '6px',
            borderRadius: '4px',
            border: '1px solid #ced4da',
            fontSize: '12px',
            minHeight: '60px',
            resize: 'vertical'
          }}
        />
      </div>
      
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={handleSave}
          disabled={rating === 0}
          style={{
            backgroundColor: rating > 0 ? '#28a745' : '#6c757d',
            color: 'white',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: rating > 0 ? 'pointer' : 'not-allowed'
          }}
        >
          Save Rating
        </button>
        <button
          onClick={onCancel}
          style={{
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

const QuestionPerformanceSummary = ({ questionsAsked }: { questionsAsked: QuestionSelectorQuestion[] }) => {
  const ratedQuestions = questionsAsked.filter(q => q.rating)
  if (ratedQuestions.length === 0) return null

  const totalRating = ratedQuestions.reduce((sum, q) => sum + (q.rating || 0), 0)
  const averageRating = totalRating / ratedQuestions.length

  const performanceLevel = averageRating >= 4.5 ? 'Excellent' :
                         averageRating >= 3.5 ? 'Good' :
                         averageRating >= 2.5 ? 'Average' :
                         averageRating >= 1.5 ? 'Below Average' : 'Poor'

  return (
    <div style={{
      backgroundColor: 'white',
      padding: '12px',
      borderRadius: '6px',
      marginBottom: '16px',
      border: '1px solid #c3e6cb'
    }}>
      <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#155724', marginBottom: '8px' }}>
        📊 Performance Summary
      </div>
      <div style={{ fontSize: '12px', color: '#155724' }}>
        Average Rating: <strong>{averageRating.toFixed(1)}/5</strong> ({performanceLevel}) • 
        Rated: {ratedQuestions.length}/{questionsAsked.length} questions
      </div>
    </div>
  )
}

const QuestionSelector = ({
  questionMetadata,
  selectedMainRole,
  selectedSubRole,
  selectedDifficulties,
  numQuestions,
  showQuestionSelector,
  questionSession,
  questionsAsked,
  editingQuestion,
  isGeneratingQuestions,
  onMainRoleChange,
  onSubRoleChange,
  onDifficultyToggle,
  onNumQuestionsChange,
  onToggleSelector,
  onGenerateQuestions,
  onAddQuestionToSession,
  onUpdateQuestionRating,
  onSetEditingQuestion
}: {
  questionMetadata: QuestionMetadata | null
  selectedMainRole: string
  selectedSubRole: string
  selectedDifficulties: string[]
  numQuestions: number
  showQuestionSelector: boolean
  questionSession: QuestionSession | null
  questionsAsked: QuestionSelectorQuestion[]
  editingQuestion: string | null
  isGeneratingQuestions: boolean
  onMainRoleChange: (role: string) => void
  onSubRoleChange: (role: string) => void
  onDifficultyToggle: (difficulty: string) => void
  onNumQuestionsChange: (num: number) => void
  onToggleSelector: () => void
  onGenerateQuestions: () => void
  onAddQuestionToSession: (question: QuestionSelectorQuestion) => void
  onUpdateQuestionRating: (questionId: string, rating: number, notes: string) => void
  onSetEditingQuestion: (questionId: string | null) => void
}) => (
  <div className="card">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <h2>🎯 Interview Question Selector</h2>
      <button
        onClick={onToggleSelector}
        style={{
          backgroundColor: showQuestionSelector ? '#dc3545' : '#007bff',
          color: 'white',
          border: 'none',
          padding: '8px 16px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '14px'
        }}
      >
        {showQuestionSelector ? 'Hide Selector' : 'Show Selector'}
      </button>
    </div>

    {showQuestionSelector && questionMetadata && (
      <div>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          Select your interview criteria and generate balanced questions for your session.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>
              Main Role
            </label>
            <select
              value={selectedMainRole}
              onChange={(e) => onMainRoleChange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ced4da',
                fontSize: '14px'
              }}
            >
              <option value="">Select Main Role</option>
              {questionMetadata.main_roles.map(role => (
                <option key={role} value={role}>{role}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>
              Sub Role
            </label>
            <select
              value={selectedSubRole}
              onChange={(e) => onSubRoleChange(e.target.value)}
              disabled={!selectedMainRole}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ced4da',
                fontSize: '14px',
                backgroundColor: !selectedMainRole ? '#f8f9fa' : 'white'
              }}
            >
              <option value="">Any Sub Role</option>
              {selectedMainRole && questionMetadata.sub_roles_by_main[selectedMainRole]?.map(role => (
                <option key={role} value={role}>{role}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>
              Difficulty Levels * (Select one or more)
            </label>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {questionMetadata.difficulty_levels.map(level => (
                <label key={level} style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '6px',
                  cursor: 'pointer',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  backgroundColor: selectedDifficulties.includes(level) ? '#e3f2fd' : '#f8f9fa',
                  border: selectedDifficulties.includes(level) ? '2px solid #2196f3' : '2px solid #dee2e6',
                  transition: 'all 0.2s ease'
                }}>
                  <input
                    type="checkbox"
                    checked={selectedDifficulties.includes(level)}
                    onChange={() => onDifficultyToggle(level)}
                    style={{ margin: 0 }}
                  />
                  <span style={{ 
                    fontSize: '14px', 
                    fontWeight: selectedDifficulties.includes(level) ? 'bold' : 'normal',
                    color: selectedDifficulties.includes(level) ? '#1976d2' : '#495057'
                  }}>
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </span>
                </label>
              ))}
            </div>
            {selectedDifficulties.length > 0 && (
              <div style={{ 
                marginTop: '8px', 
                fontSize: '12px', 
                color: '#28a745',
                fontWeight: 'bold'
              }}>
                Selected: {selectedDifficulties.join(', ')}
              </div>
            )}
          </div>

          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '8px' }}>
              Number of Questions
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={numQuestions}
              onChange={(e) => onNumQuestionsChange(parseInt(e.target.value) || 5)}
              style={{
                width: '100%',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ced4da',
                fontSize: '14px'
              }}
            />
          </div>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <button
            onClick={onGenerateQuestions}
            disabled={isGeneratingQuestions || !selectedMainRole || selectedDifficulties.length === 0}
            style={{
              backgroundColor: isGeneratingQuestions ? '#6c757d' : '#28a745',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              cursor: isGeneratingQuestions ? 'not-allowed' : 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            {isGeneratingQuestions ? '⏳ Generating...' : '🚀 Generate Questions'}
          </button>
        </div>

        {questionSession && (
          <div style={{
            backgroundColor: '#f8f9fa', 
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <h4 style={{ marginBottom: '12px', color: '#495057' }}>
              📋 Generated Questions ({questionSession.total_questions})
            </h4>
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {questionSession.questions.map((q, index) => (
                <div key={q.id} style={{ 
                  padding: '8px 12px', 
                  marginBottom: '8px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef',
                  cursor: 'pointer'
                }}
                onClick={() => onAddQuestionToSession(q)}
                title="Click to add this question to the session">
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                    Q{index + 1} • {q.difficulty} • {q.sub_role || q.main_role}
                    {questionsAsked.some(qa => qa.id === q.id) && (
                      <span style={{ color: '#28a745', fontWeight: 'bold', marginLeft: '8px' }}>
                        ✓ Added to Session
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: '500' }}>
                    {q.question}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {questionsAsked.length > 0 && (
          <div style={{
            backgroundColor: '#e8f5e8', 
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid #28a745',
            marginTop: '20px'
          }}>
            <h4 style={{ marginBottom: '12px', color: '#155724' }}>
              🎯 Questions Asked in Session ({questionsAsked.length})
            </h4>
            
            <QuestionPerformanceSummary questionsAsked={questionsAsked} />

            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {questionsAsked.map((q, index) => (
                <div key={q.id} style={{ 
                  padding: '12px', 
                  marginBottom: '12px',
                  backgroundColor: 'white',
                  borderRadius: '6px',
                  border: '1px solid #c3e6cb'
                }}>
                  <div style={{ fontSize: '12px', color: '#155724', marginBottom: '8px' }}>
                    Q{index + 1} • {q.difficulty} • {q.sub_role || q.main_role}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                    {q.question}
                  </div>
                  
                  <div style={{ marginTop: '8px' }}>
                    {editingQuestion === q.id ? (
                      <QuestionRatingForm 
                        question={q}
                        onSave={onUpdateQuestionRating}
                        onCancel={() => onSetEditingQuestion(null)}
                      />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span style={{ fontSize: '12px', color: '#155724' }}>Rating:</span>
                          {q.rating ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                              {[1,2,3,4,5].map(star => (
                                <span key={star} style={{ 
                                  color: star <= (q.rating || 0) ? '#ffc107' : '#e9ecef',
                                  fontSize: '16px'
                                }}>★</span>
                              ))}
                              <span style={{ fontSize: '12px', marginLeft: '4px' }}>
                                {q.rating}/5
                              </span>
                            </div>
                          ) : (
                            <span style={{ fontSize: '12px', color: '#6c757d' }}>Not rated</span>
                          )}
                        </div>
                        <button
                          onClick={() => onSetEditingQuestion(q.id)}
                          style={{
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            cursor: 'pointer'
                          }}
                        >
                          {q.rating ? 'Edit Rating' : 'Rate Question'}
                        </button>
                      </div>
                    )}
                    
                    {q.rating && (
                      <div style={{ fontSize: '11px', color: '#155724', marginTop: '4px' }}>
                        {getRatingDescription(q.rating)}
                      </div>
                    )}

                    {q.notes && (
                      <div style={{ fontSize: '12px', color: '#155724', marginTop: '4px', fontStyle: 'italic' }}>
                        <strong>Notes:</strong> {q.notes}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )}
  </div>
)


const RecordingControls = ({
  recording,
  totalRecordingTime,
  liveTranscript,
  liveSentiment,
  liveBias,
  biasAlerts,
  analysisLoading,
  lastAnalyzedText,
  analysisCount,
  unifiedAnalysis,
  onStartRecording,
  onStopRecording
}: {
  recording: boolean
  totalRecordingTime: number
  liveTranscript: string
  liveSentiment: any
  liveBias: any
  biasAlerts: Array<{timestamp: number, alert: string}>
  analysisLoading: boolean
  lastAnalyzedText: string
  analysisCount: number
  unifiedAnalysis: UnifiedAnalysisResponse | null
  onStartRecording: () => void
  onStopRecording: () => void
}) => (
  <div className="card">
    <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', color: '#495057' }}>🎙️ Recording Controls</h3>
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
      gap: '16px', 
      alignItems: 'center',
      marginBottom: '20px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        {!recording ? (
          <button
            onClick={onStartRecording} 
            style={{
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              padding: '14px 28px',
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '16px',
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px',
              minWidth: '160px',
              justifyContent: 'center',
              fontWeight: '500',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'
            }}
          >
            🎤 Start Recording
          </button>
        ) : (
          <button
            onClick={onStopRecording} 
            style={{
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              padding: '14px 28px',
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              minWidth: '160px',
              justifyContent: 'center',
              fontWeight: '500',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'
            }}
          >
            ⏹️ Stop Recording
          </button>
        )}
      </div>
      
      <div style={{
        padding: '16px 20px', 
        backgroundColor: recording ? '#dc3545' : '#f8f9fa', 
        borderRadius: '10px',
        border: `1px solid ${recording ? '#dc3545' : '#dee2e6'}`,
        textAlign: 'center',
        minHeight: '80px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        color: recording ? 'white' : '#666'
      }}>
        <div style={{ fontSize: '12px', marginBottom: '6px', fontWeight: '500' }}>
          Status
        </div>
        <div style={{ fontSize: '16px', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
        {recording && (
          <div style={{ 
            width: '12px', 
            height: '12px', 
            backgroundColor: 'white', 
            borderRadius: '50%', 
            animation: 'pulse 1s infinite'
          }}></div>
        )}
        {analysisLoading && recording && (
          <div style={{ 
            width: '8px', 
            height: '8px', 
            backgroundColor: '#ffc107', 
            borderRadius: '50%', 
            animation: 'pulse 0.5s infinite',
            marginLeft: '8px'
          }}></div>
        )}
          {recording ? 'Recording...' : 'Ready to Record'}
        </div>
      </div>
      
      <div style={{ 
        padding: '16px 20px', 
        backgroundColor: '#e8f4fd', 
        borderRadius: '10px',
        border: '1px solid #b3d9ff',
        textAlign: 'center',
        minHeight: '80px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center'
      }}>
        <div style={{ fontSize: '12px', color: '#0066cc', marginBottom: '6px', fontWeight: '500' }}>
          Duration
        </div>
        <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#0066cc' }}>
          {formatTime(totalRecordingTime)}
        </div>
      </div>
    </div>
    
    {recording && (
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '16px',
        marginBottom: '20px'
      }}>
        <div style={{ 
          padding: '16px',
          backgroundColor: '#e8f4fd', 
          borderRadius: '10px',
          border: '1px solid #b3d9ff',
          minHeight: '120px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#0066cc', marginBottom: '12px', textAlign: 'center' }}>
            📊 Real-Time Analysis
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', padding: '6px 10px', backgroundColor: 'white', borderRadius: '6px', alignItems: 'center' }}>
              <span>Sentiment:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {liveSentiment && (
                  <span style={{ fontSize: '16px' }}>
                    {getSentimentIcon(liveSentiment.label)}
                  </span>
                )}
                <span style={{ 
                  color: liveSentiment ? getSentimentColor(liveSentiment.label) : '#6c757d', 
                  fontWeight: '500' 
                }}>
                  {liveSentiment ? `${liveSentiment.label} (${(liveSentiment.confidence * 100).toFixed(0)}%)` : 'Listening...'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', backgroundColor: 'white', borderRadius: '6px', marginBottom: '8px', alignItems: 'center' }}>
              <span>Bias Check:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ fontSize: '16px' }}>
                  {liveBias?.is_biased ? '🚨' : liveBias ? '✅' : '⏳'}
                </span>
                <span style={{ 
                  color: liveBias?.is_biased ? '#dc3545' : liveBias ? '#28a745' : '#6c757d', 
                  fontWeight: '500' 
                }}>
                  {liveBias ? (liveBias.is_biased ? `DETECTED (${(liveBias.confidence * 100).toFixed(0)}%)` : 'CLEAN') : 'Waiting...'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', backgroundColor: 'white', borderRadius: '6px', alignItems: 'center' }}>
              <span>Text Length:</span>
              <span style={{ color: liveTranscript.length > 0 ? '#28a745' : '#6c757d', fontWeight: '500' }}>
                {liveTranscript.length} chars
              </span>
            </div>
            {analysisLoading && (
              <div style={{ 
                textAlign: 'center', 
                marginTop: '8px', 
                padding: '4px 8px', 
                backgroundColor: '#fff3cd', 
                borderRadius: '4px',
                fontSize: '11px',
                color: '#856404'
              }}>
                🔄 Analyzing speech...
              </div>
            )}
          </div>
        </div>
        
        <div style={{ 
          padding: '16px',
          backgroundColor: '#fff3cd', 
          borderRadius: '10px',
          border: '1px solid #ffeaa7',
          minHeight: '140px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#856404', marginBottom: '12px', textAlign: 'center' }}>
            🎤 Live Transcript & Analysis
          </div>
          <div style={{ 
            fontSize: '12px', 
            color: '#856404',
            backgroundColor: 'white',
            padding: '8px',
            borderRadius: '6px',
            minHeight: '50px',
            border: '1px solid #ffeaa7',
            marginBottom: '8px'
          }}>
            {liveTranscript || 'Waiting for speech...'}
          </div>
          {lastAnalyzedText && (
            <div style={{ 
              fontSize: '10px', 
              color: '#666',
              backgroundColor: '#f8f9fa',
              padding: '6px',
              borderRadius: '4px',
              border: '1px solid #dee2e6'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '2px' }}>
                Last Analyzed ({analysisCount}): {lastAnalyzedText.length > 30 ? lastAnalyzedText.substring(0, 30) + '...' : lastAnalyzedText}
              </div>
              {unifiedAnalysis && (
                <div style={{ display: 'flex', gap: '8px', fontSize: '9px' }}>
                  <span style={{ color: getSentimentColor(unifiedAnalysis.sentiment.label) }}>
                    {getSentimentIcon(unifiedAnalysis.sentiment.label)} {unifiedAnalysis.sentiment.label}
                  </span>
                  <span style={{ color: unifiedAnalysis.bias_detection.is_biased ? '#dc3545' : '#28a745' }}>
                    {unifiedAnalysis.bias_detection.is_biased ? '🚨 BIAS' : '✅ CLEAN'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div style={{ 
          padding: '16px', 
          backgroundColor: '#f8d7da', 
          borderRadius: '10px',
          border: '1px solid #f5c6cb',
          minHeight: '100px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#721c24', marginBottom: '12px', textAlign: 'center' }}>
            ⚠️ Alerts ({biasAlerts.length})
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {biasAlerts.length > 0 ? (
              <div style={{ maxHeight: '60px', overflowY: 'auto' }}>
                {biasAlerts.slice(-2).map((alert, idx) => (
                  <div key={idx} style={{ 
                    padding: '4px 8px', 
                    backgroundColor: '#f8d7da', 
                    color: '#721c24',
                    borderRadius: '4px',
                    marginBottom: '4px',
                    fontSize: '11px'
                  }}>
                    {alert.alert}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#28a745' }}>No alerts detected ✅</div>
            )}
          </div>
        </div>
      </div>
    )}
  </div>
)

const CombinedAnalysis = ({
  unifiedAnalysis,
  flaggedIssues,
  questionsAsked,
  totalRecordingTime
}: {
  unifiedAnalysis: UnifiedAnalysisResponse | null
  flaggedIssues: Array<{
    timestamp: number
    type: 'sentiment' | 'bias'
    text: string
    score: number
    explanation: string
    suggestions: string[]
    severity: 'low' | 'medium' | 'high'
  }>
  questionsAsked: QuestionSelectorQuestion[]
  totalRecordingTime: number
}) => {
  const sentimentIssues = flaggedIssues.filter(issue => issue.type === 'sentiment')
  const biasIssues = flaggedIssues.filter(issue => issue.type === 'bias')
  const hasAnalysis = unifiedAnalysis || flaggedIssues.length > 0

  if (!hasAnalysis) {
    return null
  }

  return (
    <div className="card">
      <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', color: '#495057' }}>
        🔍 Comprehensive Analysis & Session Review
      </h3>
      
      {/* Quick Stats Overview */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
        gap: '12px',
        marginBottom: '20px'
      }}>
        <div style={{ 
          padding: '12px', 
          backgroundColor: '#e8f4fd', 
          borderRadius: '8px',
          border: '1px solid #b3d9ff',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#0066cc' }}>
            {totalRecordingTime > 0 ? formatTime(totalRecordingTime) : '0:00'}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>Duration</div>
        </div>
        
        <div style={{ 
          padding: '12px', 
          backgroundColor: '#fff3cd', 
          borderRadius: '8px',
          border: '1px solid #ffeaa7',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#856404' }}>
            {questionsAsked.length}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>Questions</div>
        </div>

        <div style={{ 
          padding: '12px', 
          backgroundColor: '#f8d7da', 
          borderRadius: '8px',
          border: '1px solid #f5c6cb',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#721c24' }}>
            {flaggedIssues.length}
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>Issues Found</div>
        </div>

        {unifiedAnalysis && (
          <div style={{ 
            padding: '12px', 
            backgroundColor: unifiedAnalysis.has_issues ? '#f8d7da' : '#d4edda', 
            borderRadius: '8px',
            border: `1px solid ${unifiedAnalysis.has_issues ? '#f5c6cb' : '#c3e6cb'}`,
            textAlign: 'center'
          }}>
            <div style={{ 
              fontSize: '18px', 
              fontWeight: 'bold', 
              color: unifiedAnalysis.has_issues ? '#721c24' : '#155724'
            }}>
              {(unifiedAnalysis.overall_score * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {unifiedAnalysis.has_issues ? 'Risk Score' : 'Clean Score'}
            </div>
          </div>
        )}
      </div>

      {/* Current Analysis Results */}
      {unifiedAnalysis && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#495057', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📊 Current Analysis
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <div style={{ 
              padding: '12px', 
              backgroundColor: '#f8f9fa', 
              borderRadius: '8px',
              border: '1px solid #dee2e6'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '20px' }}>{getSentimentIcon(unifiedAnalysis.sentiment.label)}</span>
                <span style={{
                  padding: '4px 8px',
                  backgroundColor: getSentimentColor(unifiedAnalysis.sentiment.label),
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold'
                }}>
                  {unifiedAnalysis.sentiment.label}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                Confidence: {(unifiedAnalysis.sentiment.confidence * 100).toFixed(1)}%
              </div>
            </div>

            <div style={{ 
              padding: '12px', 
              backgroundColor: '#f8f9fa', 
              borderRadius: '8px',
              border: '1px solid #dee2e6'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '20px' }}>
                  {unifiedAnalysis.bias_detection.is_biased ? '🚨' : '✅'}
                </span>
                <span style={{
                  padding: '4px 8px',
                  backgroundColor: unifiedAnalysis.bias_detection.is_biased ? '#dc3545' : '#28a745',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold'
                }}>
                  {unifiedAnalysis.bias_detection.is_biased ? 'BIAS DETECTED' : 'CLEAN'}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                Confidence: {(unifiedAnalysis.bias_detection.confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Issue Summary */}
      {flaggedIssues.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#dc3545', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⚠️ Issues Detected ({flaggedIssues.length})
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '12px' }}>
            <div style={{ 
              padding: '8px 12px', 
              backgroundColor: sentimentIssues.length > 0 ? '#f8d7da' : '#d4edda', 
              borderRadius: '6px',
              border: `1px solid ${sentimentIssues.length > 0 ? '#f5c6cb' : '#c3e6cb'}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: sentimentIssues.length > 0 ? '#721c24' : '#155724' }}>
                📈 Sentiment Issues: {sentimentIssues.length}
              </div>
            </div>
            <div style={{ 
              padding: '8px 12px', 
              backgroundColor: biasIssues.length > 0 ? '#f8d7da' : '#d4edda', 
              borderRadius: '6px',
              border: `1px solid ${biasIssues.length > 0 ? '#f5c6cb' : '#c3e6cb'}`
            }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', color: biasIssues.length > 0 ? '#721c24' : '#155724' }}>
                🚨 Bias Issues: {biasIssues.length}
              </div>
            </div>
          </div>

          {/* Top Issues Preview */}
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {flaggedIssues.slice(0, 3).map((issue, index) => (
              <div key={index} style={{
                padding: '8px 12px',
                marginBottom: '8px',
                borderRadius: '6px',
                backgroundColor: issue.type === 'sentiment' ? '#e3f2fd' : '#fce4ec',
                border: `1px solid ${issue.type === 'sentiment' ? '#2196f3' : '#e91e63'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '14px' }}>
                      {issue.type === 'sentiment' ? '📈' : '🚨'}
                    </span>
                    <span style={{ 
                      fontWeight: 'bold', 
                      fontSize: '12px',
                      color: issue.type === 'sentiment' ? '#1976d2' : '#c2185b'
                    }}>
                      {issue.type.toUpperCase()} - {issue.severity.toUpperCase()}
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: '#666' }}>
                    {issue.score.toFixed(2)}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  "{issue.text.length > 60 ? issue.text.substring(0, 60) + '...' : issue.text}"
                </div>
              </div>
            ))}
            {flaggedIssues.length > 3 && (
              <div style={{ 
                textAlign: 'center', 
                padding: '8px', 
                color: '#666', 
                fontSize: '12px',
                fontStyle: 'italic'
              }}>
                +{flaggedIssues.length - 3} more issues detected
              </div>
            )}
          </div>
        </div>
      )}

      {/* Key Insights & Recommendations */}
      {unifiedAnalysis && (unifiedAnalysis.insights.length > 0 || unifiedAnalysis.recommendations.length > 0) && (
        <div>
          <h4 style={{ color: '#495057', marginBottom: '12px' }}>💡 Key Takeaways</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {unifiedAnalysis.insights.slice(0, 2).map((insight: string, index: number) => (
              <div key={index} style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: '8px', 
                padding: '8px', 
                backgroundColor: '#f8f9fa', 
                borderRadius: '6px',
                fontSize: '13px'
              }}>
                <span style={{ fontSize: '14px', marginTop: '2px' }}>💡</span>
                <span>{insight}</span>
              </div>
            ))}
            {unifiedAnalysis.recommendations.slice(0, 2).map((recommendation: string, index: number) => (
              <div key={index} style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: '8px', 
                padding: '8px', 
                backgroundColor: '#fff3cd', 
                borderRadius: '6px',
                fontSize: '13px'
              }}>
                <span style={{ fontSize: '14px', marginTop: '2px' }}>🔧</span>
                <span>{recommendation}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const TextAnalysisTrigger = ({
  analysisLoading,
  analysisError,
  onAnalyzeText
}: {
  analysisLoading: boolean
  analysisError: string | null
  onAnalyzeText: () => void
}) => (
  <div className="card">
    <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', color: '#495057' }}>🔍 Text Analysis</h3>
    <p style={{ color: '#666', marginBottom: '16px' }}>
      Analyze the current transcript for sentiment and bias detection.
    </p>
    <button
      onClick={onAnalyzeText}
      disabled={analysisLoading}
      style={{
        backgroundColor: analysisLoading ? '#6c757d' : '#007bff',
        color: 'white',
        border: 'none',
        padding: '12px 24px',
        borderRadius: '8px',
        cursor: analysisLoading ? 'not-allowed' : 'pointer',
        fontSize: '16px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}
    >
      {analysisLoading ? '⏳ Analyzing...' : '🔍 Analyze Text'}
    </button>
    {analysisError && (
      <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '4px' }}>
        Error: {analysisError}
      </div>
    )}
  </div>
)

const SessionTranscript = ({ transcript }: { transcript: TranscriptItem[] }) => (
  <div className="card">
    <h3>📝 Session Transcript</h3>
    <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
      {transcript.map((item, index) => (
        <div key={index} style={{ 
          padding: '8px 12px', 
          borderBottom: '1px solid #eee',
          fontSize: '14px'
        }}>
          <div style={{ color: '#666', fontSize: '12px', marginBottom: '4px' }}>
            {new Date(item.timestamp_ms).toLocaleTimeString()}
          </div>
          <div>{item.text}</div>
        </div>
      ))}
    </div>
  </div>
)

const SessionActions = ({
  isGeneratingPDF,
  onGeneratePDF
}: {
  isGeneratingPDF: boolean
  onGeneratePDF: () => void
}) => (
  <div className="card">
    <h3 style={{ margin: '0 0 20px 0', fontSize: '20px', color: '#495057' }}>📊 Session Actions</h3>
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
      gap: '16px',
      alignItems: 'center'
    }}>
      <button
        onClick={onGeneratePDF}
        disabled={isGeneratingPDF}
        style={{
          backgroundColor: isGeneratingPDF ? '#6c757d' : '#dc3545',
          color: 'white',
          border: 'none',
          padding: '14px 24px',
          borderRadius: '10px',
          cursor: isGeneratingPDF ? 'not-allowed' : 'pointer',
          fontSize: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          justifyContent: 'center',
          fontWeight: '500',
          transition: 'all 0.2s ease',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          minHeight: '50px'
        }}
        onMouseOver={(e) => {
          if (!isGeneratingPDF) {
            e.currentTarget.style.transform = 'translateY(-1px)'
            e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.15)'
          }
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'
        }}
      >
        {isGeneratingPDF ? '⏳ Generating...' : '📄 Generate PDF Report'}
      </button>
    </div>
  </div>
)

// Main Dashboard Component
export default function Dashboard() {
  const { user, logout } = useAuth()

  // State management
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [transcript, setTranscript] = useState<TranscriptItem[]>([])
  const [recording, setRecording] = useState(false)
  const [liveTranscript, setLiveTranscript] = useState<string>('')
  const [liveSentiment, setLiveSentiment] = useState<any>(null)
  const [liveBias, setLiveBias] = useState<any>(null)
  const [biasAlerts, setBiasAlerts] = useState<Array<{timestamp: number, alert: string}>>([])
  const [totalRecordingTime, setTotalRecordingTime] = useState(0)
  
  const [questionMetadata, setQuestionMetadata] = useState<QuestionMetadata | null>(null)
  const [selectedMainRole, setSelectedMainRole] = useState<string>('')
  const [selectedSubRole, setSelectedSubRole] = useState<string>('')
  const [selectedDifficulties, setSelectedDifficulties] = useState<string[]>([])
  const [numQuestions, setNumQuestions] = useState<number>(5)
  const [showQuestionSelector, setShowQuestionSelector] = useState(false)
  const [questionSession, setQuestionSession] = useState<QuestionSession | null>(null)
  const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false)
  
  const [questionsAsked, setQuestionsAsked] = useState<QuestionSelectorQuestion[]>([])
  const [flaggedIssues, setFlaggedIssues] = useState<Array<{
    timestamp: number
    type: 'sentiment' | 'bias'
    text: string
    score: number
    explanation: string
    suggestions: string[]
    severity: 'low' | 'medium' | 'high'
  }>>([])
  const [sessionSummary, setSessionSummary] = useState<string>('')
  const [editingQuestion, setEditingQuestion] = useState<string | null>(null)
  
  const [unifiedAnalysis, setUnifiedAnalysis] = useState<UnifiedAnalysisResponse | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [lastAnalyzedText, setLastAnalyzedText] = useState<string>('')
  const [analysisCount, setAnalysisCount] = useState<number>(0)
  
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const recordingStartTimeRef = useRef<number>(0)

  // Reset all session data
  const resetAllSessionData = () => {
    setTranscript([])
    setLiveTranscript('')
    setLiveSentiment(null)
    setLiveBias(null)
    setBiasAlerts([])
    setTotalRecordingTime(0)
    setRecording(false)
    setQuestionsAsked([])
    setFlaggedIssues([])
    setSessionSummary('')
    setUnifiedAnalysis(null)
    setLastAnalyzedText('')
    setAnalysisCount(0)
  }

  // Load question metadata on component mount
  useEffect(() => {
    const loadQuestionMetadata = async () => {
      try {
        const response = await axios.get(`${API_BASE}/question-selector/metadata`)
        setQuestionMetadata(response.data)
      } catch (error) {
        console.error('Error loading question metadata:', error)
      }
    }
    
    loadQuestionMetadata()
  }, [])

  // Sync dashboard when session changes
  useEffect(() => {
    const loadSessionTranscript = async (sessionId: number) => {
      try {
        const response = await axios.get(`${API_BASE}/sessions/${sessionId}/transcript`)
        setTranscript(response.data)
      } catch (error) {
        console.error('Error loading session transcript:', error)
      }
    }

    if (sessionId) {
      console.log('Session changed, syncing dashboard data')
      loadSessionTranscript(sessionId)
    } else {
      resetAllSessionData()
    }
  }, [sessionId])

  // Timer effect for recording time
  useEffect(() => {
    let interval: number
    if (recording) {
      interval = setInterval(() => {
        setTotalRecordingTime(Date.now() - recordingStartTimeRef.current)
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [recording])

  // Create new session
  const createNewSession = async () => {
    try {
      if (!user?.id) {
        console.error('User not authenticated for session creation')
        return null
      }
      
      const response = await axios.post(`${API_BASE}/sessions/`, {
        user_id: user.id,
        role: 'General',
        level: 'Mixed'
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
      setSessionId(response.data.id)
      return response.data.id
    } catch (error) {
      console.error('Error creating session:', error)
      return null
    }
  }

  // Unified Analysis function
  const performUnifiedAnalysis = async (textToAnalyze: string) => {
    if (!textToAnalyze.trim()) {
      setAnalysisError('No text to analyze');
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const token = localStorage.getItem('token');
      console.log('🔍 Starting unified analysis with token:', token ? 'Present' : 'Missing');
      console.log('📝 Text to analyze:', textToAnalyze);
      
      // Try authenticated endpoint first, fallback to public endpoint
      let response;
      try {
        response = await fetch('http://127.0.0.1:8000/unified-analysis/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ text: textToAnalyze }),
        });
      } catch (authError) {
        console.log('🔄 Auth failed, trying public endpoint...');
        response = await fetch('http://127.0.0.1:8000/unified-analysis/analyze-public', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: textToAnalyze }),
        });
      }

      console.log('📡 Response status:', response.status);
      console.log('📡 Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Analysis failed:', errorText);
        throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('✅ Analysis result:', result);
      setUnifiedAnalysis(result);
      setLastAnalyzedText(textToAnalyze);
      setAnalysisCount(prev => prev + 1);
    
    // Update live sentiment and bias data for display
      if (result.sentiment) {
        setLiveSentiment(result.sentiment)
    }
      if (result.bias_detection) {
        setLiveBias(result.bias_detection)
    }
    
      // Enhanced issue tracking with detailed analysis
      if (result.has_issues && result.flagged_items.length > 0) {
        result.flagged_items.forEach((item: any) => {
          const timestamp = Date.now()
    
          // Add to legacy bias alerts for backward compatibility
        setBiasAlerts(prev => [...prev, {
            timestamp,
          alert: `${item.type.toUpperCase()}: ${item.description}`
        }])
          
          // Add to enhanced flagged issues with detailed analysis
          const severity = result.overall_score > 0.7 ? 'high' : 
                          result.overall_score > 0.4 ? 'medium' : 'low'
          
          setFlaggedIssues(prev => [...prev, {
            timestamp,
            type: item.type === 'sentiment' ? 'sentiment' : 'bias',
            text: textToAnalyze,
            score: result.overall_score,
            explanation: item.description,
            suggestions: [
              'Consider using more neutral language',
              'Focus on objective criteria',
              'Avoid assumptions about personal characteristics'
            ],
            severity
          }])
        })
      }
      
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Start recording
  const startRecording = async () => {
    try {
      console.log('Starting new recording session...')
      resetAllSessionData()
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })
        await transcribeAudio(audioBlob)
      }
      
      mediaRecorder.start(1000)
      setRecording(true)
      const startTime = Date.now()
      recordingStartTimeRef.current = startTime
      
      const newSessionId = await createNewSession()
      if (newSessionId) {
        console.log('New session created:', newSessionId)
        setSessionId(newSessionId)
      }
      
      startContinuousTranscription()
      
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Could not access microphone. Please check permissions.')
    }
  }

  // Stop recording
  const stopRecording = async () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop()
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
      
      setRecording(false)
    }
  }

  // Start continuous transcription with real-time analysis
  const startContinuousTranscription = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.warn('Speech recognition not supported')
      return
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'
    
    setLiveTranscript('')
    setLiveSentiment(null)
    setLiveBias(null)
    setBiasAlerts([])
    setTotalRecordingTime(0)
    recordingStartTimeRef.current = Date.now()
    
    // Track last analysis time to avoid too frequent calls
    let lastAnalysisTime = 0
    let analysisThrottleDelay = 2000 // Analyze every 2 seconds minimum
    
    recognition.onresult = (event: any) => {
      let finalTranscript = ''
      let interimTranscript = ''
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += transcript
        } else {
          interimTranscript += transcript
        }
      }
      
      const currentTranscript = finalTranscript || interimTranscript
      if (currentTranscript.trim()) {
        setLiveTranscript(currentTranscript)
        
        // Real-time analysis for interim results (as you speak)
        const now = Date.now()
        if (interimTranscript.trim() && 
            now - lastAnalysisTime > analysisThrottleDelay && 
            interimTranscript.length > 10) {
          
          console.log('🎤 Real-time analysis of interim text:', interimTranscript)
          performUnifiedAnalysis(interimTranscript)
          lastAnalysisTime = now
        }
        
        // Always analyze final results (completed sentences)
        if (finalTranscript.trim() && finalTranscript.length > 5) {
          console.log('✅ Final transcript analysis:', finalTranscript)
          performUnifiedAnalysis(finalTranscript)
          lastAnalysisTime = now
        }
      }
    }
    
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
    }
    
    recognition.onend = () => {
      if (recording) {
        console.log('🔄 Restarting speech recognition...')
        recognition.start()
      }
    }
    
    recognition.start()
    console.log('🎙️ Real-time speech recognition and analysis started')
  }

  // Transcribe audio using Whisper
  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.wav')
      
      const response = await axios.post(`${API_BASE}/ai/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      const transcription = response.data.transcription
      if (transcription && sessionId) {
        await saveTranscriptItem(transcription)
        performUnifiedAnalysis(transcription)
      }
    } catch (error) {
      console.error('Transcription error:', error)
    }
  }

  // Save transcript item
  const saveTranscriptItem = async (text: string) => {
    if (!sessionId) return
    
    try {
      const response = await axios.post(`${API_BASE}/sessions/transcript`, {
              session_id: sessionId,
        timestamp_ms: Date.now(),
        text: text
            })
      
      setTranscript(prev => [...prev, response.data])
          } catch (error) {
      console.error('Error saving transcript:', error)
    }
  }

  // Question selection handlers
  const handleMainRoleChange = (mainRole: string) => {
    setSelectedMainRole(mainRole)
    setSelectedSubRole('')
  }

  const handleSubRoleChange = (subRole: string) => {
    setSelectedSubRole(subRole)
  }

  const handleDifficultyToggle = (difficulty: string) => {
    setSelectedDifficulties(prev => {
      if (prev.includes(difficulty)) {
        return prev.filter(d => d !== difficulty)
      } else {
        return [...prev, difficulty]
      }
    })
  }

  const handleNumQuestionsChange = (num: number) => {
    setNumQuestions(num)
  }

  const handleToggleSelector = () => {
    setShowQuestionSelector(!showQuestionSelector)
  }

  const handleGenerateQuestions = async () => {
    if (!selectedMainRole || selectedDifficulties.length === 0 || numQuestions <= 0) {
      alert('Please select main role, at least one difficulty level, and number of questions')
      return
    }

    if (!user?.id) {
      alert('User not authenticated. Please login again.')
      return
    }

    console.log('Auth token:', localStorage.getItem('token'))
    console.log('User:', user)

    setIsGeneratingQuestions(true)
    try {
      const response = await axios.post(`${API_BASE}/question-selector/generate-session`, {
        main_role: selectedMainRole,
        sub_role: selectedSubRole || null,
        difficulties: selectedDifficulties,
        num_questions: numQuestions
      })
      setQuestionSession(response.data)
      
      if (!user?.id) {
        alert('User not authenticated. Please login again.')
        return
      }
      
      console.log('Creating session for user:', user.id)
      const sessionResponse = await axios.post(`${API_BASE}/sessions/`, {
        user_id: user.id,
        role: selectedMainRole,
        level: selectedDifficulties.join(', ')
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      })
      setSessionId(sessionResponse.data.id)
      
    } catch (error) {
      console.error('Error generating question session:', error)
      alert('Failed to generate questions. Please try again.')
    } finally {
      setIsGeneratingQuestions(false)
    }
  }

  const handleAddQuestionToSession = (question: QuestionSelectorQuestion) => {
    setQuestionsAsked(prev => {
      if (prev.some(q => q.id === question.id)) {
        return prev
      }
      return [...prev, { ...question, rating: undefined, notes: '' }]
    })
  }

  const handleUpdateQuestionRating = (questionId: string, rating: number, notes: string = '') => {
    setQuestionsAsked(prev => 
      prev.map(q => 
        q.id === questionId 
          ? { ...q, rating, notes }
          : q
      )
    )
    setEditingQuestion(null)
  }

  const handleSetEditingQuestion = (questionId: string | null) => {
    setEditingQuestion(questionId)
  }

  // Generate comprehensive session summary
  const generateComprehensiveSessionSummary = () => {
    const totalIssues = flaggedIssues.length
    const sentimentIssues = flaggedIssues.filter(issue => issue.type === 'sentiment').length
    const biasIssues = flaggedIssues.filter(issue => issue.type === 'bias').length
    const highSeverityIssues = flaggedIssues.filter(issue => issue.severity === 'high').length
    
    const ratedQuestions = questionsAsked.filter(q => q.rating)
    const totalRating = ratedQuestions.reduce((sum, q) => sum + (q.rating || 0), 0)
    const averageRating = ratedQuestions.length > 0 ? totalRating / ratedQuestions.length : 0
    
    const ratingDistribution = {
      5: ratedQuestions.filter(q => q.rating === 5).length,
      4: ratedQuestions.filter(q => q.rating === 4).length,
      3: ratedQuestions.filter(q => q.rating === 3).length,
      2: ratedQuestions.filter(q => q.rating === 2).length,
      1: ratedQuestions.filter(q => q.rating === 1).length
    }

    const performanceLevel = averageRating >= 4.5 ? 'Excellent' :
                           averageRating >= 3.5 ? 'Good' :
                           averageRating >= 2.5 ? 'Average' :
                           averageRating >= 1.5 ? 'Below Average' : 'Poor'

    const summary = `
# Interview Session Summary

## Session Overview
- **Session ID**: ${sessionId}
- **Duration**: ${formatTime(totalRecordingTime)}
- **Questions Asked**: ${questionsAsked.length}
- **Total Issues Detected**: ${totalIssues}

## Issues Analysis
- **Sentiment Issues**: ${sentimentIssues}
- **Bias Issues**: ${biasIssues}
- **High Severity Issues**: ${highSeverityIssues}

## Detailed Issues
 ${flaggedIssues.map((issue, index) => `
### Issue ${index + 1} - ${issue.type.toUpperCase()} (${issue.severity.toUpperCase()})
- **Text**: "${issue.text}"
- **Score**: ${issue.score.toFixed(2)}
- **Explanation**: ${issue.explanation}
- **Suggestions**: ${issue.suggestions.join(', ')}
`).join('')}

## Questions Asked & Performance
 ${questionsAsked.map((q, index) => `
 ${index + 1}. **${q.difficulty.toUpperCase()}** - ${q.question}
   ${q.rating ? `**Rating**: ${q.rating}/5 - ${getRatingDescription(q.rating)}` : '**Rating**: Not rated'}
   ${q.notes ? `**Notes**: ${q.notes}` : ''}
`).join('')}

## Question Performance Summary
 ${ratedQuestions.length > 0 ? `
- **Average Rating**: ${averageRating.toFixed(1)}/5
- **Performance Level**: ${performanceLevel}
- **Questions Rated**: ${ratedQuestions.length}/${questionsAsked.length}
- **Rating Distribution**:
  - Excellent (5): ${ratingDistribution[5]}
  - Good (4): ${ratingDistribution[4]}
  - Average (3): ${ratingDistribution[3]}
  - Below Average (2): ${ratingDistribution[2]}
  - Poor (1): ${ratingDistribution[1]}
` : 'No questions have been rated yet.'}

## Recommendations
 ${flaggedIssues.length > 0 ? `
- Focus on neutral language and objective criteria
- Avoid assumptions about personal characteristics
- Consider the suggested improvements for each flagged issue
` : `
- Excellent interview conduct with no significant issues detected
- Continue using neutral, professional language
`}

 ${ratedQuestions.length > 0 && averageRating < 3.0 ? `
- Consider providing more detailed feedback to help candidate improve
- Focus on areas where the candidate struggled (ratings 1-2)
` : ratedQuestions.length > 0 && averageRating >= 4.0 ? `
- Candidate demonstrated strong understanding across most questions
- Consider more challenging questions for future interviews
` : ''}

## Key Takeaways
- Total recording time: ${formatTime(totalRecordingTime)}
- Issues detected: ${totalIssues} (${highSeverityIssues} high severity)
- Questions covered: ${questionsAsked.length}
- Question performance: ${ratedQuestions.length > 0 ? `${performanceLevel} (${averageRating.toFixed(1)}/5)` : 'Not evaluated'}
- Overall session quality: ${flaggedIssues.length === 0 ? 'Excellent' : flaggedIssues.length < 3 ? 'Good' : 'Needs Improvement'}
    `.trim()
    
    return summary
  }

  // Generate PDF report
  const handleGeneratePDF = async () => {
    if (!sessionId) {
      alert('No session available to generate report')
      return
    }

    setIsGeneratingPDF(true)
    try {
      const pdfData = {
        session_id: sessionId,
        role: selectedMainRole || 'General',
        level: selectedDifficulties.join(', ') || 'Mixed',
        total_recording_time: Math.floor(totalRecordingTime / 1000),
        transcript: transcript.map(item => ({
          timestamp_ms: item.timestamp_ms,
          text: item.text,
          sentiment_label: item.sentiment_label,
          sentiment_score: item.sentiment_score,
          bias_flagged: item.bias_flagged
        })),
        sentiment_analysis: transcript.filter(item => item.sentiment_label).map(item => ({
          sentiment: item.sentiment_label,
          confidence: item.sentiment_score,
          text: item.text
        })),
        bias_alerts: flaggedIssues.map(issue => ({
          alert: `${issue.type.toUpperCase()}: ${issue.explanation}`,
          timestamp: issue.timestamp,
          severity: issue.severity,
          suggestions: issue.suggestions
        })),
        questions_asked: questionsAsked.length > 0 ? questionsAsked : (questionSession?.questions || []),
        question_performance: {
          averageRating: questionsAsked.filter(q => q.rating).length > 0 
            ? (questionsAsked.filter(q => q.rating).reduce((sum, q) => sum + (q.rating || 0), 0) / questionsAsked.filter(q => q.rating).length).toFixed(1)
            : '0',
          totalRated: questionsAsked.filter(q => q.rating).length,
          totalQuestions: questionsAsked.length,
          performanceLevel: questionsAsked.filter(q => q.rating).length > 0 
            ? (questionsAsked.filter(q => q.rating).reduce((sum, q) => sum + (q.rating || 0), 0) / questionsAsked.filter(q => q.rating).length) >= 4.5 ? 'Excellent' :
              (questionsAsked.filter(q => q.rating).reduce((sum, q) => sum + (q.rating || 0), 0) / questionsAsked.filter(q => q.rating).length) >= 3.5 ? 'Good' :
              (questionsAsked.filter(q => q.rating).reduce((sum, q) => sum + (q.rating || 0), 0) / questionsAsked.filter(q => q.rating).length) >= 2.5 ? 'Average' :
              (questionsAsked.filter(q => q.rating).reduce((sum, q) => sum + (q.rating || 0), 0) / questionsAsked.filter(q => q.rating).length) >= 1.5 ? 'Below Average' : 'Poor'
            : 'Not Rated',
          ratingDistribution: {
            5: questionsAsked.filter(q => q.rating === 5).length,
            4: questionsAsked.filter(q => q.rating === 4).length,
            3: questionsAsked.filter(q => q.rating === 3).length,
            2: questionsAsked.filter(q => q.rating === 2).length,
            1: questionsAsked.filter(q => q.rating === 1).length
          }
        },
        generated_at: new Date().toISOString(),
        session_summary: sessionSummary || generateComprehensiveSessionSummary()
      }

      const response = await axios.post(`${API_BASE}/reports/generate-pdf`, pdfData, {
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `interview-report-${sessionId}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

    } catch (error) {
      console.error('Error generating PDF:', error)
      alert('Failed to generate PDF report. Please try again.')
    } finally {
      setIsGeneratingPDF(false)
    }
  }


  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      <Navbar user={user} logout={logout} />
      
              <div style={{
        maxWidth: '1400px', 
        margin: '0 auto', 
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px'
      }}>
        <QuestionSelector
          questionMetadata={questionMetadata}
          selectedMainRole={selectedMainRole}
          selectedSubRole={selectedSubRole}
          selectedDifficulties={selectedDifficulties}
          numQuestions={numQuestions}
          showQuestionSelector={showQuestionSelector}
          questionSession={questionSession}
          questionsAsked={questionsAsked}
          editingQuestion={editingQuestion}
          isGeneratingQuestions={isGeneratingQuestions}
          onMainRoleChange={handleMainRoleChange}
          onSubRoleChange={handleSubRoleChange}
          onDifficultyToggle={handleDifficultyToggle}
          onNumQuestionsChange={handleNumQuestionsChange}
          onToggleSelector={handleToggleSelector}
          onGenerateQuestions={handleGenerateQuestions}
          onAddQuestionToSession={handleAddQuestionToSession}
          onUpdateQuestionRating={handleUpdateQuestionRating}
          onSetEditingQuestion={handleSetEditingQuestion}
        />

        <RecordingControls
          recording={recording}
          totalRecordingTime={totalRecordingTime}
          liveTranscript={liveTranscript}
          liveSentiment={liveSentiment}
          liveBias={liveBias}
          biasAlerts={biasAlerts}
          analysisLoading={analysisLoading}
          lastAnalyzedText={lastAnalyzedText}
          analysisCount={analysisCount}
          unifiedAnalysis={unifiedAnalysis}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
        />

        <CombinedAnalysis
          unifiedAnalysis={unifiedAnalysis}
          flaggedIssues={flaggedIssues}
          questionsAsked={questionsAsked}
          totalRecordingTime={totalRecordingTime}
        />

        {liveTranscript && !unifiedAnalysis && (
          <TextAnalysisTrigger
            analysisLoading={analysisLoading}
            analysisError={analysisError}
            onAnalyzeText={() => performUnifiedAnalysis(liveTranscript)}
          />
        )}

      {sessionId && transcript.length > 0 && (
          <SessionTranscript transcript={transcript} />
        )}

        {sessionId && (
          <SessionActions
            isGeneratingPDF={isGeneratingPDF}
            onGeneratePDF={handleGeneratePDF}
          />
          )}
      </div>

      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
          
          .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
          }
          
          .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 24px;
            border: 1px solid #e9ecef;
            margin-bottom: 0;
          }
          
          .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 0;
          }
          
          .navbar-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          
          .navbar h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
          }
          
          .navbar-actions {
            display: flex;
            align-items: center;
            gap: 12px;
          }
          
          .btn-secondary {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
          }
          
          .btn-secondary:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-1px);
          }
          
          .user-info {
            font-size: 14px;
            opacity: 0.9;
          }
        `}
      </style>
    </div>
  )
}