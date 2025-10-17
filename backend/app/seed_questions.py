from sqlalchemy.orm import Session
from . import models
import csv
import os
import random
from typing import List, Dict, Any

ROLES = [
    "Software Engineer", "Data Scientist", "DevOps Engineer", "Product Manager",
    "Backend Engineer", "Frontend Engineer", "ML Engineer", "QA Engineer",
    "UX Designer", "Security Engineer", "Mobile Developer", "Cloud Engineer",
    "Database Administrator", "System Administrator", "Technical Writer",
    "Full Stack Engineer", "AI Engineer", "Blockchain Developer", "Game Developer",
    "Embedded Systems Engineer", "Network Engineer", "Solutions Architect"
]
LEVELS = ["Junior", "Mid", "Senior", "Lead", "Principal"]
TYPES = ["Technical", "Behavioral", "System Design", "Coding", "Problem Solving", "Culture Fit"]

# Comprehensive question database
QUESTIONS_DATABASE = {
    "Software Engineer": {
        "Technical": {
            "Junior": [
                "What is object-oriented programming and can you explain the four main principles?",
                "Explain the difference between a class and an object with examples.",
                "What are the different types of loops in programming and when would you use each?",
                "Describe the difference between stack and heap memory.",
                "What is recursion and provide an example of when you'd use it.",
                "Explain the concept of variables and data types in programming.",
                "What is the difference between == and === in JavaScript?",
                "Describe what a function is and how parameters work.",
                "What are arrays and how do you access elements in them?",
                "Explain the concept of scope in programming languages.",
                "What is debugging and what tools do you use for it?",
                "Describe the difference between compiled and interpreted languages.",
                "What are comments in code and why are they important?",
                "Explain the concept of version control and why it's useful.",
                "What is an IDE and what features make it helpful for development?"
            ],
            "Mid": [
                "Explain design patterns and give examples of three common ones you've used.",
                "What is the difference between synchronous and asynchronous programming?",
                "Describe RESTful API design principles and best practices.",
                "Explain the concept of dependency injection and its benefits.",
                "What are microservices and how do they differ from monolithic architecture?",
                "Describe different database types and when to use each.",
                "Explain the SOLID principles with practical examples.",
                "What is caching and what strategies would you use to implement it?",
                "Describe the difference between SQL and NoSQL databases.",
                "Explain the concept of concurrency and parallelism in programming.",
                "What are unit tests and how do you write effective ones?",
                "Describe the MVC pattern and its benefits.",
                "Explain the concept of polymorphism with examples.",
                "What is API versioning and why is it important?",
                "Describe different authentication methods and their security implications."
            ],
            "Senior": [
                "Design a scalable system architecture for a social media platform.",
                "Explain how you would optimize a slow-performing database query.",
                "Describe your approach to handling system failures and implementing resilience patterns.",
                "How would you design a distributed caching system?",
                "Explain the CAP theorem and its implications for distributed systems.",
                "Describe your experience with performance optimization and profiling.",
                "How would you implement a real-time messaging system?",
                "Explain the concept of eventual consistency and when it's acceptable.",
                "Describe your approach to code review and maintaining code quality.",
                "How would you design a system to handle millions of concurrent users?",
                "Explain the concept of load balancing and different strategies.",
                "Describe your experience with containerization and orchestration.",
                "How would you implement a recommendation engine?",
                "Explain the concept of event-driven architecture.",
                "Describe your approach to technical debt management."
            ],
            "Lead": [
                "How would you architect a multi-tenant SaaS application?",
                "Describe your strategy for managing technical teams and code quality.",
                "Explain how you would implement a distributed transaction system.",
                "How would you design a system for real-time data processing?",
                "Describe your approach to system monitoring and observability.",
                "How would you implement a feature flag system for gradual rollouts?",
                "Explain your strategy for handling data migration in production systems.",
                "How would you design a system for handling different time zones globally?",
                "Describe your approach to security in distributed systems.",
                "How would you implement a system for A/B testing at scale?",
                "Explain your strategy for managing third-party integrations.",
                "How would you design a system for handling file uploads at scale?",
                "Describe your approach to implementing rate limiting and throttling.",
                "How would you design a system for real-time collaboration?",
                "Explain your strategy for managing technical documentation."
            ],
            "Principal": [
                "Design a global content delivery network architecture.",
                "How would you architect a system for handling financial transactions?",
                "Describe your vision for the future of software architecture.",
                "How would you design a system for machine learning model deployment?",
                "Explain your strategy for building platform teams and developer experience.",
                "How would you architect a system for handling IoT data at scale?",
                "Describe your approach to building resilient distributed systems.",
                "How would you design a system for real-time analytics?",
                "Explain your strategy for managing technical innovation and research.",
                "How would you architect a system for handling blockchain transactions?",
                "Describe your approach to building scalable data pipelines.",
                "How would you design a system for handling video streaming?",
                "Explain your strategy for managing technical standards and governance.",
                "How would you architect a system for handling AI/ML workloads?",
                "Describe your approach to building developer productivity tools."
            ]
        },
        "Behavioral": {
            "Junior": [
                "Tell me about a time when you had to learn a new technology quickly.",
                "Describe a challenging bug you had to fix and how you approached it.",
                "Tell me about a time when you had to work with a difficult team member.",
                "Describe a project where you had to work under pressure.",
                "Tell me about a time when you made a mistake in your code and how you handled it.",
                "Describe a situation where you had to ask for help.",
                "Tell me about a time when you had to explain a technical concept to a non-technical person.",
                "Describe a time when you had to work on a project you weren't interested in.",
                "Tell me about a time when you had to meet a tight deadline.",
                "Describe a situation where you had to work independently on a project."
            ],
            "Mid": [
                "Tell me about a time when you had to refactor legacy code.",
                "Describe a situation where you had to make a difficult technical decision.",
                "Tell me about a time when you had to mentor a junior developer.",
                "Describe a project where you had to work with multiple teams.",
                "Tell me about a time when you had to learn from a failure.",
                "Describe a situation where you had to balance technical debt with new features.",
                "Tell me about a time when you had to implement a solution you disagreed with.",
                "Describe a project where you had to work with stakeholders with different priorities.",
                "Tell me about a time when you had to optimize a system's performance.",
                "Describe a situation where you had to work with limited resources."
            ],
            "Senior": [
                "Tell me about a time when you had to lead a technical initiative.",
                "Describe a situation where you had to make a decision that affected the entire team.",
                "Tell me about a time when you had to handle a production incident.",
                "Describe a project where you had to work with external vendors.",
                "Tell me about a time when you had to implement a major architectural change.",
                "Describe a situation where you had to work with conflicting requirements.",
                "Tell me about a time when you had to mentor multiple developers.",
                "Describe a project where you had to work with tight deadlines and high stakes.",
                "Tell me about a time when you had to work with a difficult client.",
                "Describe a situation where you had to work with limited information."
            ],
            "Lead": [
                "Tell me about a time when you had to build a team from scratch.",
                "Describe a situation where you had to make a decision that affected the entire company.",
                "Tell me about a time when you had to work with executives on technical strategy.",
                "Describe a project where you had to work with multiple departments.",
                "Tell me about a time when you had to handle a major technical crisis.",
                "Describe a situation where you had to work with a difficult vendor.",
                "Tell me about a time when you had to implement a major process change.",
                "Describe a project where you had to work with limited budget and resources.",
                "Tell me about a time when you had to work with a difficult stakeholder.",
                "Describe a situation where you had to work with conflicting technical opinions."
            ],
            "Principal": [
                "Tell me about a time when you had to define technical strategy for a company.",
                "Describe a situation where you had to work with board members on technical decisions.",
                "Tell me about a time when you had to work with multiple companies on a project.",
                "Describe a project where you had to work with government regulations.",
                "Tell me about a time when you had to work with a difficult investor.",
                "Describe a situation where you had to work with a difficult partner.",
                "Tell me about a time when you had to work with a difficult customer.",
                "Describe a project where you had to work with a difficult team.",
                "Tell me about a time when you had to work with a difficult manager.",
                "Describe a situation where you had to work with a difficult colleague."
            ]
        },
        "System Design": {
            "Junior": [
                "How would you design a simple chat application?",
                "Design a basic URL shortener service like bit.ly.",
                "How would you design a simple file storage system?",
                "Design a basic notification system.",
                "How would you design a simple search engine?",
                "Design a basic social media feed.",
                "How would you design a simple e-commerce system?",
                "Design a basic content management system.",
                "How would you design a simple booking system?",
                "Design a basic recommendation system."
            ],
            "Mid": [
                "Design a scalable web crawler.",
                "How would you design a distributed cache system?",
                "Design a real-time messaging system like WhatsApp.",
                "How would you design a video streaming platform?",
                "Design a distributed file storage system.",
                "How would you design a social media platform?",
                "Design a distributed database system.",
                "How would you design a content delivery network?",
                "Design a distributed logging system.",
                "How would you design a distributed search engine?"
            ],
            "Senior": [
                "Design a global video conferencing system.",
                "How would you design a distributed payment system?",
                "Design a real-time analytics platform.",
                "How would you design a distributed machine learning platform?",
                "Design a global content delivery network.",
                "How would you design a distributed blockchain system?",
                "Design a real-time collaboration platform.",
                "How would you design a distributed IoT platform?",
                "Design a global e-commerce platform.",
                "How would you design a distributed AI platform?"
            ],
            "Lead": [
                "Design a global financial trading platform.",
                "How would you design a distributed healthcare system?",
                "Design a global transportation platform.",
                "How would you design a distributed energy management system?",
                "Design a global education platform.",
                "How would you design a distributed government system?",
                "Design a global entertainment platform.",
                "How would you design a distributed security system?",
                "Design a global communication platform.",
                "How would you design a distributed manufacturing system?"
            ],
            "Principal": [
                "Design a global smart city platform.",
                "How would you design a distributed space exploration system?",
                "Design a global climate monitoring system.",
                "How would you design a distributed quantum computing platform?",
                "Design a global autonomous vehicle platform.",
                "How would you design a distributed brain-computer interface?",
                "Design a global virtual reality platform.",
                "How would you design a distributed augmented reality platform?",
                "Design a global mixed reality platform.",
                "How would you design a distributed consciousness platform?"
            ]
        },
        "Coding": {
            "Junior": [
                "Write a function to reverse a string.",
                "Implement a function to check if a string is a palindrome.",
                "Write a function to find the factorial of a number.",
                "Implement a function to check if a number is prime.",
                "Write a function to find the maximum element in an array.",
                "Implement a function to sort an array of integers.",
                "Write a function to find the sum of all elements in an array.",
                "Implement a function to check if two strings are anagrams.",
                "Write a function to find the Fibonacci sequence up to n terms.",
                "Implement a function to check if a string contains only digits."
            ],
            "Mid": [
                "Implement a binary search algorithm.",
                "Write a function to find the longest common subsequence.",
                "Implement a function to solve the two-sum problem.",
                "Write a function to find the longest palindromic substring.",
                "Implement a function to solve the knapsack problem.",
                "Write a function to find the shortest path in a graph.",
                "Implement a function to solve the coin change problem.",
                "Write a function to find the maximum subarray sum.",
                "Implement a function to solve the longest increasing subsequence.",
                "Write a function to find the median of two sorted arrays."
            ],
            "Senior": [
                "Implement a distributed consensus algorithm.",
                "Write a function to solve the traveling salesman problem.",
                "Implement a function to solve the graph coloring problem.",
                "Write a function to find the maximum flow in a network.",
                "Implement a function to solve the minimum spanning tree problem.",
                "Write a function to find the shortest path in a weighted graph.",
                "Implement a function to solve the maximum matching problem.",
                "Write a function to find the strongly connected components.",
                "Implement a function to solve the minimum cut problem.",
                "Write a function to find the maximum independent set."
            ],
            "Lead": [
                "Implement a distributed hash table.",
                "Write a function to solve the Byzantine generals problem.",
                "Implement a function to solve the consensus problem.",
                "Write a function to find the optimal resource allocation.",
                "Implement a function to solve the load balancing problem.",
                "Write a function to find the optimal scheduling algorithm.",
                "Implement a function to solve the resource contention problem.",
                "Write a function to find the optimal caching strategy.",
                "Implement a function to solve the fault tolerance problem.",
                "Write a function to find the optimal replication strategy."
            ],
            "Principal": [
                "Implement a quantum computing algorithm.",
                "Write a function to solve the protein folding problem.",
                "Implement a function to solve the climate modeling problem.",
                "Write a function to find the optimal space exploration strategy.",
                "Implement a function to solve the artificial intelligence problem.",
                "Write a function to find the optimal machine learning algorithm.",
                "Implement a function to solve the natural language processing problem.",
                "Write a function to find the optimal computer vision algorithm.",
                "Implement a function to solve the robotics problem.",
                "Write a function to find the optimal human-computer interaction."
            ]
        }
    }
}

def load_questions_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Load questions from CSV file"""
    questions = []
    
    if not os.path.exists(csv_path):
        print(f"CSV file not found at {csv_path}")
        return questions
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Flexible mapping - adapt to your CSV structure
                question_data = {
                    'question_text': row.get('question_text', row.get('question', row.get('text', ''))),
                    'role': row.get('role', 'Software Engineer'),
                    'level': row.get('level', 'Mid'),
                    'type': row.get('type', 'Technical'),
                    'difficulty_score': int(row.get('difficulty_score', row.get('difficulty', 5))),
                    'estimated_time': int(row.get('estimated_time', row.get('time', 10)))
                }
                
                # Clean up role, level, and type formatting
                question_data['role'] = question_data['role'].replace('_', ' ').title()
                question_data['level'] = question_data['level'].replace('_', ' ').title()
                question_data['type'] = question_data['type'].replace('_', ' ').title()
                
                questions.append(question_data)
        
        print(f"Loaded {len(questions)} questions from CSV")
        return questions
    
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return questions

def seed_questions(db: Session, target_count: int = 10000) -> int:
    """Seed questions from CSV database"""
    existing = db.query(models.Question).count()
    if existing >= target_count:
        print(f"Database already has {existing} questions, target is {target_count}")
        return 0

    # Load questions from CSV - look in multiple locations
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'questions_database.csv'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'questions_database.csv'),
        'questions_database.csv',
        'questions.csv'
    ]
    
    questions_data = []
    for csv_path in possible_paths:
        if os.path.exists(csv_path):
            print(f"Found CSV file at: {csv_path}")
            questions_data = load_questions_from_csv(csv_path)
            break
    
    if not questions_data:
        print("No CSV file found. Please place your CSV file as 'questions_database.csv' in the project root.")
    
    if not questions_data:
        print("No questions loaded from CSV, falling back to basic generation")
        return _generate_basic_questions(db, target_count)
    
    generated = 0
    batch = []
    
    # Process questions from CSV
    for question_data in questions_data:
        if existing + generated >= target_count:
            break
            
        # Create question object
        question = models.Question(
            role=question_data['role'],
            level=question_data['level'],
            type=question_data['type'],
            question_text=question_data['question_text']
        )
        
        batch.append(question)
        generated += 1
        
        # Batch insert for performance
        if len(batch) >= 100:
            db.bulk_save_objects(batch)
            db.commit()
            batch.clear()
            print(f"Seeded {generated} questions so far...")
    
    # Insert remaining questions
    if batch:
        db.bulk_save_objects(batch)
        db.commit()
    
    print(f"Successfully seeded {generated} questions from CSV database")
    return generated

def _generate_basic_questions(db: Session, target_count: int) -> int:
    """Fallback method to generate basic questions if CSV is not available"""
    existing = db.query(models.Question).count()
    if existing >= target_count:
        return 0

    generated = 0
    batch = []
    index = existing + 1
    
    while existing + generated < target_count:
        for role in ROLES:
            for level in LEVELS:
                for qt in TYPES:
                    if existing + generated >= target_count:
                        break
                    text = f"[{role}][{level}][{qt}] Sample question #{index}: Describe a challenge and solution."
                    batch.append(models.Question(role=role, level=level, type=qt, question_text=text))
                    generated += 1
                    index += 1
                if existing + generated >= target_count:
                    break
            if existing + generated >= target_count:
                break

        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            batch.clear()

    return generated


