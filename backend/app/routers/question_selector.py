from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import random
import time
from pathlib import Path
import logging

# Conditional import of pandas to avoid startup issues
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Pandas not available: {e}")
    PANDAS_AVAILABLE = False
    pd = None

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store loaded questions
all_questions_df = None
main_roles = []
sub_roles = []
difficulty_levels = ['easy', 'mid', 'high']

class QuestionRequest(BaseModel):
    main_role: str
    sub_role: str
    difficulties: List[str]
    num_questions: int = 9

class QuestionResponse(BaseModel):
    questions: List[Dict[str, Any]]
    total_questions: int
    difficulty_distribution: Dict[str, int]
    session_id: str

class QuestionNavigation(BaseModel):
    session_id: str
    current_index: int
    action: str  # 'next', 'previous', 'regenerate'

def load_all_questions():
    """Load and merge all CSV files from Questions_data/ folder"""
    global all_questions_df, main_roles, sub_roles
    
    # Check if pandas is available
    if not PANDAS_AVAILABLE:
        logger.error("Pandas is not available. Question loading functionality is disabled.")
        raise HTTPException(status_code=503, detail="Question loading is not available. Pandas package is not installed.")
    
    try:
        # Get the project root directory (two levels up from this file)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        questions_data_dir = project_root / "Questions_Data"
        
        # Alternative path resolution if the above doesn't work
        if not questions_data_dir.exists():
            # Try relative to current working directory
            questions_data_dir = Path("Questions_Data")
            if not questions_data_dir.exists():
                # Try going up one level from backend
                questions_data_dir = Path("../Questions_Data")
                if not questions_data_dir.exists():
                    logger.error(f"Questions_Data folder not found. Tried:")
                    logger.error(f"  1. {project_root / 'Questions_Data'}")
                    logger.error(f"  2. Questions_Data")
                    logger.error(f"  3. ../Questions_Data")
                    logger.error(f"Current working directory: {Path.cwd()}")
                    raise HTTPException(status_code=404, detail=f"Questions_Data folder not found. Checked multiple paths.")
        
        csv_files = list(questions_data_dir.glob("*.csv"))
        logger.info(f"Found {len(csv_files)} CSV files in Questions_data/")
        
        all_dataframes = []
        
        for csv_file in csv_files:
            try:
                logger.info(f"Loading {csv_file.name}")
                df = pd.read_csv(csv_file)
                
                # Standardize column names (handle case variations)
                df.columns = df.columns.str.lower().str.strip()
                df.columns = df.columns.str.replace(' ', '_')
                
                # Ensure required columns exist
                required_columns = ['main_role', 'sub_role', 'question_number', 'difficulty', 'question']
                
                # Map variations to standard names
                column_mapping = {
                    'main_role': ['main role', 'mainrole'],
                    'sub_role': ['sub role', 'subrole'],
                    'question_number': ['question number', 'questionnumber', 'question_no', 'questionno'],
                    'difficulty': ['difficulty'],
                    'question': ['question', 'question_text', 'questiontext']
                }
                
                # Rename columns based on mapping
                for standard_name, variations in column_mapping.items():
                    for col in df.columns:
                        if col in variations:
                            df = df.rename(columns={col: standard_name})
                
                # Check if all required columns are present
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    logger.warning(f"Skipping {csv_file.name} - missing columns: {missing_columns}")
                    continue
                
                # Clean and standardize data
                df = df.dropna(subset=['question'])  # Remove rows without questions
                df['difficulty'] = df['difficulty'].str.lower().str.strip()
                
                # Map difficulty variations to standard levels
                difficulty_mapping = {
                    'easy': 'easy',
                    'e': 'easy',
                    'beginner': 'easy',
                    'medium': 'mid',
                    'med': 'mid',
                    'm': 'mid',
                    'intermediate': 'mid',
                    'hard': 'high',
                    'h': 'high',
                    'difficult': 'high',
                    'advanced': 'high'
                }
                
                df['difficulty'] = df['difficulty'].map(difficulty_mapping).fillna(df['difficulty'])
                
                # Only keep rows with valid difficulties
                df = df[df['difficulty'].isin(['easy', 'mid', 'high'])]
                
                # Add source file information
                df['source_file'] = csv_file.name
                
                all_dataframes.append(df)
                logger.info(f"Loaded {len(df)} questions from {csv_file.name}")
                
            except Exception as e:
                logger.error(f"Error loading {csv_file.name}: {str(e)}")
                continue
        
        if not all_dataframes:
            raise HTTPException(status_code=500, detail="No valid CSV files could be loaded")
        
        # Merge all dataframes
        all_questions_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Remove duplicates based on question text
        all_questions_df = all_questions_df.drop_duplicates(subset=['question'], keep='first')
        
        # Standardize text columns
        all_questions_df['main_role'] = all_questions_df['main_role'].str.strip()
        all_questions_df['sub_role'] = all_questions_df['sub_role'].str.strip()
        all_questions_df['question'] = all_questions_df['question'].str.strip()
        
        # Get unique values
        main_roles = sorted(all_questions_df['main_role'].unique().tolist())
        sub_roles = sorted(all_questions_df['sub_role'].unique().tolist())
        
        logger.info(f"Successfully loaded {len(all_questions_df)} unique questions")
        logger.info(f"Main roles: {main_roles}")
        logger.info(f"Sub roles: {len(sub_roles)} total")
        
        return True
        
    except Exception as e:
        logger.error(f"Error loading questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load questions: {str(e)}")

def calculate_difficulty_distribution(num_questions: int, difficulties: List[str]) -> Dict[str, int]:
    """Calculate how to distribute questions across difficulty levels"""
    if not difficulties:
        return {}
    
    num_difficulties = len(difficulties)
    base_questions_per_difficulty = num_questions // num_difficulties
    remainder = num_questions % num_difficulties
    
    distribution = {}
    for i, difficulty in enumerate(difficulties):
        # Give remainder questions to first few difficulties
        extra = 1 if i < remainder else 0
        distribution[difficulty] = base_questions_per_difficulty + extra
    
    return distribution

def select_questions(main_role: str, sub_role: str, difficulties: List[str], num_questions: int) -> List[Dict[str, Any]]:
    """Select questions based on criteria"""
    global all_questions_df
    
    if all_questions_df is None:
        raise HTTPException(status_code=500, detail="Questions not loaded")
    
    # Filter by main role and sub role
    filtered_df = all_questions_df[
        (all_questions_df['main_role'] == main_role) & 
        (all_questions_df['sub_role'] == sub_role) &
        (all_questions_df['difficulty'].isin(difficulties))
    ].copy()
    
    if len(filtered_df) == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"No questions found for Main Role: {main_role}, Sub Role: {sub_role}, Difficulties: {difficulties}"
        )
    
    # Calculate distribution
    distribution = calculate_difficulty_distribution(num_questions, difficulties)
    
    selected_questions = []
    
    # Select questions for each difficulty level
    for difficulty, count in distribution.items():
        difficulty_questions = filtered_df[filtered_df['difficulty'] == difficulty]
        
        if len(difficulty_questions) == 0:
            logger.warning(f"No questions found for difficulty: {difficulty}")
            continue
        
        # Randomly select questions for this difficulty
        if len(difficulty_questions) >= count:
            selected = difficulty_questions.sample(n=count)
        else:
            selected = difficulty_questions
        
        for _, row in selected.iterrows():
            selected_questions.append({
                'id': f"{row['source_file']}_{row['question_number']}",
                'question_number': int(row['question_number']),
                'main_role': row['main_role'],
                'sub_role': row['sub_role'],
                'difficulty': row['difficulty'],
                'question': row['question'],
                'source_file': row['source_file']
            })
    
    # Shuffle the selected questions
    random.shuffle(selected_questions)
    
    return selected_questions

# Initialize questions on startup
@router.on_event("startup")
async def startup_event():
    try:
        logger.info("Loading questions on startup...")
        load_all_questions()
        logger.info("Questions loaded successfully on startup")
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        logger.error(f"Failed to load questions on startup: {e}")

@router.get("/metadata")
def get_question_metadata():
    """Get available main roles, sub roles, and difficulty levels"""
    global main_roles, sub_roles, all_questions_df
    
    if all_questions_df is None:
        load_all_questions()
    
    # Get sub roles grouped by main role
    sub_roles_by_main = {}
    for main_role in main_roles:
        sub_roles_for_main = sorted(
            all_questions_df[all_questions_df['main_role'] == main_role]['sub_role'].unique().tolist()
        )
        sub_roles_by_main[main_role] = sub_roles_for_main
    
    return {
        "main_roles": main_roles,
        "sub_roles_by_main": sub_roles_by_main,
        "difficulty_levels": difficulty_levels,
        "total_questions": len(all_questions_df) if all_questions_df is not None else 0
    }

@router.post("/generate-session", response_model=QuestionResponse)
def generate_question_session(request: QuestionRequest):
    """Generate a new question session with balanced difficulty distribution"""
    try:
        # Validate inputs
        if request.num_questions < 1 or request.num_questions > 20:
            raise HTTPException(status_code=400, detail="Number of questions must be between 1 and 20")
        
        if not request.difficulties:
            raise HTTPException(status_code=400, detail="At least one difficulty level must be selected")
        
        # Check if main role and sub role exist
        if request.main_role not in main_roles:
            raise HTTPException(status_code=400, detail=f"Invalid main role: {request.main_role}")
        
        # Get available sub roles for the main role
        available_sub_roles = all_questions_df[all_questions_df['main_role'] == request.main_role]['sub_role'].unique().tolist()
        if request.sub_role not in available_sub_roles:
            raise HTTPException(status_code=400, detail=f"Invalid sub role: {request.sub_role} for main role: {request.main_role}")
        
        # Select questions
        selected_questions = select_questions(
            request.main_role, 
            request.sub_role, 
            request.difficulties, 
            request.num_questions
        )
        
        if len(selected_questions) == 0:
            raise HTTPException(status_code=404, detail="No questions could be selected with the given criteria")
        
        # Calculate actual distribution
        actual_distribution = {}
        for question in selected_questions:
            difficulty = question['difficulty']
            actual_distribution[difficulty] = actual_distribution.get(difficulty, 0) + 1
        
        # Generate session ID
        session_id = f"session_{random.randint(10000, 99999)}_{int(time.time())}"
        
        return QuestionResponse(
            questions=selected_questions,
            total_questions=len(selected_questions),
            difficulty_distribution=actual_distribution,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating question session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate question session: {str(e)}")

@router.post("/regenerate-questions")
def regenerate_questions(request: QuestionRequest):
    """Regenerate questions for an existing session with new criteria"""
    return generate_question_session(request)

@router.get("/questions-by-role/{main_role}/{sub_role}")
def get_questions_by_role(main_role: str, sub_role: str, difficulty: Optional[str] = None):
    """Get all questions for a specific role and optional difficulty"""
    global all_questions_df
    
    if all_questions_df is None:
        raise HTTPException(status_code=500, detail="Questions not loaded")
    
    # Filter by main role and sub role
    filtered_df = all_questions_df[
        (all_questions_df['main_role'] == main_role) & 
        (all_questions_df['sub_role'] == sub_role)
    ]
    
    # Filter by difficulty if specified
    if difficulty:
        filtered_df = filtered_df[filtered_df['difficulty'] == difficulty]
    
    if len(filtered_df) == 0:
        return {"questions": [], "count": 0}
    
    questions = []
    for _, row in filtered_df.iterrows():
        questions.append({
            'id': f"{row['source_file']}_{row['question_number']}",
            'question_number': int(row['question_number']),
            'main_role': row['main_role'],
            'sub_role': row['sub_role'],
            'difficulty': row['difficulty'],
            'question': row['question'],
            'source_file': row['source_file']
        })
    
    return {
        "questions": questions,
        "count": len(questions),
        "difficulty_breakdown": filtered_df['difficulty'].value_counts().to_dict()
    }

@router.post("/reload-questions")
def reload_questions():
    """Manually reload all questions from CSV files"""
    try:
        result = load_all_questions()
        if result:
            return {
                "success": True,
                "message": f"Successfully loaded {len(all_questions_df)} questions",
                "total_questions": len(all_questions_df),
                "main_roles": len(main_roles),
                "sub_roles": len(sub_roles)
            }
        else:
            return {"success": False, "message": "Failed to load questions"}
    except Exception as e:
        return {"success": False, "message": f"Error loading questions: {str(e)}"}

@router.get("/stats")
def get_question_stats():
    """Get statistics about the loaded questions"""
    global all_questions_df
    
    if all_questions_df is None:
        raise HTTPException(status_code=500, detail="Questions not loaded")
    
    stats = {
        "total_questions": len(all_questions_df),
        "main_roles_count": len(main_roles),
        "sub_roles_count": len(sub_roles),
        "difficulty_distribution": all_questions_df['difficulty'].value_counts().to_dict(),
        "questions_per_main_role": all_questions_df['main_role'].value_counts().to_dict(),
        "questions_per_sub_role": all_questions_df['sub_role'].value_counts().to_dict()
    }
    
    return stats

# Import time module
import time
