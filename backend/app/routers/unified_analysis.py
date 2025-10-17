from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import InterviewSession, AnalysisResult
from ..security import get_current_user
from ..models import User

router = APIRouter()

class UnifiedAnalysisRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    user_id: Optional[int] = None

class UnifiedAnalysisResponse(BaseModel):
    # Overall analysis status
    has_issues: bool
    overall_score: float  # 0-1 scale, higher = more issues
    
    # Sentiment analysis
    sentiment: Dict[str, Any]
    
    # Bias detection
    bias_detection: Dict[str, Any]
    
    # Combined insights
    insights: List[str]
    recommendations: List[str]
    
    # Tracking for PDF report
    flagged_items: List[Dict[str, Any]]
    
    # Metadata
    processing_time_ms: float
    timestamp: str

# Global storage for flagged detections (in production, use database)
flagged_detections = []

def _get_sentiment_analysis(text: str) -> Dict[str, Any]:
    """Get sentiment analysis using VADER"""
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        
        # Determine primary sentiment
        if scores['compound'] >= 0.05:
            sentiment_label = "POSITIVE"
        elif scores['compound'] <= -0.05:
            sentiment_label = "NEGATIVE"
        else:
            sentiment_label = "NEUTRAL"
        
        return {
            "label": sentiment_label,
            "confidence": abs(scores['compound']),
            "scores": scores,
            "status": "success"
        }
    except Exception as e:
        return {
            "label": "NEUTRAL",
            "confidence": 0.0,
            "scores": {"pos": 0, "neu": 1, "neg": 0, "compound": 0},
            "status": "error",
            "error": str(e)
        }

def _get_bias_detection(text: str) -> Dict[str, Any]:
    """Get bias detection using real-time bias detection"""
    try:
        # Import the real-time bias detection function
        from .realtime_bias import _fast_lexicon_filter, _sentence_level_classification
        
        # Get lexicon-based bias detection
        lexicon_bias = _fast_lexicon_filter(text)
        
        # Get ML-based classification
        ml_biased, ml_confidence = _sentence_level_classification(text)
        
        # Determine if biased
        is_biased = len(lexicon_bias) > 0 or ml_biased
        confidence = max(
            max([detection["confidence"] for detection in lexicon_bias], default=0.0),
            ml_confidence
        )
        
        # Calculate bias score
        bias_score = 0.0
        if lexicon_bias:
            total_weight = sum(detection["weight"] * detection["confidence"] for detection in lexicon_bias)
            bias_score = min(total_weight / len(lexicon_bias), 1.0)
        
        return {
            "is_biased": is_biased,
            "confidence": confidence,
            "bias_score": bias_score,
            "categories": lexicon_bias,
            "status": "success"
        }
    except Exception as e:
        return {
            "is_biased": False,
            "confidence": 0.0,
            "bias_score": 0.0,
            "categories": [],
            "status": "error",
            "error": str(e)
        }

def _generate_insights(sentiment: Dict[str, Any], bias: Dict[str, Any]) -> List[str]:
    """Generate insights based on sentiment and bias analysis"""
    insights = []
    
    # Sentiment insights
    if sentiment["label"] == "NEGATIVE" and sentiment["confidence"] > 0.5:
        insights.append("⚠️ Negative sentiment detected with high confidence")
    elif sentiment["label"] == "POSITIVE" and sentiment["confidence"] > 0.5:
        insights.append("✅ Positive sentiment detected")
    
    # Bias insights
    if bias["is_biased"]:
        insights.append("🚨 Potential bias detected in the text")
        if bias["categories"]:
            categories = [cat["category"] for cat in bias["categories"]]
            insights.append(f"📋 Detected bias categories: {', '.join(set(categories))}")
    
    # Combined insights
    if sentiment["label"] == "NEGATIVE" and bias["is_biased"]:
        insights.append("⚠️ Combined negative sentiment and bias detected - requires attention")
    
    return insights

def _generate_recommendations(sentiment: Dict[str, Any], bias: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on analysis"""
    recommendations = []
    
    # Sentiment recommendations
    if sentiment["label"] == "NEGATIVE" and sentiment["confidence"] > 0.5:
        recommendations.append("Consider using more neutral or positive language")
    
    # Bias recommendations
    if bias["is_biased"]:
        recommendations.append("Review text for potential bias and use inclusive language")
        if bias["categories"]:
            for category in bias["categories"]:
                if category["category"] == "gender_bias":
                    recommendations.append("Avoid gender-specific language or assumptions")
                elif category["category"] == "age_bias":
                    recommendations.append("Focus on skills and experience rather than age")
    
    # General recommendations
    if not bias["is_biased"] and sentiment["label"] == "POSITIVE":
        recommendations.append("Text appears unbiased and positive - good to go!")
    
    return recommendations

def _track_flagged_detection(text: str, sentiment: Dict[str, Any], bias: Dict[str, Any], session_id: Optional[str] = None):
    """Track flagged detections for PDF report"""
    global flagged_detections
    
    flagged_items = []
    
    # Track negative sentiment
    if sentiment["label"] == "NEGATIVE" and sentiment["confidence"] > 0.5:
        flagged_items.append({
            "type": "negative_sentiment",
            "severity": "medium",
            "confidence": sentiment["confidence"],
            "description": f"Negative sentiment detected (confidence: {sentiment['confidence']:.2f})",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        })
    
    # Track bias detection
    if bias["is_biased"]:
        for category in bias["categories"]:
            flagged_items.append({
                "type": "bias_detection",
                "severity": "high",
                "confidence": category["confidence"],
                "category": category["category"],
                "description": f"{category['category']} bias detected: {category['keyword']}",
                "context": category.get("context", ""),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            })
    
    # Add to global tracking
    flagged_detections.extend(flagged_items)
    
    return flagged_items

@router.post("/analyze", response_model=UnifiedAnalysisResponse)
def unified_analysis(
    request: UnifiedAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unified analysis combining sentiment and bias detection"""
    start_time = time.time()
    
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Perform sentiment analysis
        sentiment = _get_sentiment_analysis(text)
        
        # Perform bias detection
        bias = _get_bias_detection(text)
        
        # Generate insights
        insights = _generate_insights(sentiment, bias)
        
        # Generate recommendations
        recommendations = _generate_recommendations(sentiment, bias)
        
        # Track flagged detections
        flagged_items = _track_flagged_detection(text, sentiment, bias, request.session_id)
        
        # Calculate overall score (higher = more issues)
        overall_score = 0.0
        if sentiment["label"] == "NEGATIVE":
            overall_score += sentiment["confidence"] * 0.4
        if bias["is_biased"]:
            overall_score += bias["bias_score"] * 0.6
        
        # Determine if there are issues
        has_issues = overall_score > 0.3 or len(flagged_items) > 0
        
        processing_time = (time.time() - start_time) * 1000
        
        # Save analysis result to database if session_id provided
        if request.session_id:
            try:
                analysis_result = AnalysisResult(
                    session_id=request.session_id,
                    analysis_type="unified",
                    result_data={
                        "sentiment": sentiment,
                        "bias": bias,
                        "insights": insights,
                        "recommendations": recommendations,
                        "flagged_items": flagged_items,
                        "overall_score": overall_score,
                        "has_issues": has_issues
                    },
                    created_at=datetime.now()
                )
                db.add(analysis_result)
                db.commit()
            except Exception as e:
                print(f"Error saving analysis result: {e}")
        
        return UnifiedAnalysisResponse(
            has_issues=has_issues,
            overall_score=overall_score,
            sentiment=sentiment,
            bias_detection=bias,
            insights=insights,
            recommendations=recommendations,
            flagged_items=flagged_items,
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/analyze-public", response_model=UnifiedAnalysisResponse)
def unified_analysis_public(request: UnifiedAnalysisRequest):
    """Public unified analysis (no authentication required for testing)"""
    start_time = time.time()
    
    try:
        text = request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Perform sentiment analysis
        sentiment = _get_sentiment_analysis(text)
        
        # Perform bias detection
        bias = _get_bias_detection(text)
        
        # Generate insights
        insights = _generate_insights(sentiment, bias)
        
        # Generate recommendations
        recommendations = _generate_recommendations(sentiment, bias)
        
        # Track flagged detections (no session_id for public endpoint)
        flagged_items = _track_flagged_detection(text, sentiment, bias, None)
        
        # Calculate overall score (higher = more issues)
        overall_score = 0.0
        if sentiment["label"] == "NEGATIVE":
            overall_score += sentiment["confidence"] * 0.4
        if bias["is_biased"]:
            overall_score += bias["bias_score"] * 0.6
        
        # Determine if there are issues
        has_issues = overall_score > 0.3 or len(flagged_items) > 0
        
        processing_time = (time.time() - start_time) * 1000
        
        return UnifiedAnalysisResponse(
            has_issues=has_issues,
            overall_score=overall_score,
            sentiment=sentiment,
            bias_detection=bias,
            insights=insights,
            recommendations=recommendations,
            flagged_items=flagged_items,
            processing_time_ms=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/flagged-detections")
def get_flagged_detections(current_user: User = Depends(get_current_user)):
    """Get all flagged detections for PDF report generation"""
    global flagged_detections
    
    # Filter by user if needed (in production, use database)
    user_flagged = [item for item in flagged_detections if item.get("user_id") == current_user.id]
    
    return {
        "total_flagged": len(user_flagged),
        "flagged_items": user_flagged,
        "summary": {
            "negative_sentiment": len([item for item in user_flagged if item["type"] == "negative_sentiment"]),
            "bias_detection": len([item for item in user_flagged if item["type"] == "bias_detection"])
        }
    }

@router.delete("/clear-flagged-detections")
def clear_flagged_detections(current_user: User = Depends(get_current_user)):
    """Clear flagged detections (for testing purposes)"""
    global flagged_detections
    flagged_detections = []
    return {"message": "Flagged detections cleared successfully"}
