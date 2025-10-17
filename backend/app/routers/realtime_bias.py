from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Tuple, Optional
import re
import time
import json
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import pickle
import os

router = APIRouter()

# Bias categories and their definitions
BIAS_CATEGORIES = {
    "gender_bias": {
        "description": "Gender-based discrimination or stereotyping",
        "keywords": ["women", "men", "female", "male", "girl", "boy", "lady", "gentleman"],
        "contexts": ["not good", "shouldn't", "can't", "cannot", "too", "only", "prefer", "not suitable"],
        "weight": 1.0
    },
    "age_bias": {
        "description": "Age-based discrimination",
        "keywords": ["young", "old", "age", "senior", "junior", "fresh", "experienced", "millennial", "boomer"],
        "contexts": ["too", "not suitable", "shouldn't", "can't", "cannot", "not good", "only", "prefer"],
        "weight": 1.0
    },
    "pejorative": {
        "description": "Derogatory or insulting language",
        "keywords": ["stupid", "idiot", "moron", "dumb", "pathetic", "worthless", "useless", "incompetent", "failure", "loser"],
        "weight": 1.0
    },
    "subjective": {
        "description": "Opinion-based rather than fact-based language",
        "keywords": ["obviously", "clearly", "undoubtedly", "definitely", "absolutely", "never", "always", "everyone", "nobody"],
        "weight": 0.6
    },
    "exaggeration": {
        "description": "Overstated or hyperbolic language",
        "keywords": ["amazing", "incredible", "terrible", "awful", "horrible", "fantastic", "perfect", "worst", "best", "brilliant"],
        "weight": 0.4
    },
    "stereotyping": {
        "description": "Generalizations based on group characteristics",
        "keywords": ["typical", "usually", "generally", "most", "all", "every", "never", "always", "tend to", "likely"],
        "weight": 0.8
    },
    "emotional_manipulation": {
        "description": "Language designed to evoke strong emotional responses",
        "keywords": ["shocking", "outrageous", "disgusting", "appalling", "terrifying", "devastating", "heartbreaking"],
        "weight": 0.7
    },
    "confirmation_bias": {
        "description": "Language that confirms existing beliefs without evidence",
        "keywords": ["as expected", "not surprising", "predictably", "obviously", "clearly", "undoubtedly"],
        "weight": 0.5
    }
}

class TextPayload(BaseModel):
    text: str
    session_id: Optional[str] = None

class BiasResult(BaseModel):
    is_biased: bool
    confidence: float
    categories: List[Dict[str, Any]]
    highlighted_text: str
    bias_score: float
    processing_time_ms: float

# Global bias detection pipeline
bias_pipeline = None
vectorizer = None
classifier = None

def _load_bias_pipeline():
    """Load or create the bias detection pipeline"""
    global bias_pipeline, vectorizer, classifier
    
    if bias_pipeline is None:
        try:
            # Create a simple TF-IDF + Naive Bayes pipeline for sentence-level classification
            vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words='english',
                lowercase=True
            )
            classifier = MultinomialNB(alpha=0.1)
            
            # Create the pipeline
            bias_pipeline = Pipeline([
                ('tfidf', vectorizer),
                ('classifier', classifier)
            ])
            
            # Train on synthetic bias examples
            _train_bias_classifier()
            
            print("✅ Real-time bias detection pipeline loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load bias pipeline: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load bias detection pipeline: {e}")
    
    return bias_pipeline

def _train_bias_classifier():
    """Train the bias classifier on synthetic examples"""
    global bias_pipeline
    
    # Synthetic training data
    biased_examples = [
        "That's obviously a terrible idea",
        "Everyone knows this is stupid",
        "This is absolutely ridiculous",
        "Typical behavior from these people",
        "This is clearly wrong and stupid",
        "Most people would agree this is awful",
        "This is undoubtedly the worst approach",
        "All of them are incompetent",
        "This is predictably bad",
        "Obviously this won't work",
        "This is clearly a failure",
        "Everyone can see this is wrong",
        "This is typically what happens",
        "Most of them are useless",
        "This is obviously a mistake"
    ]
    
    neutral_examples = [
        "The data shows a correlation",
        "Based on the analysis",
        "The results indicate",
        "According to the research",
        "The study found that",
        "The evidence suggests",
        "The findings show",
        "The report indicates",
        "The data reveals",
        "The analysis shows",
        "The research demonstrates",
        "The results suggest",
        "The study indicates",
        "The findings reveal",
        "The evidence shows"
    ]
    
    # Combine examples with labels
    X = biased_examples + neutral_examples
    y = [1] * len(biased_examples) + [0] * len(neutral_examples)
    
    # Train the pipeline
    bias_pipeline.fit(X, y)
    print("✅ Bias classifier trained on synthetic data")

def _fast_lexicon_filter(text: str) -> List[Dict[str, Any]]:
    """Fast lexicon-based filter for overtly biased terms"""
    text_lower = text.lower()
    words = text.split()
    detected_bias = []
    
    for category, config in BIAS_CATEGORIES.items():
        for keyword in config["keywords"]:
            if keyword in text_lower:
                # Find the position of the keyword
                keyword_pos = text_lower.find(keyword)
                word_index = -1
                
                # Find the word index
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        word_index = i
                        break
                
                if word_index >= 0:
                    # Get context around the keyword
                    start = max(0, word_index - 2)
                    end = min(len(words), word_index + 3)
                    context = " ".join(words[start:end])
                    
                    # Check for context words for gender/age bias
                    confidence = 0.9
                    if category in ["gender_bias", "age_bias"] and "contexts" in config:
                        # Higher confidence if negative context is present
                        if any(ctx in text_lower for ctx in config["contexts"]):
                            confidence = 1.0
                        # Still flag even without explicit context for these categories
                        elif category in ["gender_bias", "age_bias"]:
                            confidence = 0.7
                    
                    detected_bias.append({
                        "category": category,
                        "keyword": keyword,
                        "position": keyword_pos,
                        "context": context,
                        "weight": config["weight"],
                        "confidence": confidence,
                        "description": config["description"]
                    })
    
    return detected_bias

def _sentence_level_classification(text: str) -> Tuple[bool, float]:
    """Lightweight ML classification for sentence-level bias"""
    try:
        pipeline = _load_bias_pipeline()
        prediction = pipeline.predict([text])
        probability = pipeline.predict_proba([text])
        
        is_biased = bool(prediction[0])
        confidence = float(max(probability[0]))
        
        return is_biased, confidence
    except Exception as e:
        print(f"Sentence classification error: {e}")
        return False, 0.0

def _highlight_biased_words(text: str, bias_detections: List[Dict[str, Any]]) -> str:
    """Highlight biased words in the text"""
    if not bias_detections:
        return text
    
    highlighted_text = text
    bias_positions = []
    
    # Collect all bias positions
    for detection in bias_detections:
        keyword = detection["keyword"]
        position = detection["position"]
        category = detection["category"]
        confidence = detection["confidence"]
        
        bias_positions.append({
            "start": position,
            "end": position + len(keyword),
            "keyword": keyword,
            "category": category,
            "confidence": confidence
        })
    
    # Sort by position (descending) to avoid index shifting
    bias_positions.sort(key=lambda x: x["start"], reverse=True)
    
    # Apply highlighting
    for bias in bias_positions:
        start = bias["start"]
        end = bias["end"]
        keyword = bias["keyword"]
        category = bias["category"]
        confidence = bias["confidence"]
        
        # Create highlight with category and confidence
        highlight = f'<span style="background-color: rgba(255, 0, 0, {confidence}); color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;" title="{category} (confidence: {confidence:.2f})">{keyword}</span>'
        
        highlighted_text = highlighted_text[:start] + highlight + highlighted_text[end:]
    
    return highlighted_text

def _calculate_overall_bias_score(bias_detections: List[Dict[str, Any]], ml_biased: bool, ml_confidence: float) -> float:
    """Calculate overall bias score combining lexicon and ML results"""
    if not bias_detections and not ml_biased:
        return 0.0
    
    # Lexicon-based score (weighted by category weights)
    lexicon_score = 0.0
    if bias_detections:
        total_weight = sum(detection["weight"] * detection["confidence"] for detection in bias_detections)
        lexicon_score = min(total_weight / len(bias_detections), 1.0)
    
    # ML-based score
    ml_score = ml_confidence if ml_biased else 0.0
    
    # Combine scores (lexicon gets 70% weight, ML gets 30%)
    overall_score = (lexicon_score * 0.7) + (ml_score * 0.3)
    
    return min(overall_score, 1.0)

@router.post("/detect-realtime", response_model=BiasResult)
def detect_realtime_bias(payload: TextPayload):
    """Real-time bias detection with hybrid pipeline"""
    start_time = time.time()
    
    try:
        text = payload.text.strip()
        if not text:
            return BiasResult(
                is_biased=False,
                confidence=0.0,
                categories=[],
                highlighted_text="",
                bias_score=0.0,
                processing_time_ms=0.0
            )
        
        # Step 1: Fast lexicon-based filtering
        lexicon_bias = _fast_lexicon_filter(text)
        
        # Step 2: Lightweight ML classification
        ml_biased, ml_confidence = _sentence_level_classification(text)
        
        # Step 3: Combine results
        is_biased = len(lexicon_bias) > 0 or ml_biased
        overall_confidence = max(
            max([detection["confidence"] for detection in lexicon_bias], default=0.0),
            ml_confidence
        )
        
        # Step 4: Calculate overall bias score
        bias_score = _calculate_overall_bias_score(lexicon_bias, ml_biased, ml_confidence)
        
        # Step 5: Highlight biased words
        highlighted_text = _highlight_biased_words(text, lexicon_bias)
        
        # Step 6: Prepare categories with explanations
        categories = []
        for detection in lexicon_bias:
            categories.append({
                "category": detection["category"],
                "description": detection["description"],
                "confidence": detection["confidence"],
                "keyword": detection["keyword"],
                "context": detection["context"],
                "weight": detection["weight"]
            })
        
        # Add ML-based category if detected
        if ml_biased and not lexicon_bias:
            categories.append({
                "category": "general_bias",
                "description": "General biased language detected by ML classifier",
                "confidence": ml_confidence,
                "keyword": None,
                "context": text,
                "weight": 0.5
            })
        
        processing_time = (time.time() - start_time) * 1000
        
        return BiasResult(
            is_biased=is_biased,
            confidence=overall_confidence,
            categories=categories,
            highlighted_text=highlighted_text,
            bias_score=bias_score,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        print(f"Real-time bias detection error: {e}")
        return BiasResult(
            is_biased=False,
            confidence=0.0,
            categories=[],
            highlighted_text=payload.text,
            bias_score=0.0,
            processing_time_ms=(time.time() - start_time) * 1000
        )

@router.get("/bias-categories")
def get_bias_categories():
    """Get available bias categories and their definitions"""
    return {
        "categories": BIAS_CATEGORIES,
        "total_categories": len(BIAS_CATEGORIES)
    }

@router.post("/batch-detect")
def batch_detect_bias(texts: List[str]):
    """Batch detect bias for multiple texts"""
    results = []
    
    for text in texts:
        payload = TextPayload(text=text)
        result = detect_realtime_bias(payload)
        results.append({
            "text": text,
            "result": result.dict()
        })
    
    return {
        "results": results,
        "total_processed": len(texts)
    }
