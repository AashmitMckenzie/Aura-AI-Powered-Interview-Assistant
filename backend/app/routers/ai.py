from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import os
import time
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from ..security_utils import rate_limit

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
        print("Whisper loaded successfully")
        return True
    except ImportError as e:
        print(f"WARNING: Whisper not available: {e}")
        WHISPER_AVAILABLE = False
        whisper = None
        return False
    except Exception as e:
        print(f"WARNING: Whisper failed to load due to system issues: {e}")
        print("WARNING: This is likely due to torch/DLL compatibility issues on Windows")
        print("WARNING: Whisper functionality will be disabled")
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
        print("Torch loaded successfully")
        return True
    except ImportError as e:
        print(f"WARNING: Torch not available: {e}")
        TORCH_AVAILABLE = False
        torch = None
        return False
    except Exception as e:
        print(f"WARNING: Torch failed to load due to system issues: {e}")
        print("WARNING: This is likely due to DLL compatibility issues on Windows")
        TORCH_AVAILABLE = False
        torch = None
        return False

# Try to import torch safely
_safe_import_torch()

# Check if transformers can be imported without loading TensorFlow
TRANSFORMERS_AVAILABLE = False
pipeline = None

def _check_transformers_availability():
    """Check if transformers is available without importing it"""
    global TRANSFORMERS_AVAILABLE, pipeline
    if TRANSFORMERS_AVAILABLE:
        return True
    
    try:
        import importlib.util
        spec = importlib.util.find_spec("transformers")
        if spec is None:
            print("WARNING:  Transformers package not found")
            return False
        
        # Try to import just the pipeline function dynamically
        transformers_module = importlib.import_module("transformers")
        pipeline = getattr(transformers_module, "pipeline", None)
        if pipeline is None:
            print("WARNING:  Transformers pipeline function not found")
            return False
            
        TRANSFORMERS_AVAILABLE = True
        print("SUCCESS: Transformers available for bias detection")
        return True
    except Exception as e:
        print(f"WARNING:  Transformers not available: {e}")
        TRANSFORMERS_AVAILABLE = False
        pipeline = None
        return False

# Download required NLTK data
try:
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

WHISPER_MODEL_DIR = os.path.join(os.getcwd(), "models", "whisper")

router = APIRouter()

# Global model instances
vader_analyzer = None
whisper_model = None
bias_pipeline = None

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
    """Load OpenAI Whisper model - using tiny model for faster transcription"""
    global whisper_model
    if not WHISPER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Whisper is not available. Please install openai-whisper package.")
    
    if whisper_model is None:
        try:
            # Ensure model directory exists
            os.makedirs(WHISPER_MODEL_DIR, exist_ok=True)
            # Use tiny model for faster transcription (trade-off: slightly less accuracy)
            whisper_model = whisper.load_model("tiny", download_root=WHISPER_MODEL_DIR)
            print("SUCCESS: OpenAI Whisper tiny model loaded successfully (optimized for speed)")
        except Exception as e:
            print(f"ERROR: Failed to load Whisper: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load Whisper model: {e}")
    return whisper_model

def _load_bias_pipeline():
    """Load Hugging Face bias/toxicity detection pipeline"""
    global bias_pipeline
    
    # Check if transformers is available
    if not _check_transformers_availability():
        print("WARNING:  Transformers not available, using rule-based bias detection only")
        return None
    
    if bias_pipeline is None:
        try:
            # Use a comprehensive bias detection model
            bias_pipeline = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                return_all_scores=True
            )
            print("SUCCESS: Hugging Face bias detection model loaded successfully")
        except Exception as e:
            print(f"ERROR: Failed to load bias detection model: {e}")
            # Fallback to a simpler model
            try:
                bias_pipeline = pipeline(
                    "text-classification",
                    model="cardiffnlp/twitter-roberta-base-offensive",
                    return_all_scores=True
                )
                print("SUCCESS: Fallback bias detection model loaded successfully")
            except Exception as e2:
                print(f"ERROR: Fallback bias detection also failed: {e2}")
                print("WARNING:  Using rule-based bias detection only")
                bias_pipeline = None
    return bias_pipeline


@router.post("/sentiment")
def analyze_sentiment(payload: TextPayload):
    """Analyze sentiment using VADER (NLTK)"""
    try:
        analyzer = _load_vader_analyzer()
        scores = analyzer.polarity_scores(payload.text)
        
        # Convert VADER scores to standard format
        compound_score = scores['compound']
        
        if compound_score >= 0.05:
            label = "POSITIVE"
            score = compound_score
        elif compound_score <= -0.05:
            label = "NEGATIVE"
            score = abs(compound_score)
        else:
            label = "NEUTRAL"
            score = 0.5
            
        result = [{
            "label": label,
            "score": score,
            "vader_scores": scores
        }]
        
        return {"result": result}
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        # Fallback to simple analysis
        return {"result": [{"label": "NEUTRAL", "score": 0.5, "error": str(e)}]}


@router.post("/bias")
def detect_bias(payload: TextPayload):
    """Detect bias and toxicity with exact location detection"""
    try:
        bias_pipeline = _load_bias_pipeline()
        
        # Process results from the model if available
        flagged = False
        max_score = 0.0
        detected_labels = []
        bias_locations = []
        results = []
        
        if bias_pipeline is not None:
            try:
                results = bias_pipeline(payload.text)
                
                for result in results:
                    label = result['label']
                    score = result['score']
                    
                    # Check for toxic/bias-related labels
                    toxic_labels = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate', 'offensive']
                    if any(toxic in label.lower() for toxic in toxic_labels):
                        flagged = True
                        detected_labels.append(f"{label}: {score:.3f}")
                        max_score = max(max_score, score)
            except Exception as e:
                print(f"Error running bias pipeline: {e}")
                results = []
        
        # Enhanced rule-based checks for interview-specific bias with exact locations
        bias_patterns = {
            "gender": {
                "keywords": ["man", "woman", "female", "male", "pregnant", "mother", "father", "girl", "boy", "lady", "gentleman", "women", "men"],
                "contexts": ["prefer", "only", "must be", "should be", "typically", "usually", "generally", "not good", "not suitable", "shouldn't", "can't", "cannot", "too"]
            },
            "age": {
                "keywords": ["young", "old", "age", "retire", "millennial", "gen z", "boomer", "senior", "junior", "fresh", "experienced", "aged"],
                "contexts": ["too", "not suitable", "prefer", "only", "must be", "shouldn't", "can't", "cannot", "not good"]
            },
            "ethnicity": {
                "keywords": ["race", "ethnicity", "nationality", "accent", "background", "origin", "culture", "foreign", "immigrant"],
                "contexts": ["prefer", "only", "must be", "should be", "typically", "not suitable", "shouldn't"]
            },
            "religion": {
                "keywords": ["religion", "christian", "muslim", "jewish", "hindu", "buddhist", "faith", "belief", "religious"],
                "contexts": ["prefer", "only", "must be", "should be", "typically", "not suitable"]
            },
            "disability": {
                "keywords": ["disabled", "handicap", "mental", "autism", "wheelchair", "blind", "deaf", "limitation", "handicapped"],
                "contexts": ["prefer", "only", "must be", "should be", "not suitable", "cannot", "can't"]
            },
            "appearance": {
                "keywords": ["attractive", "good looking", "professional appearance", "dress", "style", "image", "beautiful", "handsome"],
                "contexts": ["must be", "should be", "prefer", "only", "typically", "not suitable"]
            }
        }
        
        text_lower = payload.text.lower()
        words = payload.text.split()
        
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
                        
                        # More sensitive detection - flag if keyword is present with any negative context
                        if context_found or any(neg_word in text_lower for neg_word in ["not", "no", "shouldn't", "can't", "cannot", "too", "only", "prefer"]):
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
        interview_bias_patterns = [
            r"\b(only|must|should|shouldn't|can't|cannot)\s+(men|women|males?|females?)\b",
            r"\b(prefer|want|don't want|don't prefer)\s+(young|old|experienced|fresh)\b",
            r"\b(typically|usually|generally)\s+(men|women|young|old)\b",
            r"\b(not suitable|cannot|can't)\s+(because|due to)\s+(age|gender|race|religion)\b",
            r"\b(we|they|you)\s+(shouldn't|can't|cannot|don't)\s+(hire|employ)\s+(women|men|young|old)\b",
            r"\b(too)\s+(young|old|experienced|fresh)\b",
            r"\b(not good|not suitable|not appropriate)\s+(for|at)\b"
        ]
        
        import re
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
            "confidence": max_score,
            "detected_labels": detected_labels,
            "bias_locations": bias_locations,
            "detailed_analysis": {
                "total_issues": len(bias_locations),
                "high_severity": len([b for b in bias_locations if b.get("severity") == "high"]),
                "categories_affected": list(set([b["category"] for b in bias_locations])),
            "raw_results": results
            }
        }
        
    except Exception as e:
        print(f"Bias detection error: {e}")
        # Fallback to simple rule-based detection
        text_lower = payload.text.lower()
        bias_words = ["prefer", "only", "must", "require", "not"]
        flagged = any(word in text_lower for word in bias_words)
        return {
            "flagged": flagged,
            "confidence": 0.5 if flagged else 0.0,
            "detected_labels": ["fallback_detection"] if flagged else [],
            "bias_locations": [],
            "error": str(e)
        }


@router.post("/transcribe")
@rate_limit(requests_per_minute=20)  # Security: Limit transcription requests
async def transcribe_audio(file: UploadFile = File(...), whisper_model: str = Form("tiny")):
    """Transcribe audio using OpenAI Whisper - optimized for speed"""
    try:
        # Check if Whisper is available
        if not WHISPER_AVAILABLE:
            raise HTTPException(status_code=503, detail="Audio transcription is not available. Whisper package is not installed.")
        
        # Security validation
        from ..security_utils import SecurityUtils
        SecurityUtils.validate_audio_file(file, max_size_mb=50)
        
        # Load the Whisper model
        model = _load_whisper_model()
        
        # Generate secure filename
        secure_filename = SecurityUtils.generate_secure_filename(file.filename or "audio.webm")
        tmp_path = os.path.join(WHISPER_MODEL_DIR, secure_filename)
        
        # Save upload to temp file with size validation
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=413, detail="File too large. Maximum 50MB allowed.")
        
        with open(tmp_path, "wb") as out:
            out.write(content)
        
        print(f"Transcribing audio file: {tmp_path} (size: {len(content)} bytes)")
        
        # Transcribe using Whisper with optimized settings for speed
        result = model.transcribe(
            tmp_path, 
            language="en",
            fp16=False,  # Use fp32 for better compatibility
            verbose=False,  # Reduce logging for speed
            word_timestamps=False  # Skip word-level timestamps for speed
        )
        text = result.get("text", "").strip()
        
        print(f"Transcription result: '{text}'")
        
        return {
            "text": text,
            "language": result.get("language", "en"),
            "segments": result.get("segments", [])
        }
        
    except Exception as exc:
        print(f"Transcription error: {exc}")
        from ..error_handlers import secure_http_exception
        raise secure_http_exception(500, "Transcription failed")
    finally:
        # Clean up temp file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Cleaned up temp file: {tmp_path}")
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")


@router.post("/transcribe-fast")
async def transcribe_audio_fast(file: UploadFile = File(...)):
    """Ultra-fast transcription using tiny model with minimal processing"""
    try:
        # Check if Whisper is available
        if not WHISPER_AVAILABLE:
            raise HTTPException(status_code=503, detail="Audio transcription is not available. Whisper package is not installed.")
        
        # Load the Whisper model
        model = _load_whisper_model()
        
        # Save upload to temp file
        tmp_path = os.path.join(WHISPER_MODEL_DIR, f"fast_upload_{os.getpid()}_{file.filename}")
        with open(tmp_path, "wb") as out:
            content = await file.read()
            out.write(content)
        
        print(f"Fast transcribing audio file: {tmp_path} (size: {len(content)} bytes)")
        
        # Ultra-fast transcription with minimal processing
        result = model.transcribe(
            tmp_path, 
            language="en",
            fp16=False,
            verbose=False,
            word_timestamps=False,
            condition_on_previous_text=False,  # Skip context for speed
            initial_prompt=None,  # No initial prompt for speed
            temperature=0.0  # Deterministic output for speed
        )
        text = result.get("text", "").strip()
        
        print(f"Fast transcription result: '{text}'")
        
        return {
            "text": text,
            "language": result.get("language", "en"),
            "processing_time": "fast"
        }
        
    except Exception as exc:
        print(f"Fast transcription error: {exc}")
        raise HTTPException(status_code=500, detail=f"Fast transcription failed: {exc}")
    finally:
        # Clean up temp file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Cleaned up temp file: {tmp_path}")
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")


@router.post("/transcribe-live")
async def transcribe_live_audio(file: UploadFile = File(...)):
    """Real-time live transcription with immediate sentiment analysis"""
    try:
        # Check if Whisper is available
        if not WHISPER_AVAILABLE:
            raise HTTPException(status_code=503, detail="Audio transcription is not available. Whisper package is not installed.")
        
        # Load the Whisper model
        model = _load_whisper_model()
        
        # Save upload to temp file
        tmp_path = os.path.join(WHISPER_MODEL_DIR, f"live_upload_{os.getpid()}_{file.filename}")
        with open(tmp_path, "wb") as out:
            content = await file.read()
            out.write(content)
        
        print(f"Live transcribing audio file: {tmp_path} (size: {len(content)} bytes)")
        
        # Ultra-fast transcription optimized for real-time
        result = model.transcribe(
            tmp_path, 
            language="en",
            fp16=False,
            verbose=False,
            word_timestamps=False,
            condition_on_previous_text=False,
            initial_prompt=None,
            temperature=0.0,
            no_speech_threshold=0.3,  # Lower threshold for more sensitive detection
            logprob_threshold=-0.8,   # Lower threshold for better detection
            compression_ratio_threshold=1.5  # Lower threshold for better detection
        )
        text = result.get("text", "").strip()
        
        # Perform immediate sentiment analysis
        sentiment_result = None
        if text:
            try:
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
            except Exception as e:
                print(f"Sentiment analysis error: {e}")
                sentiment_result = {
                    "label": "NEUTRAL",
                    "score": 0.5,
                    "justification": "Unable to analyze sentiment due to processing error.",
                    "error": str(e)
                }
        
        print(f"Live transcription result: '{text}' with sentiment: {sentiment_result['label'] if sentiment_result else 'N/A'}")
        
        return {
            "text": text,
            "language": result.get("language", "en"),
            "sentiment": sentiment_result,
            "processing_time": "live",
            "timestamp": int(time.time() * 1000)
        }
        
    except Exception as exc:
        print(f"Live transcription error: {exc}")
        raise HTTPException(status_code=500, detail=f"Live transcription failed: {exc}")
    finally:
        # Clean up temp file
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
                print(f"Cleaned up temp file: {tmp_path}")
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")


