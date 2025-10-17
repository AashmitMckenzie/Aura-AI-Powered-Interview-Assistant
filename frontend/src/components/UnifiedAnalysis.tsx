import React, { useState, useEffect } from 'react';

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

interface UnifiedAnalysisProps {
  liveTranscript?: string;
  isRecording?: boolean;
  onAnalysisComplete?: (analysis: UnifiedAnalysisResponse) => void;
}

const UnifiedAnalysis: React.FC<UnifiedAnalysisProps> = ({ 
  liveTranscript = '', 
  isRecording = false, 
  onAnalysisComplete 
}) => {
  const [analysis, setAnalysis] = useState<UnifiedAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAnalyzedText, setLastAnalyzedText] = useState('');

  // Auto-analyze live transcript when it changes
  useEffect(() => {
    if (liveTranscript && liveTranscript.trim() && liveTranscript !== lastAnalyzedText && isRecording) {
      // Debounce the analysis to avoid too frequent calls
      const timeoutId = setTimeout(() => {
        analyzeText(liveTranscript);
      }, 1000); // Wait 1 second after user stops speaking

      return () => clearTimeout(timeoutId);
    }
  }, [liveTranscript, isRecording, lastAnalyzedText]);

  const analyzeText = async (textToAnalyze: string) => {
    if (!textToAnalyze.trim()) {
      setError('No text to analyze');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:8000/unified-analysis/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ text: textToAnalyze }),
      });

      if (!response.ok) {
        throw new Error('Analysis failed');
      }

      const result = await response.json();
      setAnalysis(result);
      setLastAnalyzedText(textToAnalyze);
      
      // Notify parent component of analysis completion
      if (onAnalysisComplete) {
        onAnalysisComplete(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentIcon = (label: string) => {
    switch (label) {
      case 'POSITIVE':
        return '📈';
      case 'NEGATIVE':
        return '📉';
      default:
        return '📊';
    }
  };

  const getSentimentColor = (label: string) => {
    switch (label) {
      case 'POSITIVE':
        return '#28a745';
      case 'NEGATIVE':
        return '#dc3545';
      default:
        return '#007bff';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return '#dc3545';
      case 'medium':
        return '#ffc107';
      case 'low':
        return '#28a745';
      default:
        return '#6c757d';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div className="card">
        <h3>🛡️ Live Unified Analysis</h3>
        
        {/* Live Transcript Display */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Live Transcript:
          </label>
          <div
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '14px',
              fontFamily: 'inherit',
              minHeight: '80px',
              backgroundColor: liveTranscript ? '#f8f9fa' : '#fff',
              borderColor: isRecording ? '#007bff' : '#ddd',
              borderWidth: isRecording ? '2px' : '1px'
            }}
          >
            {liveTranscript ? (
              <div>
                <div style={{ color: '#666', fontSize: '12px', marginBottom: '8px' }}>
                  {isRecording ? '🎤 Recording...' : '📝 Transcript:'}
                </div>
                <div style={{ lineHeight: '1.5' }}>{liveTranscript}</div>
              </div>
            ) : (
              <div style={{ color: '#999', fontStyle: 'italic' }}>
                {isRecording ? 'Start speaking to see live transcription and analysis...' : 'Start recording to begin live analysis'}
              </div>
            )}
          </div>
        </div>

        {/* Analysis Status */}
        <div style={{ marginBottom: '20px' }}>
          {loading && (
            <div style={{
              padding: '12px',
              backgroundColor: '#d1ecf1',
              color: '#0c5460',
              border: '1px solid #bee5eb',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <div style={{ 
                width: '20px', 
                height: '20px', 
                border: '2px solid #0c5460', 
                borderTop: '2px solid transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              Analyzing live transcript...
            </div>
          )}
          
          {error && (
            <div style={{
              padding: '12px',
              backgroundColor: '#f8d7da',
              color: '#721c24',
              border: '1px solid #f5c6cb',
              borderRadius: '4px',
              marginBottom: '20px'
            }}>
              ⚠️ {error}
            </div>
          )}
        </div>
      </div>

      {analysis && (
        <div style={{ marginTop: '20px' }}>
          {/* Overall Status */}
          <div className="card">
            <h3>
              {analysis.has_issues ? '⚠️ Issues Detected' : '✅ No Issues Found'}
            </h3>
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 'bold' }}>Issue Score</span>
                <span style={{ color: '#666' }}>
                  {(analysis.overall_score * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '20px',
                backgroundColor: '#e9ecef',
                borderRadius: '10px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${analysis.overall_score * 100}%`,
                  height: '100%',
                  backgroundColor: analysis.has_issues ? '#dc3545' : '#28a745',
                  transition: 'width 0.3s ease'
                }} />
              </div>
              <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                <span style={{
                  padding: '4px 8px',
                  backgroundColor: analysis.has_issues ? '#dc3545' : '#28a745',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  {analysis.has_issues ? 'Issues Detected' : 'No Issues'}
                </span>
                <span style={{
                  padding: '4px 8px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}>
                  ⏱️ {analysis.processing_time_ms.toFixed(0)}ms
                </span>
              </div>
            </div>
          </div>

          {/* Sentiment Analysis */}
          <div className="card">
            <h3>💝 Sentiment Analysis</h3>
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                <span style={{ fontSize: '20px' }}>{getSentimentIcon(analysis.sentiment.label)}</span>
                <span style={{
                  padding: '6px 12px',
                  backgroundColor: getSentimentColor(analysis.sentiment.label),
                  color: 'white',
                  borderRadius: '4px',
                  fontWeight: 'bold'
                }}>
                  {analysis.sentiment.label}
                </span>
                <span style={{ color: '#666' }}>
                  Confidence: {(analysis.sentiment.confidence * 100).toFixed(1)}%
                </span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: '#28a745', fontWeight: 'bold', fontSize: '18px' }}>
                    {(analysis.sentiment.scores.pos * 100).toFixed(1)}%
                  </div>
                  <div style={{ color: '#666', fontSize: '14px' }}>Positive</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: '#007bff', fontWeight: 'bold', fontSize: '18px' }}>
                    {(analysis.sentiment.scores.neu * 100).toFixed(1)}%
                  </div>
                  <div style={{ color: '#666', fontSize: '14px' }}>Neutral</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ color: '#dc3545', fontWeight: 'bold', fontSize: '18px' }}>
                    {(analysis.sentiment.scores.neg * 100).toFixed(1)}%
                  </div>
                  <div style={{ color: '#666', fontSize: '14px' }}>Negative</div>
                </div>
              </div>
            </div>
          </div>

          {/* Bias Detection */}
          <div className="card">
            <h3>🛡️ Bias Detection</h3>
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                <span style={{ fontSize: '20px' }}>
                  {analysis.bias_detection.is_biased ? '🚨' : '✅'}
                </span>
                <span style={{
                  padding: '6px 12px',
                  backgroundColor: analysis.bias_detection.is_biased ? '#dc3545' : '#28a745',
                  color: 'white',
                  borderRadius: '4px',
                  fontWeight: 'bold'
                }}>
                  {analysis.bias_detection.is_biased ? 'Bias Detected' : 'No Bias'}
                </span>
                <span style={{ color: '#666' }}>
                  Score: {(analysis.bias_detection.bias_score * 100).toFixed(1)}%
                </span>
              </div>

              {analysis.bias_detection.categories.length > 0 && (
                <div>
                  <h4 style={{ marginBottom: '10px', fontSize: '16px' }}>Detected Bias Categories:</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {analysis.bias_detection.categories.map((category, index) => (
                      <div key={index} style={{
                        padding: '15px',
                        backgroundColor: '#f8f9fa',
                        borderRadius: '8px',
                        border: '1px solid #dee2e6'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{
                            padding: '4px 8px',
                            backgroundColor: '#6c757d',
                            color: 'white',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: 'bold'
                          }}>
                            {category.category}
                          </span>
                          <span style={{ color: '#666', fontSize: '14px' }}>
                            {(category.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div style={{ fontSize: '14px', marginBottom: '4px' }}>
                          <strong>Keyword:</strong> {category.keyword}
                        </div>
                        <div style={{ fontSize: '14px', color: '#666' }}>
                          <strong>Context:</strong> {category.context}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Insights */}
          {analysis.insights.length > 0 && (
            <div className="card">
              <h3>💡 Key Insights</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysis.insights.map((insight, index) => (
                  <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ fontSize: '16px', marginTop: '2px' }}>💡</span>
                    <span style={{ fontSize: '14px' }}>{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {analysis.recommendations.length > 0 && (
            <div className="card">
              <h3>🔧 Recommendations</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysis.recommendations.map((recommendation, index) => (
                  <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ fontSize: '16px', marginTop: '2px' }}>🔧</span>
                    <span style={{ fontSize: '14px' }}>{recommendation}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Flagged Items */}
          {analysis.flagged_items.length > 0 && (
            <div className="card">
              <h3>📋 Flagged Items (for PDF Report)</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {analysis.flagged_items.map((item, index) => (
                  <div key={index} style={{
                    padding: '12px',
                    border: '1px solid #dee2e6',
                    borderRadius: '8px',
                    backgroundColor: '#f8f9fa'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{
                        padding: '4px 8px',
                        backgroundColor: getSeverityColor(item.severity),
                        color: 'white',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {item.severity.toUpperCase()}
                      </span>
                      <span style={{ color: '#666', fontSize: '12px' }}>
                        {(item.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '4px' }}>
                      {item.description}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {new Date(item.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UnifiedAnalysis;