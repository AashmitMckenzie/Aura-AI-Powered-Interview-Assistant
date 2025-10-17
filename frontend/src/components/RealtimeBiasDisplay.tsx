import { useState, useEffect } from 'react'

interface BiasCategory {
  category: string
  description: string
  confidence: number
  keyword?: string
  context?: string
  weight: number
}

interface BiasResult {
  is_biased: boolean
  confidence: number
  categories: BiasCategory[]
  highlighted_text: string
  bias_score: number
  processing_time_ms: number
}

interface RealtimeBiasDisplayProps {
  text: string
  onBiasDetected?: (result: BiasResult) => void
  isActive: boolean
}

const BIAS_CATEGORY_COLORS = {
  pejorative: '#dc3545',
  subjective: '#fd7e14',
  exaggeration: '#ffc107',
  stereotyping: '#6f42c1',
  emotional_manipulation: '#e83e8c',
  confirmation_bias: '#20c997',
  general_bias: '#6c757d'
}

const BIAS_CATEGORY_ICONS = {
  pejorative: '🚫',
  subjective: '💭',
  exaggeration: '📈',
  stereotyping: '🏷️',
  emotional_manipulation: '🎭',
  confirmation_bias: '🔄',
  general_bias: '⚠️'
}

export default function RealtimeBiasDisplay({ text, onBiasDetected, isActive }: RealtimeBiasDisplayProps) {
  const [biasResult, setBiasResult] = useState<BiasResult | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [lastAnalyzedText, setLastAnalyzedText] = useState('')

  const analyzeText = async (textToAnalyze: string) => {
    if (!textToAnalyze.trim() || textToAnalyze === lastAnalyzedText) return

    setIsAnalyzing(true)
    try {
      const response = await fetch('http://127.0.0.1:8000/bias-realtime/detect-realtime', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: textToAnalyze })
      })

      if (response.ok) {
        const result = await response.json()
        setBiasResult(result)
        setLastAnalyzedText(textToAnalyze)
        
        if (onBiasDetected) {
          onBiasDetected(result)
        }
      }
    } catch (error) {
      console.error('Bias detection error:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  useEffect(() => {
    if (isActive && text.trim()) {
      // Debounce the analysis to avoid too many requests
      const timeoutId = setTimeout(() => {
        analyzeText(text)
      }, 500) // 500ms debounce

      return () => clearTimeout(timeoutId)
    }
  }, [text, isActive])

  const getCategoryColor = (category: string) => {
    return BIAS_CATEGORY_COLORS[category as keyof typeof BIAS_CATEGORY_COLORS] || '#6c757d'
  }

  const getCategoryIcon = (category: string) => {
    return BIAS_CATEGORY_ICONS[category as keyof typeof BIAS_CATEGORY_ICONS] || '⚠️'
  }

  const renderHighlightedText = () => {
    if (!biasResult || !biasResult.highlighted_text) {
      return <span>{text}</span>
    }

    // Security: Sanitize HTML content to prevent XSS
    const sanitizeHtml = (html: string) => {
      // Remove script tags and event handlers
      return html
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/on\w+="[^"]*"/gi, '')
        .replace(/on\w+='[^']*'/gi, '')
        .replace(/javascript:/gi, '')
        .replace(/vbscript:/gi, '')
        .replace(/data:text\/html/gi, '')
    }

    return (
      <div 
        dangerouslySetInnerHTML={{ __html: sanitizeHtml(biasResult.highlighted_text) }}
        style={{ lineHeight: '1.6' }}
      />
    )
  }

  return (
    <div style={{ 
      border: '1px solid #dee2e6', 
      borderRadius: '8px', 
      padding: '16px',
      backgroundColor: '#f8f9fa',
      marginBottom: '16px'
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginBottom: '12px'
      }}>
        <h4 style={{ margin: 0, color: '#495057' }}>
          🎯 Real-time Bias Detection
          {isAnalyzing && <span style={{ color: '#007bff', marginLeft: '8px' }}>Analyzing...</span>}
        </h4>
        
        {biasResult && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px'
          }}>
            <div style={{
              backgroundColor: biasResult.is_biased ? '#dc3545' : '#28a745',
              color: 'white',
              padding: '4px 8px',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {biasResult.is_biased ? 'BIASED' : 'CLEAN'}
            </div>
            <div style={{
              backgroundColor: '#e9ecef',
              color: '#495057',
              padding: '4px 8px',
              borderRadius: '12px',
              fontSize: '12px'
            }}>
              Score: {(biasResult.bias_score * 100).toFixed(0)}%
            </div>
            <div style={{
              backgroundColor: '#e9ecef',
              color: '#495057',
              padding: '4px 8px',
              borderRadius: '12px',
              fontSize: '12px'
            }}>
              {biasResult.processing_time_ms.toFixed(0)}ms
            </div>
          </div>
        )}
      </div>

      {/* Live Transcription with Highlighted Bias */}
      <div style={{
        backgroundColor: 'white',
        border: '1px solid #ced4da',
        borderRadius: '6px',
        padding: '12px',
        minHeight: '60px',
        marginBottom: '12px'
      }}>
        <div style={{ fontSize: '14px', color: '#666', marginBottom: '6px' }}>
          Live Transcription:
        </div>
        <div style={{ fontSize: '16px', lineHeight: '1.5' }}>
          {renderHighlightedText()}
        </div>
      </div>

      {/* Bias Categories */}
      {biasResult && biasResult.categories.length > 0 && (
        <div>
          <div style={{ 
            fontSize: '14px', 
            fontWeight: 'bold', 
            color: '#495057',
            marginBottom: '8px'
          }}>
            Detected Bias Categories:
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {biasResult.categories.map((category, index) => (
              <div 
                key={index}
                style={{
                  backgroundColor: 'white',
                  border: `2px solid ${getCategoryColor(category.category)}`,
                  borderRadius: '6px',
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px'
                }}
              >
                <div style={{ fontSize: '16px' }}>
                  {getCategoryIcon(category.category)}
                </div>
                
                <div style={{ flex: 1 }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px',
                    marginBottom: '4px'
                  }}>
                    <span style={{ 
                      fontWeight: 'bold',
                      color: getCategoryColor(category.category),
                      textTransform: 'uppercase',
                      fontSize: '12px'
                    }}>
                      {category.category}
                    </span>
                    <span style={{
                      backgroundColor: getCategoryColor(category.category),
                      color: 'white',
                      padding: '2px 6px',
                      borderRadius: '10px',
                      fontSize: '10px',
                      fontWeight: 'bold'
                    }}>
                      {(category.confidence * 100).toFixed(0)}%
                    </span>
                    <span style={{
                      backgroundColor: '#e9ecef',
                      color: '#495057',
                      padding: '2px 6px',
                      borderRadius: '10px',
                      fontSize: '10px'
                    }}>
                      Weight: {category.weight}
                    </span>
                  </div>
                  
                  <div style={{ 
                    fontSize: '13px', 
                    color: '#6c757d',
                    marginBottom: '4px'
                  }}>
                    {category.description}
                  </div>
                  
                  {category.keyword && (
                    <div style={{ fontSize: '12px', color: '#495057' }}>
                      <strong>Keyword:</strong> "{category.keyword}"
                    </div>
                  )}
                  
                  {category.context && (
                    <div style={{ fontSize: '12px', color: '#495057' }}>
                      <strong>Context:</strong> "{category.context}"
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Bias Detected */}
      {biasResult && !biasResult.is_biased && (
        <div style={{
          backgroundColor: '#d4edda',
          border: '1px solid #c3e6cb',
          borderRadius: '6px',
          padding: '12px',
          color: '#155724',
          textAlign: 'center'
        }}>
          <div style={{ fontSize: '16px', marginBottom: '4px' }}>
            ✅ No Bias Detected
          </div>
          <div style={{ fontSize: '14px' }}>
            The text appears to be neutral and unbiased
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{ 
        marginTop: '12px',
        padding: '8px',
        backgroundColor: '#e9ecef',
        borderRadius: '4px',
        fontSize: '11px'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Bias Categories:</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {Object.entries(BIAS_CATEGORY_ICONS).map(([category, icon]) => (
            <div key={category} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
              <span>{icon}</span>
              <span style={{ textTransform: 'capitalize' }}>{category.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
