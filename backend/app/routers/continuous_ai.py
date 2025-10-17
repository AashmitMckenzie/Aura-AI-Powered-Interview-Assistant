from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import os
import time
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
# Conditional imports to avoid heavy ML library loading issues on startup
WHISPER_AVAILABLE = False
whisper = None

def _safe_import_whisper():
    """Safely import whisper with comprehensive error handling"""
    global WHISPER_AVAILABLE, whisper
    try:
        import whisper
        WHISPER_AVAILABLE = True
        whisper = whisper
        print("SUCCESS: Whisper loaded successfully in continuous_ai")
        return True
    except ImportError as e:
        print(f"WARNING:  Whisper not available: {e}")
        WHISPER_AVAILABLE = False
        whisper = None
        return False
    except Exception as e:
        print(f"WARNING:  Whisper failed to load due to system issues: {e}")
        print("WARNING:  This is likely due to torch/DLL compatibility issues on Windows")
        print("WARNING:  Whisper functionality will be disabled")
        WHISPER_AVAILABLE = False
        whisper = None
        return False

# Try to import whisper safely
_safe_import_whisper()

TORCH_AVAILABLE = False
torch = None

def _safe_import_torch():
    """Safely import torch with comprehensive error handling"""
    global TORCH_AVAILABLE, torch
    try:
        import torch
        TORCH_AVAILABLE = True
        torch = torch
        print("SUCCESS: Torch loaded successfully in continuous_ai")
        return True
    except ImportError as e:
        print(f"WARNING:  Torch not available: {e}")
        TORCH_AVAILABLE = False
        torch = None
        return False
    except Exception as e:
        print(f"WARNING:  Torch failed to load due to system issues: {e}")
        print("WARNING:  This is likely due to DLL compatibility issues on Windows")
        TORCH_AVAILABLE = False
        torch = None
        return False

# Try to import torch safely
_safe_import_torch()

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

WHISPER_MODEL_DIR = os.path.join(os.getcwd(), "models", "whisper")

router = APIRouter()

class RealTimeTextPayload(BaseModel):
    text: str
    timestamp: Optional[float] = None
    session_id: Optional[int] = None

# Global model instances
vader_analyzer = None
whisper_model = None

class TextPayload(BaseModel):
    text: str

def _load_vader_analyzer():
    """Load VADER sentiment analyzer"""
    global vader_analyzer
    if vader_analyzer is None:
        try:
            vader_analyzer = SentimentIntensityAnalyzer()
            print("SUCCESS: VADER sentiment analyzer loaded successfully")
        except Exception as e:
            print(f"ERROR: Failed to load VADER: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load VADER sentiment analyzer: {e}")
    return vader_analyzer

def _load_whisper_model():
    """Load OpenAI Whisper model - using tiny model for fastest transcription"""
    global whisper_model
    if not WHISPER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Whisper is not available. Please install openai-whisper package.")
    
    if whisper_model is None:
        try:
            # Ensure model directory exists
            os.makedirs(WHISPER_MODEL_DIR, exist_ok=True)
            # Use tiny model for fastest transcription
            whisper_model = whisper.load_model("tiny", download_root=WHISPER_MODEL_DIR)
            print("SUCCESS: OpenAI Whisper tiny model loaded successfully (optimized for continuous processing)")
        except Exception as e:
            print(f"ERROR: Failed to load Whisper: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load Whisper model: {e}")
    return whisper_model

def detect_bias_detailed(text: str):
    """Enhanced bias detection with exact location detection"""
    try:
        # Enhanced rule-based checks for interview-specific bias with exact locations
        bias_patterns = {
            "gender": {
                "keywords": ["man", "woman", "female", "male", "pregnant", "mother", "father", "girl", "boy", "lady", "gentleman"],
                "contexts": ["prefer", "only", "must be", "should be", "typically", "usually", "generally"]
            },
            "age": {
                "keywords": ["young", "old", "age", "retire", "millennial", "gen z", "boomer", "senior", "junior", "fresh", "experienced"],
                "contexts": ["too", "not suitable", "prefer", "only", "must be"]
            },
            "ethnicity": {
                "keywords": ["race", "ethnicity", "nationality", "accent", "background", "origin", "culture"],
                "contexts": ["prefer", "only", "must be", "should be", "typically"]
            },
            "religion": {
                "keywords": ["religion", "christian", "muslim", "jewish", "hindu", "buddhist", "faith", "belief"],
                "contexts": ["prefer", "only", "must be", "should be", "typically"]
            },
            "disability": {
                "keywords": ["disabled", "handicap", "mental", "autism", "wheelchair", "blind", "deaf", "limitation"],
                "contexts": ["prefer", "only", "must be", "should be", "not suitable", "cannot"]
            },
            "appearance": {
                "keywords": ["attractive", "good looking", "professional appearance", "dress", "style", "image"],
                "contexts": ["must be", "should be", "prefer", "only", "typically"]
            }
        }
        
        text_lower = text.lower()
        words = text.split()
        bias_locations = []
        flagged = False
        detected_labels = []
        
        for category, patterns in bias_patterns.items():
            for keyword in patterns["keywords"]:
                if keyword in text_lower:
                    # Find exact position and context
                    keyword_pos = text_lower.find(keyword)
                    
                    # Look for context words around the keyword
                    keyword_index = -1
                    for i, word in enumerate(words):
                        if keyword in word.lower():
                            keyword_index = i
                            break
                    
                    if keyword_index >= 0:
                        # Get context (3 words before and after)
                        start = max(0, keyword_index - 3)
                        end = min(len(words), keyword_index + 4)
                        context = " ".join(words[start:end])
                        
                        # Check if any context words are present
                        context_found = any(ctx in text_lower for ctx in patterns["contexts"])
                        
                        if context_found:
                            bias_location = {
                                "category": category,
                                "keyword": keyword,
                                "position": keyword_pos,
                                "context": context,
                                "severity": "high" if context_found else "medium",
                                "explanation": f"Potential {category} bias detected with keyword '{keyword}' in context: '{context}'"
                            }
                            bias_locations.append(bias_location)
                            flagged = True
                            detected_labels.append(f"{category}: {keyword} (context: {context})")
        
        # Additional pattern-based detection for interview bias
        import re
        interview_bias_patterns = [
            r"\b(only|must|should)\s+(men|women|males?|females?)\b",
            r"\b(prefer|want)\s+(young|old|experienced|fresh)\b",
            r"\b(typically|usually|generally)\s+(men|women|young|old)\b",
            r"\b(not suitable|cannot)\s+(because|due to)\s+(age|gender|race|religion)\b"
        ]
        
        for pattern in interview_bias_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                bias_location = {
                    "category": "interview_bias",
                    "pattern": pattern,
                    "match": match.group(),
                    "position": match.start(),
                    "severity": "high",
                    "explanation": f"Interview bias pattern detected: '{match.group()}' - This may indicate discriminatory language"
                }
                bias_locations.append(bias_location)
                flagged = True
                detected_labels.append(f"Interview bias: {match.group()}")
        
        return {
            "flagged": flagged,
            "locations": bias_locations,
            "detected_labels": detected_labels,
            "detailed_analysis": {
                "total_issues": len(bias_locations),
                "high_severity": len([b for b in bias_locations if b.get("severity") == "high"]),
                "categories_affected": list(set([b["category"] for b in bias_locations]))
            }
        }
        
    except Exception as e:
        print(f"Bias detection error: {e}")
        return {
            "flagged": False,
            "locations": [],
            "detected_labels": [],
            "error": str(e)
        }

@router.post("/analyze-realtime")
def analyze_realtime_text(payload: RealTimeTextPayload):
    """Real-time analysis of text as user speaks each phrase"""
    try:
        start_time = time.time()
        text = payload.text.strip()
        
        if not text:
            return {
                "text": "",
                "sentiment": {"label": "NEUTRAL", "score": 0.5, "confidence": 0.0},
                "bias": {"flagged": False, "confidence": 0.0, "categories": []},
                "processing_time_ms": 0,
                "timestamp": payload.timestamp or time.time()
            }
        
        # Fast sentiment analysis using VADER
        sentiment_result = None
        bias_result = None
        
        try:
            # Sentiment analysis
            analyzer = _load_vader_analyzer()
            scores = analyzer.polarity_scores(text)
            
            compound_score = scores['compound']
            if compound_score >= 0.05:
                label = "POSITIVE"
                confidence = compound_score
                status = "Optimistic and confident language detected"
            elif compound_score <= -0.05:
                label = "NEGATIVE"
                confidence = abs(compound_score)
                status = "Concerned or uncertain language detected"
            else:
                label = "NEUTRAL"
                confidence = 0.5
                status = "Balanced and factual language"
            
            sentiment_result = {
                "label": label,
                "score": confidence,
                "confidence": confidence,
                "scores": {
                    "pos": scores['pos'],
                    "neu": scores['neu'],
                    "neg": scores['neg'],
                    "compound": compound_score
                },
                "status": status
            }
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            sentiment_result = {
                "label": "NEUTRAL",
                "score": 0.5,
                "confidence": 0.0,
                "status": "Unable to analyze sentiment"
            }
        
        try:
            # Fast bias detection using rule-based approach
            bias_result = _detect_bias_fast(text)
            
        except Exception as e:
            print(f"Bias detection error: {e}")
            bias_result = {
                "flagged": False,
                "confidence": 0.0,
                "categories": [],
                "status": "Unable to detect bias"
            }
        
        processing_time = (time.time() - start_time) * 1000
        
        # Determine if there are any issues
        has_issues = (
            (sentiment_result and sentiment_result["label"] == "NEGATIVE" and sentiment_result["confidence"] > 0.3) or
            (bias_result and bias_result["flagged"])
        )
        
        # Generate insights
        insights = []
        if sentiment_result["label"] == "POSITIVE":
            insights.append("Positive and confident response")
        elif sentiment_result["label"] == "NEGATIVE":
            insights.append("Consider maintaining a more positive tone")
        
        if bias_result["flagged"]:
            insights.append("Potential bias detected - review language")
        
        # Generate recommendations
        recommendations = []
        if sentiment_result["confidence"] > 0.7:
            if sentiment_result["label"] == "NEGATIVE":
                recommendations.append("Consider using more neutral language")
                recommendations.append("Focus on objective facts rather than emotions")
        if bias_result["flagged"]:
            recommendations.append("Avoid assumptions about personal characteristics")
            recommendations.append("Use inclusive and objective language")
        
        return {
            "text": text,
            "sentiment": sentiment_result,
            "bias_detection": bias_result,
            "has_issues": has_issues,
            "overall_score": sentiment_result["confidence"],
            "insights": insights,
            "recommendations": recommendations,
            "processing_time_ms": processing_time,
            "timestamp": payload.timestamp or time.time()
        }
        
    except Exception as e:
        print(f"Real-time analysis error: {e}")
        return {
            "text": payload.text,
            "sentiment": {"label": "NEUTRAL", "score": 0.5, "confidence": 0.0},
            "bias_detection": {"flagged": False, "confidence": 0.0, "categories": []},
            "has_issues": False,
            "overall_score": 0.5,
            "insights": [],
            "recommendations": [],
            "processing_time_ms": 0,
            "timestamp": payload.timestamp or time.time(),
            "error": str(e)
        }

def _detect_bias_fast(text: str) -> dict:
    """Fast rule-based bias detection for real-time analysis"""
    text_lower = text.lower()
    
    # Quick bias patterns
    bias_patterns = {
        "gender": ["man", "woman", "female", "male", "pregnant", "mother", "father", "girl", "boy"],
        "age": ["young", "old", "age", "retire", "millennial", "gen z", "boomer", "senior", "junior"],
        "ethnicity": ["race", "ethnicity", "nationality", "accent", "background", "origin", "foreign"],
        "religion": ["religion", "christian", "muslim", "jewish", "hindu", "buddhist", "faith"],
        "disability": ["disabled", "handicap", "mental", "autism", "wheelchair", "blind", "deaf"]
    }
    
    negative_words = ["prefer", "only", "must", "should", "typically", "usually", "not good", "not suitable"]
    
    detected_categories = []
    flagged = False
    
    for category, keywords in bias_patterns.items():
        for keyword in keywords:
            if keyword in text_lower:
                # Check for negative context
                context_found = any(neg_word in text_lower for neg_word in negative_words)
                if context_found:
                    detected_categories.append({
                        "category": category,
                        "keyword": keyword,
                        "context": "negative language detected",
                        "confidence": 0.8,
                        "weight": 1.0,
                        "description": f"Potential {category} bias with keyword '{keyword}'"
                    })
                    flagged = True
    
    return {
        "flagged": flagged,
        "confidence": 0.8 if flagged else 0.0,
        "bias_score": 0.8 if flagged else 0.0,
        "categories": detected_categories,
        "status": "Bias detected" if flagged else "No bias detected"
    }

@router.post("/transcribe-continuous")
async def transcribe_continuous_audio(file: UploadFile = File(...)):
    """Continuous real-time transcription with immediate bias detection"""
    try:
        # Load the Whisper model
        model = _load_whisper_model()
        
        # Save upload to temp file
        tmp_path = os.path.join(WHISPER_MODEL_DIR, f"continuous_upload_{os.getpid()}_{file.filename}")
        with open(tmp_path, "wb") as out:
            content = await file.read()
            out.write(content)
        
        print(f"Continuous transcribing audio file: {tmp_path} (size: {len(content)} bytes)")
        
        # Ultra-fast transcription optimized for continuous processing
        result = model.transcribe(
            tmp_path, 
            language="en",
            fp16=False,
            verbose=False,
            word_timestamps=False,
            condition_on_previous_text=False,
            initial_prompt=None,
            temperature=0.0,
            no_speech_threshold=0.2,  # Very low threshold for immediate detection
            logprob_threshold=-1.0,   # Very low threshold for immediate detection
            compression_ratio_threshold=1.2  # Very low threshold for immediate detection
        )
        text = result.get("text", "").strip()
        
        # Perform immediate sentiment and bias analysis
        sentiment_result = None
        bias_result = None
        
        if text:
            try:
                # Sentiment analysis
                analyzer = _load_vader_analyzer()
                scores = analyzer.polarity_scores(text)
                
                compound_score = scores['compound']
                if compound_score >= 0.05:
                    label = "POSITIVE"
                    score = compound_score
                    justification = f"Positive sentiment detected (score: {compound_score:.3f}). The text contains optimistic, confident, or enthusiastic language."
                elif compound_score <= -0.05:
                    label = "NEGATIVE"
                    score = abs(compound_score)
                    justification = f"Negative sentiment detected (score: {compound_score:.3f}). The text contains pessimistic, uncertain, or concerned language."
                else:
                    label = "NEUTRAL"
                    score = 0.5
                    justification = f"Neutral sentiment detected (score: {compound_score:.3f}). The text maintains a balanced, factual tone without strong emotional indicators."
                
                sentiment_result = {
                    "label": label,
                    "score": score,
                    "justification": justification,
                    "vader_scores": scores,
                    "confidence": abs(compound_score)
                }
                
                # Bias analysis
                bias_analysis = detect_bias_detailed(text)
                bias_result = {
                    "flagged": bias_analysis["flagged"],
                    "locations": bias_analysis["locations"],
                    "analysis": bias_analysis["detailed_analysis"],
                    "explanation": f"Found {bias_analysis['detailed_analysis']['total_issues']} potential bias issues" if bias_analysis["flagged"] else "No bias detected"
                }
                
            except Exception as e:
                print(f"Analysis error: {e}")
                sentiment_result = {
                    "label": "NEUTRAL",
                    "score": 0.5,
                    "justification": "Unable to analyze sentiment due to processing error.",
                    "error": str(e)
                }
                bias_result = {
                    "flagged": False,
                    "confidence": 0.0,
                    "locations": [],
                    "explanation": "Unable to analyze bias due to processing error."
                }
        
        print(f"Continuous transcription result: '{text}' with sentiment: {sentiment_result['label'] if sentiment_result else 'N/A'} and bias: {'flagged' if bias_result and bias_result['flagged'] else 'clean'}")
        
        return {
            "text": text,
            "language": result.get("language", "en"),
            "sentiment": sentiment_result,
            "bias": bias_result,
            "processing_time": "continuous",
            "timestamp": int(time.time() * 1000)
        }
        
    except Exception as exc:
        print(f"Continuous transcription error: {exc}")
        from ..error_handlers import secure_http_exception
        raise secure_http_exception(500, "Continuous transcription failed")
    finally:
        # Clean up temp file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Cleaned up temp file: {tmp_path}")
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")
