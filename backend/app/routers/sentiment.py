from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

router = APIRouter()

# Global model instance
vader_analyzer = None

def _load_vader_analyzer():
    """Load VADER sentiment analyzer"""
    global vader_analyzer
    if vader_analyzer is None:
        try:
            vader_analyzer = SentimentIntensityAnalyzer()
            print("✅ VADER sentiment analyzer loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load VADER: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load VADER sentiment analyzer: {e}")
    return vader_analyzer

@router.post("/session-sentiment")
def analyze_session_sentiment(payload: dict):
    """Analyze overall session sentiment based on all transcriptions"""
    try:
        transcript_items = payload.get("transcript_items", [])
        if not transcript_items:
            return {
                "overall_sentiment": "NEUTRAL",
                "overall_score": 0.5,
                "justification": "No transcript data available for analysis.",
                "detailed_analysis": [],
                "confidence": 0.0
            }
        
        analyzer = _load_vader_analyzer()
        
        # Analyze each transcript item
        detailed_analysis = []
        total_positive = 0
        total_negative = 0
        total_neutral = 0
        weighted_scores = []
        
        for item in transcript_items:
            text = item.get("text", "")
            if not text.strip():
                continue
                
            scores = analyzer.polarity_scores(text)
            compound_score = scores['compound']
            
            if compound_score >= 0.05:
                label = "POSITIVE"
                total_positive += 1
            elif compound_score <= -0.05:
                label = "NEGATIVE"
                total_negative += 1
            else:
                label = "NEUTRAL"
                total_neutral += 1
            
            # Weight by text length (longer responses have more impact)
            weight = len(text.split())
            weighted_scores.append(compound_score * weight)
            
            detailed_analysis.append({
                "text": text[:100] + "..." if len(text) > 100 else text,
                "sentiment": label,
                "score": abs(compound_score),
                "confidence": abs(compound_score),
                "word_count": len(text.split())
            })
        
        # Calculate overall sentiment
        if not weighted_scores:
            overall_score = 0.5
            overall_sentiment = "NEUTRAL"
        else:
            overall_score = sum(weighted_scores) / sum(len(item.get("text", "").split()) for item in transcript_items if item.get("text", "").strip())
            overall_score = max(-1, min(1, overall_score))  # Clamp between -1 and 1
            
            if overall_score >= 0.05:
                overall_sentiment = "POSITIVE"
            elif overall_score <= -0.05:
                overall_sentiment = "NEGATIVE"
            else:
                overall_sentiment = "NEUTRAL"
        
        # Generate comprehensive justification
        total_items = len([item for item in transcript_items if item.get("text", "").strip()])
        positive_pct = (total_positive / total_items * 100) if total_items > 0 else 0
        negative_pct = (total_negative / total_items * 100) if total_items > 0 else 0
        neutral_pct = (total_neutral / total_items * 100) if total_items > 0 else 0
        
        justification = f"""
Overall Session Analysis:
• Total responses analyzed: {total_items}
• Positive responses: {total_positive} ({positive_pct:.1f}%)
• Negative responses: {total_negative} ({negative_pct:.1f}%)
• Neutral responses: {total_neutral} ({neutral_pct:.1f}%)

Overall sentiment: {overall_sentiment} (score: {overall_score:.3f})

Analysis: The candidate's responses show a {overall_sentiment.lower()} tone throughout the interview. 
This suggests {'confidence and enthusiasm' if overall_sentiment == 'POSITIVE' else 'concern or uncertainty' if overall_sentiment == 'NEGATIVE' else 'a balanced, professional approach'} in their communication style.
        """.strip()
        
        return {
            "overall_sentiment": overall_sentiment,
            "overall_score": abs(overall_score),
            "justification": justification,
            "detailed_analysis": detailed_analysis,
            "confidence": abs(overall_score),
            "statistics": {
                "total_responses": total_items,
                "positive_count": total_positive,
                "negative_count": total_negative,
                "neutral_count": total_neutral,
                "positive_percentage": positive_pct,
                "negative_percentage": negative_pct,
                "neutral_percentage": neutral_pct
            }
        }
        
    except Exception as e:
        print(f"Session sentiment analysis error: {e}")
        return {
            "overall_sentiment": "NEUTRAL",
            "overall_score": 0.5,
            "justification": f"Error analyzing session sentiment: {str(e)}",
            "detailed_analysis": [],
            "confidence": 0.0,
            "error": str(e)
        }

