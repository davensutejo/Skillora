# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app, send_file
from flask_login import login_required, current_user
from .models import Note, User, ChatMessage, CSInterestSurvey, CSInterest, LearningPath, Course, Module, Quiz, QuizQuestion, UserProgress, QuizAttempt, UserSettings
from . import db
from .db_utils import update_user_profile # Assuming get_user_by_id is not used here
from datetime import datetime, timedelta
import json
import requests
import traceback # For detailed error logging
import asyncio
from .course import main as course_generator, parse_chapters_simple
import os
from sqlalchemy import func
import re
from werkzeug.utils import secure_filename
import time
import uuid
import random
import threading

# Import from api_utils
from .api_utils import get_generation_status, update_generation_status

# Import configurations - MAKE SURE THESE ARE CORRECT FOR DIRECT GEMINI API
from .config import (
    TEMPERATURE, 
    MAX_TOKENS,    # Will be used for maxOutputTokens
    MAX_CHAT_HISTORY,
    OPENROUTER_API_KEY,   # Add this if not already present in config.py
    OPENROUTER_URL,       # Make sure this is in config.py
    OPENROUTER_MODEL,     # Make sure this is in config.py
    SYSTEM_PROMPT        # Make sure this is in config.py
)

# Import from manim
from .manim import get_video_script

views = Blueprint('views', __name__)

# Define allowed image extensions and upload folder
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = 'Backend/website/static/uploads/chat_images'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Helper Function to Convert Chat History ---
def convert_messages_format(openai_messages):
    """Converts chat message history to the format needed for API requests.
    Takes OpenAI-style messages and ensures they're properly formatted."""
    formatted_messages = []
    
    for msg in openai_messages:
        # Ensure content is not empty or None before appending
        content = msg.get("content")
        role = msg.get("role")
        
        if content and role in ["user", "assistant", "system"]:
            # OpenRouter uses the same format as OpenAI
            formatted_messages.append({
                "role": role,
                "content": content
            })
    
    # Ensure we have at least one message and the conversation flow makes sense
    if not formatted_messages:
        return []
        
    # Make sure we don't have consecutive messages with same role (keep the last one)
    deduplicated_messages = [formatted_messages[0]]
    for i in range(1, len(formatted_messages)):
        if formatted_messages[i]['role'] != formatted_messages[i-1]['role']:
            deduplicated_messages.append(formatted_messages[i])
        else:
            # Replace previous message with same role
            deduplicated_messages[-1] = formatted_messages[i]
    
    return deduplicated_messages

# --- Routes ---

@views.route('/test')
def test():
    return "Route testing successful"

@views.route('/', methods=['GET','POST'])
@views.route('/index', methods=['GET','POST'])
@views.route('/home', methods=['GET','POST'])
def home():
    # Double-check the session validity
    if hasattr(current_user, 'id') and current_user.id:
        db_user = User.query.get(current_user.id)
        if not db_user:
            print("DEBUG: User exists in session but not in database - logging out")
            from flask_login import logout_user
            logout_user()
            flash('Session error. Please log in again.', category='error')
            return redirect(url_for('auth.login'))
    
    # For the /home path, ensure the user is logged in
    if request.path == '/home' and current_user.is_anonymous:
            flash('Please log in to access your dashboard.', category='info')
            return redirect(url_for('auth.login'))
    
    # Check if user is logged in (not anonymous)
    if current_user.is_anonymous:
        return render_template('index.html')
    
    # User is authenticated, show dashboard
    
    # Handle POST request for notes
    if request.method == 'POST':
        note = request.form.get('note')
        if not note or len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            try:
                new_note = Note(data=note, user_id=current_user.id)
                db.session.add(new_note)
                db.session.commit()
                flash('Note added!', category='success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding note: {str(e)}', category='error')
                print(f"ERROR adding note: {str(e)}\n{traceback.format_exc()}")

    return render_template('home.html', user=current_user)

@views.route('/my_courses', methods=['GET'])
@login_required
def my_courses():
    # If user hasn't completed the survey, redirect them
    if not current_user.is_survey_completed:
        flash('Please complete the CS interest survey first.', 'warning')
        return redirect(url_for('views.cs_interest_survey'))
    
    # Get user's learning preferences
    user_preferences = None
    try:
        user_preferences = CSInterest.query.filter_by(user_id=current_user.id).first()
    except Exception as e:
        print(f"Error accessing CSInterest: {e}")
        # This will allow the view to continue even if the cs_interest table doesn't exist yet
    
    # Get user's learning path
    learning_path = None
    try:
        learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
    except Exception as e:
        print(f"Error accessing LearningPath: {e}")
        # This will allow the view to continue even if the learning_path table doesn't exist yet
    
    # Load or generate courses based on learning path
    if learning_path:
        # Check if courses already exist for this learning path
        courses = Course.query.filter_by(user_id=current_user.id).all()
        
        # If no courses found, generate them
        if not courses:
            # Get career path from learning path
            career_path = learning_path.career_path
            
            # Define course topics based on career path
            if career_path == "Software Engineer":
                course_topics = [
                    "Programming Fundamentals",
                    "Frameworks & Advanced Development",
                    "Real Projects & Career Preparation"
                ]
            elif career_path == "Data Scientist":
                course_topics = [
                    "Data Analysis Fundamentals",
                    "Machine Learning Basics",
                    "Advanced Data Science & AI"
                ]
            elif career_path == "Web Developer":
                course_topics = [
                    "HTML/CSS/JavaScript Fundamentals",
                    "Frontend Frameworks",
                    "Backend Development & Databases"
                ]
            else:
                # Default courses if career path not recognized
                course_topics = [
                    "Computer Science Fundamentals",
                    "Programming Fundamentals",
                    "Software Development"
                ]
            
            # Create course objects for each topic
            for i, topic in enumerate(course_topics):
                new_course = Course(
                    title=topic,
                    description=f"Learn all about {topic.lower()} for your {career_path} career path",
                    category_name=career_path,
                    level="Beginner" if i == 0 else "Intermediate" if i == 1 else "Advanced",
                    user_id=current_user.id,
                    order=i+1
                )
                db.session.add(new_course)
            db.session.commit()
            
            # Reload courses after creating them
            courses = Course.query.filter_by(user_id=current_user.id).all()
    else:
        courses = []
    
    # Get progress for each course
    in_progress_courses = []
    completed_courses = []
    recommended_courses = []
    
    for course in courses:
        # Get modules for this course
        modules = Module.query.filter_by(course_id=course.id).all()
        
        # If no modules, generate them
        if not modules:
            # Get OpenRouter API key
            api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY
            if api_key:
                # Generate course overview using OpenRouter API
                prompt = (
                    f"Create a concise course overview about '{course.title}' for {learning_path.career_path} career path. "
                    "List 4-5 main chapters or modules. "
                    "Use a clear list format, like 'Chapter 1: Title', 'Module A: Title', or '1. Introduction'. "
                    "Put each chapter/module on a new line."
                    "Focus on distinct learning units."
                )
                try:
                    # Call OpenRouter API to generate course content
                    response = requests.post(
                        url=OPENROUTER_URL,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": request.host_url if hasattr(request, 'host_url') else "https://skillora.com",
                            "X-Title": "Skillora Learning Platform",
                        },
                        json={
                            "model": OPENROUTER_MODEL or "google/gemini-2.5-pro-exp-03-25:free",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        },
                        timeout=30
                    )
                    
                    # Process the response from OpenRouter to get course overview
                    if response.status_code == 200:
                        response_data = response.json()
                        course_overview = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    else:
                        print(f"Error from OpenRouter API: {response.status_code}")
                        print(f"Response: {response.text}")
                        course_overview = ""  # Default empty string if no response
                    
                    # Properly formatted try-except block
                    try:
                        # Parse chapters from the course overview
                        chapters = parse_chapters_simple(course_overview)
                        
                        # Use our new function to initialize modules with proper video-quiz alternating pattern
                        initialize_course_modules(course, chapters)
                    
                        if response.status_code != 200:
                            print(f"Error from OpenRouter API: {response.status_code}")
                            print(f"Response: {response.text}")
                    except Exception as e:
                        print(f"Error generating modules: {e}")
                        print((traceback.format_exc()))
                except Exception as e:
                    print(f"Error generating modules: {e}")
                    print((traceback.format_exc()))
        
        # Calculate course progress
        total_modules = len(modules) if modules else 0
        completed_modules = 0
        
        for module in modules:
            progress = UserProgress.query.filter_by(
                user_id=current_user.id, 
                module_id=module.id
            ).first()
            
            if progress and progress.is_completed:
                completed_modules += 1
        
        # Calculate percentage
        progress_percentage = 0
        if total_modules > 0:
            progress_percentage = int((completed_modules / total_modules) * 100)
        
        # Add course info for template
        course_info = {
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'category': course.category_name,
            'level': course.level,
            'progress': progress_percentage,
            'modules': modules,
            'total_modules': total_modules,
            'completed_modules': completed_modules
        }
        
        # Categorize course based on progress
        if progress_percentage == 100:
            completed_courses.append(course_info)
        elif progress_percentage > 0:
            in_progress_courses.append(course_info)
        else:
            # If no progress, it's a new course
            in_progress_courses.append(course_info)
    
    return render_template(
        'my_courses.html', 
        user=current_user,
        in_progress_courses=in_progress_courses,
        completed_courses=completed_courses,
        recommended_courses=recommended_courses,
        preferences=user_preferences
    )

@views.route('/learning-path')
@login_required
def learning_path():
    """Handle the learning path page - show user's personalized learning path."""
    try:
        # Check if user has completed the survey
        if not current_user.is_survey_completed:
            print("DEBUG: User has not completed survey, redirecting")
            flash('Please complete the CS interest survey before accessing your learning path.', category='info')
            return redirect(url_for('views.cs_interest_survey'))

        # Get the learning path for the user - if it doesn't exist, create a default one
        learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
        
        if not learning_path:
            print(f"DEBUG: Creating default learning path for user {current_user.id}")
            # If we somehow got here without a learning path, create a default one
            learning_path = LearningPath(
                user_id=current_user.id,
                career_path="Software Engineer",
                focus_areas=json.dumps(["Software Engineer"])
            )
            db.session.add(learning_path)
            db.session.commit()
            flash('Created a default learning path for you. Complete the survey for a personalized path.', category='info')
        
        # Standardized path names and descriptions
        path_details_map = {
            'Software Engineer': {
                'title': 'Software Engineer',
                'icon': 'fa-code',
                'duration': '9 months',
                'courses': 15,
                'modules': 5,
                'description': 'Master core software development concepts including algorithms, data structures, and software engineering principles.'
            },
            'Data Scientist': {
                'title': 'Data Scientist',
                'icon': 'fa-chart-bar',
                'duration': '8 months',
                'courses': 12,
                'modules': 4,
                'description': 'Learn to analyze complex data sets, build predictive models, and communicate insights using statistical methods.'
            },
            'Web Developer': {
                'title': 'Web Developer',
                'icon': 'fa-globe',
                'duration': '7 months',
                'courses': 14,
                'modules': 4,
                'description': 'Build modern web applications using front-end frameworks and back-end technologies with database integration.'
            },
            'Mobile Developer': {
                'title': 'Mobile Developer',
                'icon': 'fa-mobile-alt',
                'duration': '7 months',
                'courses': 12,
                'modules': 4,
                'description': 'Create native and cross-platform mobile applications for iOS and Android devices.'
            },
            'Cybersecurity Specialist': {
                'title': 'Cybersecurity Specialist',
                'icon': 'fa-shield-alt',
                'duration': '8 months',
                'courses': 15,
                'modules': 5,
                'description': 'Learn to protect systems, networks, and data from digital attacks and security breaches.'
            },
            'AI Engineer': {
                'title': 'AI Engineer',
                'icon': 'fa-robot',
                'duration': '9 months',
                'courses': 16,
                'modules': 5,
                'description': 'Build intelligent systems and algorithms that can learn from and make decisions based on data.'
            },
            'Game Developer': {
                'title': 'Game Developer',
                'icon': 'fa-gamepad',
                'duration': '8 months',
                'courses': 14,
                'modules': 4,
                'description': 'Design and develop interactive games for various platforms using industry-standard engines and techniques.'
            },
            'Systems Engineer': {
                'title': 'Systems Engineer',
                'icon': 'fa-microchip',
                'duration': '9 months',
                'courses': 15,
                'modules': 5,
                'description': 'Work with operating systems, networks, and hardware integration at a low level to build efficient systems.'
            }
        }
        
        # Get the career path from the learning path
        career_path = learning_path.career_path
        print(f"DEBUG: Career path from database: {career_path}")
        
        # Use the exact path key or find a close match
        if career_path in path_details_map:
            path_details = path_details_map[career_path]
        else:
            # Find a close match or use default
            for key in list(path_details_map.keys()):
                if key.lower() in career_path.lower() or career_path.lower() in key.lower():
                    path_details = path_details_map[key]
                    career_path = key  # Update career_path to matched key for module selection
                    break
            else:
                # Default to Software Engineer if no match found
                print(f"DEBUG: No match found for {career_path}, using default")
                path_details = path_details_map['Software Engineer']
                career_path = 'Software Engineer'  # Update career_path for module selection
                
        print(f"DEBUG: Using path details: {path_details}")
                    
        # Define personalized modules for each career path
        if career_path == "Software Engineer":
            modules = [
                {
                    'title': 'Programming Fundamentals',
                    'description': 'Master the core concepts of programming languages, data structures, and algorithms.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Programming Basics', 'Data Structures', 'Algorithms'],
                    'projects': ['Algorithm Implementation Project']
                },
                {
                    'title': 'Software Design & Architecture',
                    'description': 'Learn design patterns, software architecture, and best practices for maintainable code.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Object-Oriented Design', 'Design Patterns', 'Clean Code', 'Software Architecture'],
                    'projects': ['Design Patterns Implementation']
                },
                {
                    'title': 'Backend Development',
                    'description': 'Build robust server-side applications with databases, APIs, and cloud services.',
                    'duration': '10 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 2,
                    'courses': ['Database Design', 'API Development', 'Server Management', 'Cloud Services'],
                    'projects': ['REST API Project', 'Database-Driven Application']
                },
                {
                    'title': 'Software Testing & DevOps',
                    'description': 'Master testing methodologies, CI/CD, and DevOps practices for reliable software delivery.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Automated Testing', 'CI/CD Pipelines', 'DevOps Practices'],
                    'projects': ['Automated Testing Suite']
                },
                {
                    'title': 'Industry Projects',
                    'description': 'Apply all your skills in real-world projects and prepare for your career.',
                    'duration': '8 weeks',
                    'no_of_courses': 1,
                    'no_of_projects': 2,
                    'courses': ['Project Management'],
                    'projects': ['Capstone Project', 'Industry Collaboration Project']
                }
            ]
        elif career_path == "Data Scientist":
            modules = [
                {
                    'title': 'Data Analysis Fundamentals',
                    'description': 'Learn the basics of data analysis, statistics, and exploratory data analysis.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Statistics for Data Science', 'Python for Data Analysis', 'Exploratory Data Analysis'],
                    'projects': ['Data Analysis Project']
                },
                {
                    'title': 'Machine Learning Fundamentals',
                    'description': 'Master core machine learning algorithms, evaluation methods, and implementation.',
                    'duration': '8 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Supervised Learning', 'Unsupervised Learning', 'Model Evaluation'],
                    'projects': ['ML Model Implementation Project']
                },
                {
                    'title': 'Advanced Data Science',
                    'description': 'Explore deep learning, natural language processing, and computer vision.',
                    'duration': '10 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 2,
                    'courses': ['Deep Learning', 'Natural Language Processing', 'Computer Vision'],
                    'projects': ['Deep Learning Project', 'NLP/CV Application']
                },
                {
                    'title': 'Data Engineering & Deployment',
                    'description': 'Learn to build data pipelines and deploy models in production environments.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Data Engineering', 'MLOps', 'Model Deployment'],
                    'projects': ['End-to-End ML Pipeline']
                }
            ]
        elif career_path == "Web Developer":
            modules = [
                {
                    'title': 'Frontend Fundamentals',
                    'description': 'Master HTML, CSS, and JavaScript to create engaging user interfaces.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['HTML & CSS', 'JavaScript Fundamentals', 'Responsive Design'],
                    'projects': ['Interactive Website Project']
                },
                {
                    'title': 'Frontend Frameworks',
                    'description': 'Build dynamic web applications using modern frameworks and tools.',
                    'duration': '7 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['React.js', 'State Management', 'Frontend Testing'],
                    'projects': ['Single Page Application']
                },
                {
                    'title': 'Backend Development',
                    'description': 'Create server-side applications with databases and RESTful APIs.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Node.js', 'Express.js', 'Databases', 'REST APIs'],
                    'projects': ['Full-Stack Web Application']
                },
                {
                    'title': 'Web Application Deployment',
                    'description': 'Deploy and maintain web applications using DevOps and cloud services.',
                    'duration': '4 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Web Hosting', 'Containerization', 'CI/CD for Web'],
                    'projects': ['Production-Ready Web App']
                }
            ]
        elif career_path == "Mobile Developer":
            modules = [
                {
                    'title': 'Mobile Development Fundamentals',
                    'description': 'Learn the basics of mobile app development and user interface design.',
                    'duration': '5 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Mobile UI Design', 'App Architecture', 'Mobile Development Basics'],
                    'projects': ['Simple Mobile App']
                },
                {
                    'title': 'Native App Development',
                    'description': 'Build native applications for iOS and Android platforms.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Swift for iOS', 'Kotlin for Android', 'Native UI Components', 'Device Features'],
                    'projects': ['Native Mobile Application']
                },
                {
                    'title': 'Cross-Platform Development',
                    'description': 'Create applications that run on multiple platforms with a single codebase.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['React Native', 'Flutter', 'Cross-Platform State Management'],
                    'projects': ['Cross-Platform App']
                },
                {
                    'title': 'Mobile App Publishing & Monitoring',
                    'description': 'Learn to publish apps to stores, implement analytics, and maintain apps post-launch.',
                    'duration': '4 weeks',
                    'no_of_courses': 2,
                    'no_of_projects': 1,
                    'courses': ['App Store Optimization', 'Mobile Analytics & Monitoring'],
                    'projects': ['Production-Ready Mobile App']
                }
            ]
        elif career_path == "Cybersecurity Specialist":
            modules = [
                {
                    'title': 'Security Fundamentals',
                    'description': 'Learn the core concepts of cybersecurity and threat landscapes.',
                    'duration': '5 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Security Principles', 'Cryptography Basics', 'Threat Intelligence'],
                    'projects': ['Security Risk Assessment']
                },
                {
                    'title': 'Network & Application Security',
                    'description': 'Master techniques to secure networks and applications from attacks.',
                    'duration': '7 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Network Security', 'Secure Coding', 'Web Application Security', 'Penetration Testing'],
                    'projects': ['Vulnerability Assessment Project']
                },
                {
                    'title': 'Defensive Security',
                    'description': 'Learn to detect, respond to, and recover from security incidents.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Security Operations', 'Incident Response', 'Digital Forensics'],
                    'projects': ['Security Operations Center Simulation']
                },
                {
                    'title': 'Cloud & Infrastructure Security',
                    'description': 'Secure cloud environments and critical infrastructure systems.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Cloud Security', 'Container Security', 'Infrastructure as Code Security'],
                    'projects': ['Secure Cloud Architecture']
                },
                {
                    'title': 'Governance & Compliance',
                    'description': 'Implement security governance frameworks and ensure regulatory compliance.',
                    'duration': '4 weeks',
                    'no_of_courses': 2,
                    'no_of_projects': 1,
                    'courses': ['Security Governance', 'Compliance Frameworks'],
                    'projects': ['Compliance Program Implementation']
                }
            ]
        elif career_path == "AI Engineer":
            modules = [
                {
                    'title': 'AI Fundamentals',
                    'description': 'Learn the foundations of artificial intelligence and machine learning.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Introduction to AI', 'Machine Learning Basics', 'Neural Networks'],
                    'projects': ['Basic ML Model Implementation']
                },
                {
                    'title': 'Deep Learning',
                    'description': 'Master deep learning architectures and techniques for complex AI tasks.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Convolutional Neural Networks', 'Recurrent Neural Networks', 'Transformer Models', 'Generative Models'],
                    'projects': ['Deep Learning Application']
                },
                {
                    'title': 'Natural Language Processing',
                    'description': 'Build AI systems that understand, interpret, and generate human language.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Text Processing', 'Language Models', 'Dialog Systems'],
                    'projects': ['NLP Application']
                },
                {
                    'title': 'Computer Vision',
                    'description': 'Create AI systems that can process and analyze visual data.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Image Processing', 'Object Detection', 'Image Generation'],
                    'projects': ['Computer Vision System']
                },
                {
                    'title': 'AI Engineering & Deployment',
                    'description': 'Learn to deploy and maintain AI systems in production environments.',
                    'duration': '5 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['MLOps', 'AI Ethics', 'Model Deployment'],
                    'projects': ['Production AI System']
                }
            ]
        elif career_path == "Game Developer":
            modules = [
                {
                    'title': 'Game Development Fundamentals',
                    'description': 'Learn the core concepts of game development and design.',
                    'duration': '5 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Game Design Principles', 'Game Engines Intro', '2D Game Development'],
                    'projects': ['Simple 2D Game']
                },
                {
                    'title': '3D Game Development',
                    'description': 'Create immersive 3D games with advanced game engines.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['3D Modeling', 'Unity Development', 'Game Physics', '3D Animation'],
                    'projects': ['3D Game Prototype']
                },
                {
                    'title': 'Game Programming',
                    'description': 'Master programming techniques specific to game development.',
                    'duration': '7 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Game AI', 'Multiplayer Programming', 'Game Systems Development'],
                    'projects': ['Game Programming Project']
                },
                {
                    'title': 'Game Production',
                    'description': 'Learn the complete game production pipeline from concept to release.',
                    'duration': '6 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Game Project Management', 'Testing & Quality Assurance', 'Game Optimization', 'Publishing & Monetization'],
                    'projects': ['Complete Game Project']
                }
            ]
        elif career_path == "Systems Engineer":
            modules = [
                {
                    'title': 'Operating Systems Fundamentals',
                    'description': 'Master the core concepts of operating systems and system programming.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Operating Systems Theory', 'System Programming', 'Memory Management'],
                    'projects': ['Custom OS Component']
                },
                {
                    'title': 'Distributed Systems',
                    'description': 'Design and implement distributed computing systems and architectures.',
                    'duration': '7 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Distributed Computing', 'Consensus Algorithms', 'Fault Tolerance', 'Distributed Databases'],
                    'projects': ['Distributed System Implementation']
                },
                {
                    'title': 'Infrastructure & Networking',
                    'description': 'Build and manage complex network infrastructure and systems.',
                    'duration': '8 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Network Protocols', 'Infrastructure as Code', 'Containerization', 'Cloud Services'],
                    'projects': ['Automated Infrastructure Project']
                },
                {
                    'title': 'Performance Engineering',
                    'description': 'Optimize system performance, reliability, and scalability.',
                    'duration': '6 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Performance Analysis', 'Scalability Design', 'Capacity Planning'],
                    'projects': ['System Optimization Project']
                },
                {
                    'title': 'Systems Security',
                    'description': 'Secure low-level systems and infrastructure against attacks.',
                    'duration': '5 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Secure System Design', 'Kernel Security', 'Infrastructure Security'],
                    'projects': ['Security Hardening Project']
                }
            ]
        else:
            # Default modules as fallback (same as Software Engineer)
            modules = [
                {
                    'title': 'Programming Fundamentals',
                    'description': 'Understand the basic concepts of programming and algorithms that form the foundation of software development.',
                    'duration': '4 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 1,
                    'courses': ['Introduction to Programming Logic', 'Basic Data Structures', 'Basic Algorithms'],
                    'projects': ['Programming Fundamentals Project']
                },
                {
                    'title': 'Frameworks & Advanced Development',
                    'description': 'Learn about frameworks and advanced development techniques used in the industry.',
                    'duration': '6 weeks',
                    'no_of_courses': 4,
                    'no_of_projects': 1,
                    'courses': ['Introduction to Frameworks', 'API Development', 'Advanced Database Integration', 'Testing and Deployment'],
                    'projects': ['Framework Application Project']
                },
                {
                    'title': 'Real Projects & Career Preparation',
                    'description': 'Apply your skills in real projects and prepare yourself for a professional career.',
                    'duration': '8 weeks',
                    'no_of_courses': 3,
                    'no_of_projects': 2,
                    'courses': ['Software Project Management', 'Best Practices & User Experience', 'Portfolio & Interview Preparation'],
                    'projects': ['Capstone Project', 'Work Environment Simulation']
                }
            ]

        # Hardcoded progress for prototype
        progress_percentage = 85
        
        # Render the template with all needed data
        return render_template(
            'learning_path.html',
            user=current_user,
            path_name=career_path,
            path_details=path_details,
            modules=modules,
            progress_percentage=progress_percentage
        )
        
    except Exception as e:
        # Display error details in console for debugging
        print(f"ERROR in learning_path route: {str(e)}")
        print((traceback.format_exc()))
        
        # Show user-friendly error message
        flash('An error occurred while loading your learning path. Please try again later.', category='error')
        return redirect(url_for('views.home'))

@views.route('/schedule')
@login_required
def schedule():
    return render_template('schedule.html', user=current_user)

@views.route('/library')
@login_required
def library():
    return render_template('library.html', user=current_user)

@views.route('/tutors')
@login_required
def tutors():
    return render_template('tutors.html', user=current_user)

@views.route('/progress')
@login_required
def progress():
    if not current_user.is_survey_completed:
        flash('Please complete the CS interest survey before accessing your progress.', category='info')
        return redirect(url_for('views.cs_interest_survey'))
    return render_template('progress.html', user=current_user)

# --- Profile Routes ---
@views.route('/profile')
@login_required
def profile():
    # Get skills and interests - Note: Skills seem to be stored in 'bio' field? Revisit if needed.
    # Assuming skills are comma-separated in the 'bio' field for now.
    skills = current_user.bio.split(',') if current_user.bio else []
    skills = [s.strip() for s in skills if s.strip()] # Clean up spaces

    interests = [] # Where should interests come from? Maybe survey? Add logic if needed.

    date_of_birth_formatted = ''
    if current_user.date_of_birth:
        try:
            date_of_birth_formatted = current_user.date_of_birth.strftime("%B %d, %Y")
        except ValueError as e:
            date_of_birth_formatted = "Invalid Date" # Handle potential invalid date format
            print(f"ERROR formatting date: {str(e)}")
    
    member_since = current_user.created_at.strftime("%B %Y") if current_user.created_at else "N/A"
    
    return render_template(
        "profile.html", 
        user=current_user,
        skills=skills,
        interests=interests, # Pass interests here
        date_of_birth_formatted=date_of_birth_formatted,
        member_since=member_since
    )

@views.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            date_of_birth = request.form.get('date_of_birth')
            location = request.form.get('location')
            username = request.form.get('username') # Assuming username can be updated
            
            dob_date = None
            if date_of_birth:
                try:
                    dob_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format for date of birth (YYYY-MM-DD)', 'error')
                    # Don't proceed with update if date is invalid
                    return redirect(url_for('views.profile'))
            
            if not first_name:
                flash('First name is required', 'error')
                return redirect(url_for('views.profile'))
            # Add username validation if necessary (e.g., check uniqueness if changed)
                
            success = update_user_profile(
                current_user.id,
                first_name=first_name,
                last_name=last_name,
                username=username, # Add username update
                phone=phone,
                date_of_birth=dob_date,
                location=location
            )
                
            if success:
                flash('Profile updated successfully!', 'success')
            else:
                # update_user_profile should ideally raise an exception on failure
                flash('An error occurred while updating your profile', 'error')
                
            return redirect(url_for('views.profile'))
            
        except Exception as e:
            # Log the full error
            print(f"ERROR updating profile: {str(e)}\n{traceback.format_exc()}")
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('views.profile'))

@views.route('/profile/update-bio', methods=['POST'])
@login_required
def update_bio():
    """Update user bio, job title, and potentially skills (if stored differently)"""
    if request.method == 'POST':
        try:
            bio_text = request.form.get('bio') # This might contain skills based on profile view
            job_title = request.form.get('job_title')
            # If skills are handled separately, get them here:
            # skills = request.form.get('skills')

            success = update_user_profile(
                current_user.id,
                bio=bio_text, # Update bio field
                job_title=job_title
                # Add skills field update if needed: skills=skills
            )
                
            if success:
                flash('Bio and Job Title updated successfully!', 'success')
            else:
                flash('An error occurred while updating your bio', 'error')
                
            return redirect(url_for('views.profile'))
            
        except Exception as e:
            print(f"ERROR updating bio: {str(e)}\n{traceback.format_exc()}")
            flash(f'An unexpected error occurred: {str(e)}', 'error')
            return redirect(url_for('views.profile'))

# --- API Routes for Profile ---
@views.route('/api/profile', methods=['GET'])
@login_required
def api_get_profile():
    """API to get profile data as JSON"""
    user_data = {
        'id': current_user.id,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'username': current_user.username,
        'phone': current_user.phone,
        'date_of_birth': current_user.date_of_birth.isoformat() if current_user.date_of_birth else None,
        'bio': current_user.bio,
        'location': current_user.location,
        'job_title': current_user.job_title,
        'member_since': current_user.created_at.strftime("%B %Y") if current_user.created_at else None,
        'is_survey_completed': current_user.is_survey_completed
    }
    return jsonify(user_data)

@views.route('/api/profile/update', methods=['POST'])
@login_required
def api_update_profile():
    """API to update profile data via JSON"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        update_fields = {}
        allowed_fields = [
            'first_name', 'last_name', 'phone', 'bio', 
            'location', 'job_title', 'username'
        ]
        
        for field in allowed_fields:
            if field in data:
                update_fields[field] = data[field]
        
        if 'date_of_birth' in data:
            dob_str = data['date_of_birth']
            if dob_str:
                try:
                    dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    update_fields['date_of_birth'] = dob_date
                except (ValueError, TypeError) as e:
                    return jsonify({'success': False, 'message': 'Invalid date format for date of birth (YYYY-MM-DD)'}), 400
            else:
                update_fields['date_of_birth'] = None # Allow clearing the date

        if not update_fields:
             return jsonify({'success': False, 'message': 'No valid fields provided for update'}), 400

        success = update_user_profile(current_user.id, **update_fields)
        
        if success:
            # Fetch updated user data to return
            updated_user = User.query.get(current_user.id)
            user_data = {
                'id': updated_user.id, 'email': updated_user.email, 'first_name': updated_user.first_name,
                'last_name': updated_user.last_name, 'username': updated_user.username, 'phone': updated_user.phone,
                'date_of_birth': updated_user.date_of_birth.isoformat() if updated_user.date_of_birth else None,
                'bio': updated_user.bio, 'location': updated_user.location, 'job_title': updated_user.job_title
            }
            return jsonify({'success': True, 'message': 'Profile updated successfully', 'user': user_data})
        else:
            return jsonify({'success': False, 'message': 'Failed to update profile'}), 500
            
    except Exception as e:
        print(f"ERROR in api_update_profile: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'An internal server error occurred: {str(e)}'}), 500

# --- Settings, Help, Debug ---
@views.route('/settings')
@login_required
def settings():
    return render_template("settings.html", user=current_user)

@views.route('/help')
@login_required
def help():
    return render_template("help.html", user=current_user)

@views.route('/debug_home')
def debug_home():
    """A debug route that just renders the home template without any logic"""
    if not current_user.is_authenticated:
        return "You are not logged in. Please log in to view the home page."
    mock_user = {'first_name': getattr(current_user, 'first_name', 'Debug User')}
    return render_template('home.html', user=current_user) # Pass current_user for consistency

# --- AI Chat API ---
@views.route('/api/chat', methods=['POST'])
@login_required
def chat_with_ai():
    """API endpoint for AI chat using OpenRouter."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'message': 'No message provided'}), 400
            
        user_message = data['message']
        if not user_message.strip() and 'imageUrl' not in data:
            return jsonify({'success': False, 'message': 'Message cannot be empty and no image provided'}), 400

        # --- Get Chat History from DB ---
        try:
            db_messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(
                ChatMessage.created_at.asc() # Get in chronological order
            ).limit(MAX_CHAT_HISTORY).all()
            
            # Build history in OpenAI format
            chat_history = []
            for msg in db_messages:
                chat_history.append({
                    "role": msg.role, # Should be 'user' or 'assistant'
                    "content": msg.content
                })
        except Exception as db_error:
            print(f"ERROR retrieving chat history: {str(db_error)}\n{traceback.format_exc()}")
            flash('Could not retrieve chat history.', 'error') # Inform user via flash if appropriate
            chat_history = [] # Start fresh if DB fails

        # Check if there's an image URL in the request
        image_url = data.get('imageUrl')
        
        # If we have an image URL, include it in the user message
        if image_url:
            # Format the message to include the image
            if user_message.strip():
                # Both text and image
                user_message = f"{user_message}\n\n[IMAGE: {image_url}]"
            else:
                # Image only
                user_message = f"[IMAGE: {image_url}]"
                
            # Save user message with image in DB if not already saved during upload
            if '[IMAGE:' not in user_message:
                try:
                    ChatMessage.add_message(user_id=current_user.id, role="user", content=user_message)
                except Exception as db_error:
                    print(f"ERROR saving chat message with image: {str(db_error)}\n{traceback.format_exc()}")
                    # Don't fail the whole request, but log it

        # --- Prepare messages for API ---
        # Combine history and current message
        current_conversation = chat_history + [{"role": "user", "content": user_message}]

        # Get system prompt from configuration
        system_prompt = SYSTEM_PROMPT
        if not system_prompt:
            system_prompt = "You are Skillora AI, a learning assistant that helps users with educational questions."
            
        # If we have an image, add instructions about image handling to the system prompt
        if image_url:
            image_instruction = "\nThe user has shared an image. The image URL is provided within [IMAGE: url] tags. Please acknowledge the image and respond appropriately based on its content if visible to you. If you cannot see or process the image, politely inform the user that you can't view the image but you'll do your best to help with their question."
            system_prompt += image_instruction
        
        # Add system message if we have one and the API supports it
        messages = convert_messages_format(current_conversation)
        if system_prompt:
            # Add system message at the beginning
            messages.insert(0, {"role": "system", "content": system_prompt})

        # --- Get preferences and adjust temperature ---
        preferences = data.get('preferences', {})
        response_style = preferences.get('response_style', 'balanced') # Default style
        temp = TEMPERATURE # Default temperature
        if response_style == 'concise':
            temp = max(0.2, TEMPERATURE - 0.3) # Lower temp
        elif response_style == 'detailed':
            temp = min(0.9, TEMPERATURE + 0.2) # Higher temp

        # --- Get API key ---
        api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY
        if not api_key:
            return jsonify({'success': False, 'message': 'OpenRouter API key not configured'}), 500
            
        # --- Set up API Request ---
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": request.host_url,  # Using the current application URL
            "X-Title": "Skillora Learning Platform",
        }
        
        # Define the model to use (from config or use default)
        model = "google/gemini-2.0-flash-exp:free"
        
        # --- OpenRouter Payload ---
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": MAX_TOKENS
        }

        # --- Log Request ---
        print(f"--- OpenRouter API Request ---")
        print(f"URL: {OPENROUTER_URL}")
        print(f"Model: {model}")
        print(f"Temperature: {temp}")
        print(f"Message count: {len(messages)}")
        print(f"Contains image: {'Yes' if image_url else 'No'}")
        print(f"-------------------------")

        # --- Make the API Call ---
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=45 # Increased timeout slightly
            )

            # --- Process Response ---
            print(f"--- OpenRouter API Response ---")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = "Unknown error"
                try:
                    response_data = response.json()
                    error_detail = response_data.get('error', {}).get('message', 'Unknown error')
                except:
                    error_detail = response.text[:100]  # First 100 chars of response
                
                print(f"Error from OpenRouter: {error_detail}")
                return jsonify({
                    'success': False, 
                    'error_type': 'api_error', 
                    'message': f'AI service returned error: {error_detail}'
                }), 502  # Bad Gateway
            
            # Parse the successful response
            try:
                response_data = response.json()
                
                # Extract the AI response text
                ai_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                if not ai_response:
                    return jsonify({
                        'success': False,
                        'error_type': 'api_response_format',
                        'message': 'Empty response from AI service'
                    }), 500
                
                # Strip any leading/trailing whitespace
                ai_response = ai_response.strip()
                            
                # Save user message in DB (if not already saved) only for text-only messages
                if not image_url:
                    try:
                        ChatMessage.add_message(user_id=current_user.id, role="user", content=user_message)
                    except Exception as db_error:
                        print(f"ERROR saving user message: {str(db_error)}\n{traceback.format_exc()}")
                
                # Save AI response
                try:
                    ChatMessage.add_message(user_id=current_user.id, role="assistant", content=ai_response)
                    print("DEBUG: AI message saved to DB.")
                except Exception as db_error:
                    print(f"ERROR saving AI message: {str(db_error)}\n{traceback.format_exc()}")
                    # Don't fail the whole request, but log it
                
                # --- Return Success ---
                return jsonify({
                    'success': True,
                    'response': ai_response,
                    'timestamp': datetime.now().isoformat() # Use ISO format for consistency
                })
            except ValueError as e:
                print(f"ERROR parsing JSON response: {str(e)}")
                return jsonify({
                    'success': False,
                    'error_type': 'api_response',
                    'message': 'Error parsing response from AI service',
                    'technical_details': f"JSON Error: {str(e)}"
                }), 500

        except requests.exceptions.Timeout:
            print(f"ERROR: Timeout connecting to OpenRouter API")
            return jsonify({'success': False, 'error_type': 'timeout', 'message': 'Connection to AI timed out. Please try again later.'}), 504 # Gateway Timeout
        except requests.exceptions.RequestException as e:
            # Includes connection errors, DNS errors, etc.
            error_details = str(e)
            print(f"ERROR: Network error during API call: {error_details}\n{traceback.format_exc()}")
            return jsonify({'success': False, 'error_type': 'api_request_failed', 'message': 'A network error occurred while contacting the AI.', 'technical_details': error_details}), 503 # Service Unavailable
            
    except Exception as e:
        # General catch-all for unexpected errors in the function
        error_traceback = traceback.format_exc()
        print(f"FATAL ERROR in chat_with_ai: {str(e)}\n{error_traceback}")
        return jsonify({'success': False, 'error_type': 'server_error', 'message': 'An internal server error occurred.', 'technical_details': str(e)}), 500

# --- Clear Chat History API ---
@views.route('/api/chat/clear', methods=['POST'])
@login_required
def clear_chat_history():
    """Clear the chat history stored in the database"""
    try:
        # Clear chat history from database
        num_deleted = ChatMessage.clear_chat_history(current_user.id)
        print(f"DEBUG: Cleared {num_deleted} chat messages from database for user {current_user.id}")

        return jsonify({'success': True, 'message': 'Chat history cleared successfully'})
    except Exception as e:
        print(f"Error clearing chat history: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

# --- CS Interest Survey Routes ---
@views.route('/cs-interest-survey', methods=['GET', 'POST'])
@login_required
def cs_interest_survey():
    """Handle the CS interest survey page"""
    # Redirect if already completed
    if current_user.is_survey_completed and request.method == 'GET':
        flash('You have already completed the survey. Viewing your learning path.', category='info')
        return redirect(url_for('views.learning_path'))

    # Handle form submission
    if request.method == 'POST':
        try:
            # Get form data (using .get with default None and type conversion)
            algorithms = request.form.get('algorithms_interest', default=None, type=int)
            data_science = request.form.get('data_science_interest', default=None, type=int)
            web_dev = request.form.get('web_development_interest', default=None, type=int)
            mobile_dev = request.form.get('mobile_development_interest', default=None, type=int)
            cybersecurity = request.form.get('cybersecurity_interest', default=None, type=int)
            ai = request.form.get('artificial_intelligence_interest', default=None, type=int)
            game_dev = request.form.get('game_development_interest', default=None, type=int)
            systems = request.form.get('systems_programming_interest', default=None, type=int)

            # Add validation: Ensure required fields (e.g., interest ratings) are provided
            interest_fields = [algorithms, data_science, web_dev, mobile_dev, cybersecurity, ai, game_dev, systems]
            if any(interest is None for interest in interest_fields):
                flash('Please rate your interest in all technical areas.', category='error')
                # Render the form again, potentially passing back submitted values
                return render_template('cs_interest_survey.html', user=current_user, submitted_data=request.form)

            learning_style = request.form.get('preferred_learning_style')
            career_goal = request.form.get('career_goal')
            prior_experience = request.form.get('prior_experience')
            time_availability = request.form.get('learning_time_availability')

            # Check if user already has a survey record
            survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()

            if not survey:
                survey = CSInterestSurvey(user_id=current_user.id)
                db.session.add(survey)
                print(f"DEBUG: Creating new survey record for user {current_user.id}")
            else:
                print(f"DEBUG: Updating existing survey record for user {current_user.id}")

            # Update survey fields
            survey.algorithms_interest = algorithms
            survey.data_science_interest = data_science
            survey.web_development_interest = web_dev
            survey.mobile_development_interest = mobile_dev
            survey.cybersecurity_interest = cybersecurity
            survey.artificial_intelligence_interest = ai
            survey.game_development_interest = game_dev
            survey.systems_programming_interest = systems
            survey.preferred_learning_style = learning_style
            survey.career_goal = career_goal
            survey.prior_experience = prior_experience
            survey.learning_time_availability = time_availability
            survey.updated_at = datetime.utcnow() # Use UTC time

            # Mark the survey as completed for the user
            current_user.is_survey_completed = True

            # Create or update learning path based on survey results
            interest_scores = {
                'Software Engineer': survey.algorithms_interest or 1,
                'Data Scientist': survey.data_science_interest or 1,
                'Web Developer': survey.web_development_interest or 1,
                'Mobile Developer': survey.mobile_development_interest or 1,
                'Cybersecurity Specialist': survey.cybersecurity_interest or 1,
                'AI Engineer': survey.artificial_intelligence_interest or 1,
                'Game Developer': survey.game_development_interest or 1,
                'Systems Engineer': survey.systems_programming_interest or 1
            }
            
            # Find the career path with the highest interest score
            recommended_career = max(interest_scores, key=interest_scores.get)
            
            # Create or update learning path
            learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
            if not learning_path:
                learning_path = LearningPath(
                    user_id=current_user.id,
                    career_path=recommended_career,
                    focus_areas=json.dumps([k for k, v in list(interest_scores.items()) if v >= 4])  # Areas with high interest
                )
                db.session.add(learning_path)
                print(f"DEBUG: Created new learning path with career: {recommended_career}")
            else:
                learning_path.career_path = recommended_career
                learning_path.focus_areas = json.dumps([k for k, v in list(interest_scores.items()) if v >= 4])
                learning_path.date_updated = datetime.utcnow()
                print(f"DEBUG: Updated existing learning path to: {recommended_career}")

            # Commit the changes (survey, user update, and learning path)
            db.session.commit()

            # Store generation task information in the session
            session['course_generation'] = {
                'status': 'pending',
                'percent': 0,
                'step': 1,
                'message': 'Starting course generation process...',
                'career_path': recommended_career,
                'learning_style': learning_style,
                'time_availability': time_availability
            }

            # Redirect to loading page instead of learning path
            flash('Survey submitted successfully! We are now generating your personalized courses...', category='success')
            return redirect(url_for('views.generate_courses'))
        except Exception as e:
            db.session.rollback() # Rollback on error
            print(f"ERROR submitting survey: {str(e)}\n{traceback.format_exc()}")
            flash(f'An error occurred while submitting the survey: {str(e)}', category='error')
            # Redirect back to the survey form on error
            return redirect(url_for('views.cs_interest_survey'))

    # GET request - show the survey form
    # Check if there's existing survey data to pre-fill the form (e.g., if validation failed on POST)
    existing_survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
    return render_template('cs_interest_survey.html', user=current_user, survey_data=existing_survey)

@views.route('/reset-survey')
@login_required
def reset_survey():
    """Reset the CS interest survey data for the current user."""
    try:
        # Find existing survey
        survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
        
        if survey:
            # Option 1: Delete the survey entry completely
            # db.session.delete(survey)
            
            # Option 2: Reset all survey values to None/defaults
            survey.algorithms_interest = None
            survey.data_science_interest = None
            survey.web_development_interest = None
            survey.mobile_development_interest = None
            survey.cybersecurity_interest = None
            survey.artificial_intelligence_interest = None
            survey.game_development_interest = None
            survey.systems_programming_interest = None
            survey.preferred_learning_style = None
            survey.career_goal = None
            survey.prior_experience = None
            survey.learning_time_availability = None
            survey.updated_at = datetime.utcnow()
        
        # Mark survey as not completed regardless if survey exists
        current_user.is_survey_completed = False
        
        # Commit changes
        db.session.commit()
        
        flash('Your CS interest survey has been reset. Please complete the survey again.', category='success')
    except Exception as e:
        db.session.rollback()  # Rollback on error
        print(f"ERROR resetting survey: {str(e)}\n{traceback.format_exc()}")
        flash(f'An error occurred while resetting your survey: {str(e)}', category='error')
    
    # Redirect to the survey page
    return redirect(url_for('views.cs_interest_survey'))

# Add this function before generate_module_content
def is_youtube_video_available(video_id):
    """
    Check if a YouTube video is available (not deleted, private, or region-restricted).
    Returns True if the video is available, False otherwise.
    """
    try:
        # Use requests to check if the video page is accessible
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.head(url, timeout=3)  # Quick HEAD request to avoid downloading content
        return response.status_code == 200
    except Exception:
        # Any error means the video is likely not available
        return False

def extract_valid_youtube_urls(text, max_urls=5, check_availability=True):
    """
    Extracts valid YouTube URLs from text and performs validation.
    Returns a list of validated URLs up to max_urls.
    
    Parameters:
    - text: The text to extract YouTube URLs from
    - max_urls: Maximum number of URLs to extract
    - check_availability: If True, checks if videos are actually available using HTTP requests
    """
    # First, try to find all possible YouTube URLs with a comprehensive regex
    # This regex handles various YouTube URL formats
    youtube_regex = r'(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/user\/[^\/]+\/[^\/]+\/|youtube\.com\/[^\/]+\/[^\/]+\/|youtube\.com\/verify_age\?next_url=\/watch%3Fv%3D)([a-zA-Z0-9_-]{11})'
    
    matches = re.findall(youtube_regex, text)
    
    # Process and validate matches
    valid_urls = []
    seen_ids = set()  # To prevent duplicates
    
    print(f"Starting with {len(matches)} potential YouTube URL matches")
    
    for match in matches:
        # Extract the video ID (last group in the regex)
        video_id = match[3]
        
        # Skip if we've already seen this video ID
        if video_id in seen_ids:
            continue
        
        # Skip YouTube shorts
        if 'shorts' in ''.join(match):
            continue
        
        # If requested, verify the video is actually available
        if check_availability:
            if not is_youtube_video_available(video_id):
                print(f"Skipping unavailable YouTube video: {video_id}")
                continue
        
        # Construct a canonical URL
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        valid_urls.append(canonical_url)
        seen_ids.add(video_id)
        
        # Stop if we've reached the maximum number of URLs
        if len(valid_urls) >= max_urls:
            break
    
    # If we didn't find enough URLs with the regex, try a simpler approach
    if len(valid_urls) < max_urls:
        # Look for text that might be a YouTube URL but didn't match the regex
        simpler_regex = r'https?:\/\/(www\.)?youtu(be\.com|\.be)\S+'
        additional_matches = re.findall(simpler_regex, text)
        
        for match in additional_matches:
            # Look for valid YouTube IDs in the matched text
            full_match_str = f"https://{match[0]}youtu{match[1]}"
            # Skip if this contains '/shorts/'
            if '/shorts/' in full_match_str:
                continue
                
            # Extract all possible 11-character IDs that look like YouTube IDs
            potential_ids = re.findall(r'([a-zA-Z0-9_-]{11})', full_match_str)
            for video_id in potential_ids:
                if video_id not in seen_ids:
                    # Verify availability if requested
                    if check_availability:
                        if not is_youtube_video_available(video_id):
                            continue
                        
                    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
                    valid_urls.append(canonical_url)
                    seen_ids.add(video_id)
                    
                    if len(valid_urls) >= max_urls:
                        break
            
            if len(valid_urls) >= max_urls:
                break
    
    print(f"Found {len(valid_urls)} valid and available YouTube URLs")
    return valid_urls

# Now improve the generate_module_content function to use our enhanced YouTube URL validation
@views.route('/generate_module_content/<int:module_id>', methods=['POST'])
@login_required
def generate_module_content(module_id):
    """Generate educational content for a module using Manim"""
    print(f"\n[VIDEO GENERATION] Starting for module ID: {module_id}")
    
    module = Module.query.get_or_404(module_id)
    print(f"[VIDEO GENERATION] Module title: {module.title}")
    
    # Make sure the module belongs to the current user
    course = Course.query.get_or_404(module.course_id)
    if course.user_id != current_user.id:
        print(f"[VIDEO GENERATION] ERROR: Module doesn't belong to current user")
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # If this is a quiz module, we shouldn't be generating video content
    if module.content_type == 'quiz':
        print(f"[VIDEO GENERATION] ERROR: Cannot generate video content for quiz modules")
        return jsonify({'success': False, 'error': 'Cannot generate video content for quiz modules'}), 400
    
    # Set the content type explicitly to video
    module.content_type = 'video'
    
    # Get user learning preferences to personalize content
    preferences = CSInterest.query.filter_by(user_id=current_user.id).first()
    learning_style = preferences.learning_style if preferences else "visual"
    print(f"[VIDEO GENERATION] User learning style: {learning_style}")
    
    # Get preferred learning duration from user preferences or settings
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    preferred_duration = 15  # Default to 15 minutes
    
    if user_settings and hasattr(user_settings, 'preferred_video_duration'):
        preferred_duration = user_settings.preferred_video_duration
    
    print(f"[VIDEO GENERATION] Preferred duration: {preferred_duration} minutes")
    
    try:
        # Import the Manim utilities
        from .manim import generate_and_save_manim_video
        
        # Generate educational content about the module topic
        # We'll use a simple description for now - in a real app you'd use GPT/Gemini to generate detailed content
        module_description = f"An educational overview of {module.title}, covering key concepts and applications."
        
        # Define the output path for the video
        videos_folder = os.path.join("Backend", "website", "static", "uploads", "manim_videos")
        os.makedirs(videos_folder, exist_ok=True)
        
        # Create a safe filename
        safe_title = ''.join(c if c.isalnum() else '_' for c in module.title)
        unique_id = str(uuid.uuid4())[:8]
        video_filename = f"{safe_title}_{unique_id}.mp4"
        video_path = os.path.join(videos_folder, video_filename)
        
        print(f"[VIDEO GENERATION] Generating Manim video for '{module.title}'")
        print(f"[VIDEO GENERATION] Output path: {video_path}")
        
        # Generate the Manim video
        output_path = generate_and_save_manim_video(
            topic=module.title,
            content=module_description,
            learning_style=learning_style,
            output_path=video_path
        )
        
        if not output_path:
            print(f"[VIDEO GENERATION] Failed to generate Manim video")
            # Fallback to YouTube links as a backup solution
            print(f"[VIDEO GENERATION] Falling back to YouTube links")
            return fallback_to_youtube_links(module, learning_style, preferred_duration)
        
        print(f"[VIDEO GENERATION] Successfully generated Manim video at: {output_path}")
        
        # Convert the output path to a URL path that can be accessed by the frontend
        # The path should be relative to the static folder
        relative_path = os.path.relpath(output_path, os.path.join("Backend", "website", "static"))
        video_url = url_for('static', filename=relative_path)
        
        print(f"[VIDEO GENERATION] Video URL for frontend: {video_url}")
        
        # Store the video URL in the module
        module.manim_video_path = output_path
        
        # Also store a YouTube link as a fallback (empty list for now)
        module.youtube_links = "[]"
        
        # Update the module in the database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Generated educational content successfully',
            'video_path': video_url
        })
        
    except Exception as e:
        print(f"[VIDEO GENERATION] Error generating Manim video: {str(e)}")
        print(f"[VIDEO GENERATION] Traceback: {traceback.format_exc()}")
        
        # Fallback to YouTube links if Manim fails
        print(f"[VIDEO GENERATION] Falling back to YouTube links due to error")
        return fallback_to_youtube_links(module, learning_style, preferred_duration)

def fallback_to_youtube_links(module, learning_style, preferred_duration):
    """Fallback method to find YouTube links if Manim generation fails"""
    try:
        print(f"[YOUTUBE FALLBACK] Finding YouTube videos for '{module.title}'")
        
        # Create a search query based on learning style
        search_term = module.title
        
        # Define detailed style-specific terms for better matching 
        style_specific_terms = {
            "hands-on": {
                "terms": ["project-based tutorial", "practical demonstration", "coding exercise", "hands-on workshop", "interactive lesson"],
                "excluded": ["lecture", "theoretical"]
            },
            "auditory": {
                "terms": ["lecture", "explanation", "discussion", "talk", "spoken tutorial"],
                "excluded": ["no commentary", "text only"]
            },
            "visual": {
                "terms": ["visual explanation", "diagram-based", "animated tutorial", "illustration", "visual guide"],
                "excluded": ["audio only", "no visuals"]
            }
        }
        
        # Select style modifiers - choose 2 random terms from the appropriate style
        style_info = style_specific_terms.get(learning_style, 
                                            {"terms": ["tutorial"], "excluded": []})
        
        import random
        selected_terms = random.sample(style_info["terms"], min(2, len(style_info["terms"])))
        
        # Build a more sophisticated search query
        search_query = f"{search_term} " + " ".join(selected_terms)
        print(f"[YOUTUBE FALLBACK] Search query: {search_query}")
        
        # Add duration preference modifiers
        duration_min = max(1, preferred_duration - 5)
        duration_max = preferred_duration + 5
        
        if preferred_duration <= 10:
            search_query += " short tutorial"
        elif preferred_duration >= 30:
            search_query += " comprehensive lesson"
        
        # STEP 1: Get candidate videos using OpenRouter API to access Gemini
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print(f"[YOUTUBE FALLBACK] ERROR: OpenRouter API key not found")
            return jsonify({'success': False, 'error': 'OpenRouter API key not found'}), 500
            
        print(f"[YOUTUBE FALLBACK] OpenRouter API key found")
        
        # Create a detailed prompt for finding appropriate videos
        search_prompt = (
            f"Search YouTube for high-quality educational videos about: '{search_query}'. "
            f"The user prefers the {learning_style} learning style and videos between {duration_min}-{duration_max} minutes long. "
            f"Find 6-8 highly relevant videos from reputable educational channels. "
            f"For each video, include ONLY the following information:"
            f"1. The full YouTube URL (must start with https://www.youtube.com/watch?v= or https://youtu.be/)"
            f"2. The title of the video"
            f"3. The channel name"
            f"\nFormat the response as a numbered list with one video per line."
            f"\nEnsure all URLs are valid YouTube video URLs from established channels (not shorts, playlists, or channels)."
            f"\nPROVIDE ONLY YOUTUBE VIDEOS THAT ARE PUBLICLY AVAILABLE AND NOT REGION-RESTRICTED."
        )
        
        print(f"[YOUTUBE FALLBACK] Making API call to OpenRouter...")
        
        # First API call to get candidate videos using OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": request.host_url,  # Using the current application URL
                "X-Title": "Skillora Learning Platform",
            },
            json={
                "model": "google/gemini-2.5-pro-exp-03-25:free",  # Using Gemini through OpenRouter
                "messages": [
                    {
                        "role": "user",
                        "content": search_prompt
                    }
                ]
            }
        )
        
        # Process the response from OpenRouter
        if response.status_code != 200:
            print(f"[YOUTUBE FALLBACK] ERROR from OpenRouter API: {response.status_code}")
            print(f"[YOUTUBE FALLBACK] Response: {response.text}")
            return jsonify({'success': False, 'error': f'OpenRouter API error: {response.text}'}), 500
            
        response_data = response.json()
        response_text = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        print(f"[YOUTUBE FALLBACK] Received response from OpenRouter. Extracting YouTube URLs...")
        print(f"[YOUTUBE FALLBACK] Response text sample: {response_text[:100]}...")
        
        # Extract all potential YouTube URLs from the response with availability checking
        all_possible_urls = extract_valid_youtube_urls(response_text, max_urls=10, check_availability=True)
        print(f"[YOUTUBE FALLBACK] Extracted {len(all_possible_urls)} valid URLs: {all_possible_urls}")
        
        # If we don't have enough URLs, make a second more direct attempt
        if len(all_possible_urls) < 3:
            print("[YOUTUBE FALLBACK] Not enough valid URLs found. Making a second attempt...")
            # Make a more direct request focused just on getting URLs
            direct_prompt = (
                f"Find 5-8 popular educational YouTube videos about: '{search_query}'. "
                f"Return ONLY a list of YouTube video URLs, each on a new line. "
                f"Each URL must start with 'https://www.youtube.com/watch?v='. "
                f"IMPORTANT: Only include videos that are publicly available, not deleted, not private, and not region-restricted."
                f"Do not include YouTube Shorts, playlists, or channel URLs."
            )
            
            try:
                direct_response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": request.host_url,
                        "X-Title": "Skillora Learning Platform",
                    },
                    json={
                        "model": "google/gemini-2.5-pro-exp-03-25:free",
                        "messages": [
                            {
                                "role": "user",
                                "content": direct_prompt
                            }
                        ]
                    }
                )
                
                direct_response_data = direct_response.json()
                direct_response_text = direct_response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract URLs from this response and add them to our list
                additional_urls = extract_valid_youtube_urls(direct_response_text, max_urls=10-len(all_possible_urls), check_availability=True)
                all_possible_urls.extend(additional_urls)
                
                # Remove duplicates while preserving order
                seen = set()
                all_possible_urls = [url for url in all_possible_urls if not (url in seen or seen.add(url))]
            except Exception as e:
                print(f"[YOUTUBE FALLBACK] Error in direct URL request: {e}")
        
        # If we still don't have enough URLs, add some default educational videos as a last resort
        if len(all_possible_urls) < 2:
            print("[YOUTUBE FALLBACK] Still not enough valid URLs. Adding default educational videos...")
            # Add some general educational videos as a last resort
            default_videos = [
                "https://www.youtube.com/watch?v=rfscVS0vtbw",  # Python tutorial
                "https://www.youtube.com/watch?v=OK_JCtrrv-c",  # JavaScript tutorial
                "https://www.youtube.com/watch?v=ER8oKX5myE0",  # Java tutorial
                "https://www.youtube.com/watch?v=8jLOx1hD3_o",  # C++ tutorial
                "https://www.youtube.com/watch?v=ua-CiDNNj30",  # Web Development
                "https://www.youtube.com/watch?v=_uQrJ0TkZlc",  # Python for beginners
            ]
            
            # Add enough default videos to reach a minimum of 3
            for video in default_videos:
                if len(all_possible_urls) >= 3:
                    break
                if video not in all_possible_urls:
                    all_possible_urls.append(video)
        
        if not all_possible_urls:
            print("[YOUTUBE FALLBACK] Failed to find any valid YouTube URLs")
            return jsonify({'success': False, 'error': 'No valid YouTube videos found'}), 500
            
        # Save the URLs to the module
        module.youtube_links = json.dumps(all_possible_urls)
        db.session.commit()
        
        print(f"[YOUTUBE FALLBACK] Saved {len(all_possible_urls)} YouTube URLs to module")
        
        return jsonify({
            'success': True,
            'message': 'Found and saved YouTube videos for the module',
            'urls': all_possible_urls
        })
        
    except Exception as e:
        print(f"[YOUTUBE FALLBACK] Error finding YouTube videos: {str(e)}")
        print(f"[YOUTUBE FALLBACK] Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Error finding YouTube videos: {str(e)}'}), 500

def generate_module_quiz(module_id, topic):
    """Generate a quiz for a given module using OpenRouter API."""
    # Get the module
    module = Module.query.get_or_404(module_id)
    
    # Make sure the module is marked as a quiz type
    module.content_type = 'quiz'
    db.session.commit()
    
    # Check if quiz already exists
    existing_quiz = Quiz.query.filter_by(module_id=module_id).first()
    if existing_quiz:
        return  # Quiz already exists
    
    # Create a new quiz
    new_quiz = Quiz(
        title=f"Quiz on {topic}",
        description=f"Test your knowledge of {topic}",
        module_id=module_id,
        passing_score=70  # Set default passing score
    )
    db.session.add(new_quiz)
    db.session.flush()  # Get the ID without committing
    
    # Generate video script to base the quiz on
    try:
        course = Course.query.get(module.course_id)
        script_content = get_video_script(topic, course.title)
    except Exception:
        script_content = ""
    
    # Generate questions using OpenRouter API based on the video script
    try:
        api_key = os.getenv('OPENROUTER_API_KEY') or OPENROUTER_API_KEY
        if not api_key:
            print("OpenRouter API key not found, using default questions")
            create_default_questions(new_quiz.id, topic)
            db.session.commit()
            return True
        
        quiz_prompt = (
            f"Based on the following video script:\n\n{script_content}\n\n"
            "Generate 5 quiz questions that test understanding of its key concepts. "
            "Include 3 multiple-choice questions with 4 options (1 correct) and 2 fill-in-the-blank questions. "
            "Return a JSON array with this structure:\n"
            "[{\"type\": \"multiple_choice\", \"question\": \"Question text?\", \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"], \"correct_answer\": \"Option A\"},"
            "{\"type\": \"fill_in_blank\", \"question\": \"Question with _____ blank.\", \"correct_answer\": \"the correct word\"}]"
        )
        
        # Make API request to OpenRouter instead of using Gemini directly
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": request.host_url if hasattr(request, 'host_url') else "https://skillora.com",
                "X-Title": "Skillora Learning Platform",
            },
            json={
                "model": "google/gemini-2.5-pro-exp-03-25:free",  # Use Gemini through OpenRouter
                "messages": [
                    {
                        "role": "user",
                        "content": quiz_prompt
                    }
                ]
            },
            timeout=30  # Set a reasonable timeout
        )
        
        # Process OpenRouter response
        if response.status_code != 200:
            print(f"Error from OpenRouter API: {response.status_code}")
            print(f"Response: {response.text}")
            create_default_questions(new_quiz.id, topic)
            db.session.commit()
            return True
        
        response_data = response.json()
        questions_text = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\[\s*{.*}\s*\]', questions_text, re.DOTALL)
        if json_match:
            questions_json = json_match.group(0)
            questions = json.loads(questions_json)
            
            # Create question objects
            for i, q in enumerate(questions):
                new_question = QuizQuestion(
                    quiz_id=new_quiz.id,
                    question_text=q["question"],
                    question_type=q["type"],
                    options=json.dumps(q.get("options", [])),
                    correct_answer=q["correct_answer"],
                    order=i+1,
                    points=20  # Each question is worth 20 points for a total of 100
                )
                db.session.add(new_question)
            
            db.session.commit()
            return True
        else:
            # If no JSON found, create some default questions
            create_default_questions(new_quiz.id, topic)
            db.session.commit()
            return True
    except Exception as e:
        print(f"Error generating quiz with OpenRouter: {e}")
        print((traceback.format_exc()))
        # Create default questions on error
        create_default_questions(new_quiz.id, topic)
        db.session.commit()
        return True

def create_default_questions(quiz_id, topic):
    """Create default questions for a quiz if AI generation fails."""
    # Create 3 multiple choice questions
    for i in range(3):
        question = QuizQuestion(
            quiz_id=quiz_id,
            question_text=f"Sample multiple choice question {i+1} about {topic}?",
            question_type="multiple_choice",
            options=json.dumps([f"Option A for question {i+1}", f"Option B for question {i+1}", 
                                f"Option C for question {i+1}", f"Option D for question {i+1}"]),
            correct_answer=f"Option A for question {i+1}",
            order=i+1,
            points=20
        )
        db.session.add(question)
    
    # Create 2 fill in the blank questions
    for i in range(2):
        question = QuizQuestion(
            quiz_id=quiz_id,
            question_text=f"Sample fill in the blank question {i+1} about {topic}. Fill in the _____.",
            question_type="fill_in_blank",
            options=json.dumps([]),
            correct_answer="answer",
            order=i+4,
            points=20
        )
        db.session.add(question)

# Add a route to get quiz questions
@views.route('/get_quiz/<int:quiz_id>', methods=['GET'])
@login_required
def get_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if the quiz belongs to a module that belongs to a course of the current user
    module = Module.query.get_or_404(quiz.module_id)
    course = Course.query.get_or_404(module.course_id)
    if course.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Get quiz questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).order_by(QuizQuestion.order).all()
    
    # Format questions for JSON response
    questions_json = []
    for q in questions:
        questions_json.append({
            'id': q.id,
            'quiz_id': q.quiz_id,
            'question_text': q.question_text,
            'question_type': q.question_type,
            'options': q.options,  # Already JSON string
            'order': q.order
        })
    
    # Return quiz and questions
    return jsonify({
        'success': True,
        'quiz': {
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'passing_score': quiz.passing_score
        },
        'questions': questions_json
    })

# Add a route to submit quiz answers
@views.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    data = request.json
    quiz_id = data.get('quiz_id')
    answers = data.get('answers')
    
    if not quiz_id or not answers:
        return jsonify({'success': False, 'error': 'Missing quiz_id or answers'}), 400
    
    # Get the quiz
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
    
    # Calculate score
    total_points = 0
    earned_points = 0
    
    for q in questions:
        total_points += q.points
        user_answer = answers.get(str(q.id))
        
        if user_answer:
            # For multiple choice, exact match
            if q.question_type == 'multiple_choice' and user_answer == q.correct_answer:
                earned_points += q.points
            # For fill in blank, case-insensitive contains
            elif q.question_type == 'fill_in_blank' and q.correct_answer.lower() in user_answer.lower():
                earned_points += q.points
    
    # Calculate percentage
    score_percentage = int((earned_points / total_points) * 100) if total_points > 0 else 0
    passed = score_percentage >= quiz.passing_score
    
    # Record the quiz attempt
    quiz_attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score_percentage,
        answers=json.dumps(answers),
        is_passed=passed
    )
    db.session.add(quiz_attempt)
    
    # If passed, mark the module as completed
    if passed:
        module = Module.query.get(quiz.module_id)
        progress = UserProgress.query.filter_by(user_id=current_user.id, module_id=module.id).first()
        
        if not progress:
            progress = UserProgress(user_id=current_user.id, module_id=module.id)
            db.session.add(progress)
        
        progress.is_completed = True
        progress.completion_date = func.now()
        
    db.session.commit()
    
    return jsonify({
        'success': True,
        'score': score_percentage,
        'passed': passed,
        'passing_score': quiz.passing_score
    })

# Add a route for bookmark functionality
@views.route('/update_bookmark', methods=['POST'])
@login_required
def update_bookmark():
    data = request.json
    course_id = data.get('course_id')
    is_bookmarked = data.get('is_bookmarked', False)
    
    if not course_id:
        return jsonify({'success': False, 'error': 'Missing course_id'}), 400
    
    # Update course bookmark status
    course = Course.query.get_or_404(course_id)
    
    # Check if course belongs to current user
    if course.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    course.is_bookmarked = is_bookmarked
    db.session.commit()
    
    return jsonify({'success': True})

@views.route('/learning-interface/<int:course_id>/<int:module_id>')
@login_required
def learning_interface(course_id, module_id):
    # Get the course
    course = Course.query.get_or_404(course_id)
    
    # Check if the course belongs to the user
    if course.user_id != current_user.id:
        flash('You do not have access to this course.', 'danger')
        return redirect(url_for('views.my_courses'))
    
    # Get the current module
    current_module = Module.query.get_or_404(module_id)
    
    # Check if the module belongs to the course
    if current_module.course_id != course_id:
        flash('Invalid module for this course.', 'danger')
        return redirect(url_for('views.my_courses'))
    
    # Auto-load content if this is a video module without content
    if current_module.content_type == 'video' and not current_module.get_youtube_links():
        try:
            # Call the content generation function directly
            generate_module_content(current_module.id)
            # Refresh the module from the database to get the updated content
            current_module = Module.query.get_or_404(module_id)
        except Exception as e:
            flash(f'Error automatically loading content: {str(e)}', 'warning')
    
    # Auto-generate quiz content if this is a quiz module without existing quiz
    if current_module.content_type == 'quiz' and not current_module.quiz:
        try:
            # Generate the quiz based on the video script
            generate_module_quiz(current_module.id, current_module.title)
            # Refresh the module to include the new quiz
            current_module = Module.query.get_or_404(module_id)
        except Exception as e:
            flash(f'Error generating quiz: {str(e)}', 'warning')
    
    # Get all modules for this course, ordered by their order field
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()
    
    # Get the user's progress for all modules in this course
    user_progress = {}
    progress_records = UserProgress.query.filter_by(user_id=current_user.id).all()
    
    for progress in progress_records:
        user_progress[progress.module_id] = progress
    
    # Calculate overall course progress
    total_modules = len(modules)
    completed_modules = sum(1 for module in modules if module.id in user_progress and user_progress[module.id].is_completed)
    progress_percentage = round((completed_modules / total_modules) * 100) if total_modules > 0 else 0
    
    # If the user is viewing this course for the first time, redirect to the first video module
    if module_id == modules[0].id and 'content_type' in dir(modules[0]) and modules[0].content_type == 'quiz':
        # Find the first video module
        for module in modules:
            if 'content_type' in dir(module) and module.content_type == 'video':
                return redirect(url_for('views.learning_interface', course_id=course_id, module_id=module.id))
    
    return render_template(
        'learning_interface.html',
        user=current_user,
        course=course,
        current_module=current_module,
        modules=modules,
        user_progress=user_progress,
        progress_percentage=progress_percentage
    )

@views.route('/api/course/<int:course_id>/modules', methods=['GET'])
@login_required
def get_course_modules(course_id):
    # Get the course
    course = Course.query.get_or_404(course_id)
    
    # Check if the course belongs to the user
    if course.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
    
    # Get all modules for this course, ordered by their order field
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()
    
    # Format modules for JSON response
    modules_json = []
    for module in modules:
        modules_json.append({
            'id': module.id,
            'title': module.title,
            'description': module.description,
            'content_type': module.content_type,
            'order': module.order,
            'estimated_time_minutes': module.estimated_time_minutes,
            'has_quiz': module.quiz is not None
        })
    
    return jsonify({
        'success': True,
        'modules': modules_json
    })

# Modify the course generation process to always start with video modules
def initialize_course_modules(course, chapters):
    """Initialize course modules with an alternating pattern of video, quiz, video, quiz..."""
    
    for i, chapter in enumerate(chapters[:5]):  # Limit to 5 main chapters
        # First create a video module
        video_module = Module(
            title=chapter,
            description=f"Learn about {chapter}",
            course_id=course.id,
            order=i*2+1,  # Use odd numbers for videos: 1, 3, 5, 7, 9
            youtube_links="[]",  # Empty list for now, will be populated async
            content_type="video"  # Explicitly set content type
        )
        db.session.add(video_module)
        
        # Then create a quiz module for this chapter
        quiz_module = Module(
            title=f"Quiz: {chapter}",
            description=f"Test your knowledge of {chapter}",
            course_id=course.id,
            order=i*2+2,  # Use even numbers for quizzes: 2, 4, 6, 8, 10
            content_type="quiz"  # Explicitly set as quiz type
        )
        db.session.add(quiz_module)
        
        # Create a quiz for this module
        new_quiz = Quiz(
            title=f"Quiz on {chapter}",
            description=f"Test your knowledge about {chapter}",
            module_id=0  # This will be set after module is created
        )
        db.session.add(new_quiz)
    
    db.session.commit()
    
    # After commit, link quizzes with quiz modules
    video_modules = Module.query.filter_by(course_id=course.id, content_type="video").order_by(Module.order).all()
    quiz_modules = Module.query.filter_by(course_id=course.id, content_type="quiz").order_by(Module.order).all()
    quizzes = Quiz.query.filter_by(module_id=0).all()
    
    # Link quizzes to quiz modules
    for i, quiz_module in enumerate(quiz_modules):
        if i < len(quizzes):
            quizzes[i].module_id = quiz_module.id
            
            # Generate questions for this quiz using the video module's title
            if i < len(video_modules):
                try:
                    generate_module_quiz(quiz_module.id, video_modules[i].title)
                except Exception as e:
                    print(f"Error generating quiz questions: {e}")
    
    db.session.commit()
    return True

@views.route('/settings/learning-preferences', methods=['GET', 'POST'])
@login_required
def learning_preferences():
    """View and update learning preferences"""
    
    # Get the user's current settings
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    
    # If settings don't exist, create them
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()
    
    # Get the learning style preferences
    learning_preferences = CSInterest.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        # Update preferred video duration
        preferred_duration = request.form.get('preferred_video_duration')
        if preferred_duration and preferred_duration.isdigit():
            user_settings.preferred_video_duration = int(preferred_duration)
        
        # Update learning style if changed
        learning_style = request.form.get('learning_style')
        if learning_style and learning_preferences:
            learning_preferences.learning_style = learning_style
        
        # Update other settings
        daily_goal = request.form.get('daily_goal_minutes')
        if daily_goal and daily_goal.isdigit():
            user_settings.daily_goal_minutes = int(daily_goal)
            
        theme = request.form.get('theme')
        if theme in ['light', 'dark']:
            user_settings.theme = theme
            
        language = request.form.get('language')
        if language:
            user_settings.language = language
            
        notifications = request.form.get('notifications') == 'on'
        user_settings.notification_enabled = notifications
        
        # Save changes
        db.session.commit()
        
        flash('Learning preferences updated successfully', 'success')
        return redirect(url_for('views.learning_preferences'))
    
    # For GET request
    return render_template(
        'learning_preferences.html', 
        user_settings=user_settings,
        learning_style=learning_preferences.learning_style if learning_preferences else 'visual'
    )

@views.route('/api/chat/upload-image', methods=['POST'])
@login_required
def upload_chat_image():
    """API endpoint for uploading images for chat"""
    try:
        # Check if a file was uploaded
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
            
        file = request.files['image']
        
        # Check if the file has a filename
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
            
        # Check if the file is allowed
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Allowed types: png, jpg, jpeg, gif, webp'}), 400
            
        # Make the filename unique by adding timestamp and user ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(f"user_{current_user.id}_{timestamp}_{file.filename}")
        
        # Create user-specific directory
        user_upload_dir = os.path.join(UPLOAD_FOLDER, f"user_{current_user.id}")
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(user_upload_dir, filename)
        file.save(file_path)
        
        # Generate a URL for the uploaded image
        image_url = url_for('static', filename=f'uploads/chat_images/user_{current_user.id}/{filename}')
        
        # Get optional caption
        caption = request.form.get('caption', '')
        
        # If we have a caption, save the message and image reference in the DB
        if caption:
            # Save user message with image reference
            try:
                content = f"{caption}\n\n[IMAGE: {image_url}]"
                ChatMessage.add_message(user_id=current_user.id, role="user", content=content)
                print("DEBUG: User message with image saved to DB.")
            except Exception as db_error:
                print(f"ERROR saving chat message with image: {str(db_error)}\n{traceback.format_exc()}")
                # Don't fail the whole request, but log it
        
        # Return the URL of the saved image
        return jsonify({
            'success': True, 
            'imageUrl': image_url,
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"ERROR in upload_chat_image: {str(e)}\n{error_traceback}")
        return jsonify({'success': False, 'message': f'Error uploading image: {str(e)}'}), 500

@views.route('/generate-courses')
@login_required
def generate_courses():
    """Show the loading page while courses are being generated"""
    # Ensure the user has completed the survey
    if not current_user.is_survey_completed:
        flash('Please complete the CS interest survey first.', category='warning')
        return redirect(url_for('views.cs_interest_survey'))
    
    # Check if we have generation info in the session
    if 'course_generation' not in session:
        # Create default generation info if not in session
        session['course_generation'] = {
            'status': 'pending',
            'percent': 0,
            'step': 1,
            'message': 'Starting course generation process...',
            'career_path': 'Software Engineer',  # Default
            'learning_style': 'visual',          # Default
            'time_availability': 'medium'        # Default
        }
    
    # Start the background task for course generation if it's not already running
    if session['course_generation']['status'] == 'pending':
        # Begin the course generation process in the background
        # This would typically be done with a task queue like Celery
        # For now, we'll simulate it in a background thread
        import threading
        thread = threading.Thread(
            target=generate_courses_background,
            args=(
                current_user.id,
                session['course_generation']['career_path'],
                session['course_generation']['learning_style'],
                session['course_generation']['time_availability']
            )
        )
        thread.daemon = True
        thread.start()
        
        # Update status to in-progress
        session['course_generation']['status'] = 'in-progress'
        session.modified = True
    
    # Show loading template
    return render_template('loading_courses.html', user=current_user)

@views.route('/api/course-generation/status')
@login_required
def course_generation_status():
    """Get the status of course generation process"""
    user_id = current_user.id
    
    # Get the status from Redis or a file
    status_data = get_generation_status(user_id)
    
    if not status_data:
        # No status found, the process might not have started
        return jsonify({
            "percent": 0,
            "message": "Waiting to start course generation...",
            "step": 1,
            "completed": False
        })
    
    # Try to get Manim video generation progress if available
    try:
        from .manim import get_manim_generation_progress
        manim_progress = get_manim_generation_progress()
        
        # If we're in the video generation step (step 3), enhance the status with Manim details
        if status_data.get("step") == 3 and manim_progress["status"] != "idle":
            # Calculate a more detailed percentage for step 3
            # The course generation is step 3 of 4, so it covers 25% to 75% of the overall process
            if manim_progress["total_videos"] > 0:
                manim_percent = (manim_progress["completed_videos"] / manim_progress["total_videos"]) * 50
                # Step 3 covers 25% to 75% of the overall process
                overall_percent = 25 + manim_percent
                
                # Enhance the status message with Manim details
                if manim_progress["current_video"]:
                    message = f"Generating video for '{manim_progress['current_video']}' ({manim_progress['completed_videos']}/{manim_progress['total_videos']})"
                else:
                    message = status_data.get("message", "Generating course videos...")
                
                # Update the status data
                status_data["percent"] = min(overall_percent, 75)  # Cap at 75% (end of step 3)
                status_data["message"] = message
                status_data["manim_progress"] = {
                    "status": manim_progress["status"],
                    "completed": manim_progress["completed_videos"],
                    "total": manim_progress["total_videos"],
                    "current": manim_progress["current_video"],
                    "details": manim_progress["details"][-3:] if manim_progress["details"] else []
                }
    except (ImportError, AttributeError, KeyError) as e:
        # If we can't get Manim progress, just continue with the regular status
        print(f"Could not get Manim progress: {e}")
        pass
    
    # Return the status
    return jsonify({
        "percent": status_data.get("percent", 0),
        "message": status_data.get("message", "Generating courses..."),
        "step": status_data.get("step", 1),
        "completed": status_data.get("status") == "completed",
        "manim_progress": status_data.get("manim_progress", {})
    })

def generate_courses_background(user_id, career_path, learning_style, time_availability):
    """Generate courses with Manim videos in the background"""
    # Import flask app at the function level to avoid circular imports
    from . import create_app
    app = create_app()
    
    # Create an application context for this background thread
    with app.app_context():
        try:
            print(f"\n[COURSE GENERATION] Starting for user {user_id}")
            print(f"[COURSE GENERATION] Career Path: {career_path}")
            print(f"[COURSE GENERATION] Learning Style: {learning_style}")
            print(f"[COURSE GENERATION] Time Availability: {time_availability}")
            
            # Get the user and their learning path
            from .models import User, LearningPath
            user = User.query.get(user_id)
            if not user:
                print(f"[COURSE GENERATION] ERROR: User {user_id} not found!")
                return
                
            learning_path = LearningPath.query.filter_by(user_id=user_id).first()
            if not learning_path:
                print(f"[COURSE GENERATION] ERROR: Learning path for user {user_id} not found!")
                return
            
            # Update session with progress (step 1)
            update_generation_status(
                user_id, 
                percent=10, 
                step=1, 
                message=f"Analyzing your {career_path} learning profile..."
            )
            
            print(f"[COURSE GENERATION] Step 1: Analyzing learning profile (10%)")
            
            # Sleep to simulate work (would be actual processing in production)
            import time
            time.sleep(2)
            
            # Define course topics based on career path
            print(f"[COURSE GENERATION] Getting course topics for {career_path}")
            course_topics = get_course_topics_for_career(career_path)
            print(f"[COURSE GENERATION] Found {len(course_topics)} course topics")
            
            # Update session with progress (step 2)
            update_generation_status(
                user_id, 
                percent=30, 
                step=2, 
                message=f"Designing your {career_path} course structure..."
            )
            print(f"[COURSE GENERATION] Step 2: Designing course structure (30%)")
            time.sleep(2)
            
            # Create course objects in the database
            print(f"[COURSE GENERATION] Creating course objects in database")
            courses = create_courses_for_user(user_id, career_path, course_topics)
            print(f"[COURSE GENERATION] Created {len(courses)} courses")
            
            # Update session with progress (step 3)
            update_generation_status(
                user_id, 
                percent=50, 
                step=3, 
                message="Generating educational videos with Manim..."
            )
            print(f"[COURSE GENERATION] Step 3: Generating educational videos (50%)")
            
            # Generate Manim videos for each course
            for i, course in enumerate(courses):
                # Update progress percentage based on course index
                course_progress = 50 + int((i / len(courses)) * 40)
                update_generation_status(
                    user_id,
                    percent=course_progress,
                    step=3,
                    message=f"Creating videos for {course.title}..."
                )
                
                print(f"[COURSE GENERATION] Creating modules for course: {course.title} ({course_progress}%)")
                # Create modules with Manim videos
                create_modules_with_manim(course, learning_style, time_availability)
                print(f"[COURSE GENERATION] Completed modules for course: {course.title}")
                time.sleep(3)  # Simulate video generation time
            
            # Update session with progress (step 4)
            update_generation_status(
                user_id, 
                percent=95, 
                step=4, 
                message="Finalizing your learning path..."
            )
            print(f"[COURSE GENERATION] Step 4: Finalizing learning path (95%)")
            time.sleep(2)
            
            # Mark generation as complete
            update_generation_status(
                user_id, 
                percent=100, 
                step=4, 
                message="Your personalized courses are ready!",
                status="completed"
            )
            print(f"[COURSE GENERATION] Completed successfully for user {user_id} (100%)")
        
        except Exception as e:
            import traceback
            print(f"[COURSE GENERATION] ERROR: {str(e)}")
            print(f"[COURSE GENERATION] TRACEBACK: {traceback.format_exc()}")
            
            # Update status to error
            update_generation_status(
                user_id,
                percent=0,
                step=1,
                message=f"Error generating courses: {str(e)}",
                status="error"
            )

def update_generation_status(user_id, percent, step, message, status="in-progress"):
    """Update the generation status in the session for the given user"""
    # In a real application, you would use a proper task queue and database
    # For this example, we're using a simpler approach with file storage
    
    # Since we can't directly access the user's session from a background thread,
    # we'll store the status in a global variable or file that can be checked by the API endpoint
    
    try:
        # Create a status file for this user
        status_data = {
            'status': status,
            'percent': percent,
            'step': step,
            'message': message,
            'completed': status == "completed",
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in a global dict - in production, this would be a database or Redis
        if not hasattr(update_generation_status, 'status_store'):
            update_generation_status.status_store = {}
        
        update_generation_status.status_store[user_id] = status_data
        
        print(f"[STATUS UPDATE] User: {user_id} | Status: {status} | Progress: {percent}% | Step: {step} | Message: {message}")
    except Exception as e:
        import traceback
        print(f"[STATUS UPDATE] ERROR updating generation status: {str(e)}")
        print(f"[STATUS UPDATE] TRACEBACK: {traceback.format_exc()}")

def get_course_topics_for_career(career_path):
    """Get relevant course topics based on career path"""
    if career_path == "Software Engineer":
        return [
            {
                "title": "Programming Fundamentals",
                "description": "Master the core concepts of programming languages, data structures, and algorithms.",
                "level": "Beginner"
            },
            {
                "title": "Software Design & Architecture",
                "description": "Learn design patterns, software architecture, and best practices for maintainable code.",
                "level": "Intermediate"
            },
            {
                "title": "Backend Development",
                "description": "Build robust server-side applications with databases, APIs, and cloud services.",
                "level": "Intermediate"
            },
            {
                "title": "Software Testing & DevOps",
                "description": "Master testing methodologies, CI/CD, and DevOps practices for reliable software delivery.",
                "level": "Advanced"
            }
        ]
    elif career_path == "Data Scientist":
        return [
            {
                "title": "Data Analysis Fundamentals",
                "description": "Learn the basics of data analysis, statistics, and exploratory data analysis.",
                "level": "Beginner"
            },
            {
                "title": "Machine Learning Fundamentals",
                "description": "Master core machine learning algorithms, evaluation methods, and implementation.",
                "level": "Intermediate"
            },
            {
                "title": "Advanced Data Science",
                "description": "Explore deep learning, natural language processing, and computer vision.",
                "level": "Advanced"
            }
        ]
    elif career_path == "Web Developer":
        return [
            {
                "title": "Frontend Fundamentals",
                "description": "Master HTML, CSS, and JavaScript to create engaging user interfaces.",
                "level": "Beginner"
            },
            {
                "title": "Frontend Frameworks",
                "description": "Build dynamic web applications using modern frameworks and tools.",
                "level": "Intermediate"
            },
            {
                "title": "Backend Development",
                "description": "Create server-side applications with databases and RESTful APIs.",
                "level": "Intermediate"
            }
        ]
    elif career_path == "Mobile Developer":
        return [
            {
                "title": "Mobile Development Fundamentals",
                "description": "Learn the basics of mobile app development and user interface design.",
                "level": "Beginner"
            },
            {
                "title": "Native App Development",
                "description": "Build native applications for iOS and Android platforms.",
                "level": "Intermediate"
            },
            {
                "title": "Cross-Platform Development",
                "description": "Create applications that run on multiple platforms with a single codebase.",
                "level": "Advanced"
            }
        ]
    elif career_path == "Cybersecurity Specialist":
        return [
            {
                "title": "Security Fundamentals",
                "description": "Learn the core concepts of cybersecurity and threat landscapes.",
                "level": "Beginner"
            },
            {
                "title": "Network & Application Security",
                "description": "Master techniques to secure networks and applications from attacks.",
                "level": "Intermediate"
            },
            {
                "title": "Defensive Security",
                "description": "Learn to detect, respond to, and recover from security incidents.",
                "level": "Advanced"
            }
        ]
    elif career_path == "AI Engineer":
        return [
            {
                "title": "AI Fundamentals",
                "description": "Learn the foundations of artificial intelligence and machine learning.",
                "level": "Beginner"
            },
            {
                "title": "Deep Learning",
                "description": "Master deep learning architectures and techniques for complex AI tasks.",
                "level": "Intermediate"
            },
            {
                "title": "Natural Language Processing",
                "description": "Build AI systems that understand, interpret, and generate human language.",
                "level": "Advanced"
            }
        ]
    elif career_path == "Game Developer":
        return [
            {
                "title": "Game Development Fundamentals",
                "description": "Learn the core concepts of game development and design.",
                "level": "Beginner"
            },
            {
                "title": "3D Game Development",
                "description": "Create immersive 3D games with advanced game engines.",
                "level": "Intermediate"
            },
            {
                "title": "Game Programming",
                "description": "Master programming techniques specific to game development.",
                "level": "Advanced"
            }
        ]
    elif career_path == "Systems Engineer":
        return [
            {
                "title": "Operating Systems Fundamentals",
                "description": "Master the core concepts of operating systems and system programming.",
                "level": "Beginner"
            },
            {
                "title": "Distributed Systems",
                "description": "Design and implement distributed computing systems and architectures.",
                "level": "Intermediate"
            },
            {
                "title": "Infrastructure & Networking",
                "description": "Build and manage complex network infrastructure and systems.",
                "level": "Advanced"
            }
        ]
    else:
        # Default set of courses
        return [
            {
                "title": "Programming Fundamentals",
                "description": "Learn core programming concepts and principles.",
                "level": "Beginner"
            },
            {
                "title": "Software Development",
                "description": "Build software applications with modern technologies.",
                "level": "Intermediate"
            },
            {
                "title": "Advanced Computing",
                "description": "Explore advanced computing topics and specializations.",
                "level": "Advanced"
            }
        ]

def create_courses_for_user(user_id, career_path, course_topics):
    """Create course objects in the database for the user"""
    created_courses = []
    
    for i, topic in enumerate(course_topics):
        # Create a new course
        new_course = Course(
            title=topic["title"],
            description=topic["description"],
            category_name=career_path,
            level=topic["level"],
            user_id=user_id,
            order=i+1
        )
        db.session.add(new_course)
        
        # Store in our return list
        created_courses.append(new_course)
    
    # Commit to database to get course IDs
    db.session.commit()
    print(f"Created {len(created_courses)} courses for user {user_id}")
    
    return created_courses

def create_modules_with_manim(course, learning_style, time_availability):
    """Create course modules with Manim visualization videos"""
    print(f"\n[MANIM GENERATION] Starting for course: {course.title}")
    print(f"[MANIM GENERATION] Learning style: {learning_style}")
    print(f"[MANIM GENERATION] Time availability: {time_availability}")
    
    # Define chapter topics based on the course title
    chapters = get_chapter_topics_for_course(course.title)
    print(f"[MANIM GENERATION] Generated {len(chapters)} chapter topics")
    
    # Initialize modules with the chapter topics
    initialize_course_modules(course, chapters)
    print(f"[MANIM GENERATION] Initialized course modules structure")
    
    # Get all video modules for this course
    video_modules = Module.query.filter_by(course_id=course.id, content_type="video").order_by(Module.order).all()
    print(f"[MANIM GENERATION] Found {len(video_modules)} video modules to generate")
    
    # Import our Manim utilities
    try:
        from .manim import (
            generate_and_save_manim_video, 
            reset_manim_progress, 
            update_manim_progress, 
            get_manim_generation_progress
        )
        using_real_manim = True
        print(f"[MANIM GENERATION] Successfully imported manim module")
        
        # Initialize the progress tracking
        reset_manim_progress(total_videos=len(video_modules))
        update_manim_progress("initializing", f"Starting Manim video generation for course: {course.title}")
    except ImportError as e:
        using_real_manim = False
        print(f"[MANIM GENERATION] Could not import manim: {e}")
        print(f"[MANIM GENERATION] Will fall back to YouTube links")
    
    # For each video module, generate a Manim script and render it
    for i, module in enumerate(video_modules):
        try:
            print(f"[MANIM GENERATION] Processing module {i+1} of {len(video_modules)}: {module.title}")
            
            if using_real_manim:
                # Update the progress tracking
                update_manim_progress(
                    "processing", 
                    f"Processing module {i+1}/{len(video_modules)}: {module.title}",
                    video_title=module.title
                )
                
                # Generate educational content about the module topic
                module_description = f"An educational overview of {module.title}, covering key concepts and applications."
                
                # Define the output path for the video
                videos_folder = os.path.join("Backend", "website", "static", "uploads", "manim_videos")
                os.makedirs(videos_folder, exist_ok=True)
                
                # Create a safe filename
                safe_title = ''.join(c if c.isalnum() else '_' for c in module.title)
                unique_id = str(uuid.uuid4())[:8]
                video_filename = f"{safe_title}_{unique_id}.mp4"
                video_path = os.path.join(videos_folder, video_filename)
                
                print(f"[MANIM GENERATION] Generating Manim video for module ID {module.id}: '{module.title}'")
                print(f"[MANIM GENERATION] Output path: {video_path}")
                
                # Generate the Manim video
                output_path = generate_and_save_manim_video(
                    topic=module.title,
                    content=module_description,
                    learning_style=learning_style,
                    output_path=video_path
                )
                
                if output_path:
                    print(f"[MANIM GENERATION] Successfully generated Manim video at: {output_path}")
                    
                    # Store the video path in the module
                    module.manim_video_path = output_path
                    db.session.commit()
                else:
                    update_manim_progress(
                        "fallback", 
                        f"Failed to generate Manim video for module {module.id}, falling back to YouTube"
                    )
                    print(f"[MANIM GENERATION] Failed to generate Manim video for module {module.id}")
                    # Fall back to YouTube links
                    print(f"[MANIM GENERATION] Falling back to YouTube links via generate_module_content")
                    generate_module_content(module.id)
            else:
                # Fall back to using the existing generate_module_content function
                print(f"[MANIM GENERATION] Using fallback YouTube links via generate_module_content")
                generate_module_content(module.id)
            
        except Exception as e:
            print(f"[MANIM GENERATION] Error generating content for module {module.title}: {str(e)}")
            print(f"[MANIM GENERATION] Traceback: {traceback.format_exc()}")
            
            if using_real_manim:
                update_manim_progress(
                    "error",
                    f"Error generating content for module {module.title}: {str(e)}"
                )
            
            # Try to fall back to YouTube links
            try:
                print(f"[MANIM GENERATION] Attempting YouTube fallback for module {module.id}")
                generate_module_content(module.id)
            except Exception as inner_e:
                print(f"[MANIM GENERATION] Even YouTube fallback failed: {str(inner_e)}")
                continue  # Continue with the next module
    
    if using_real_manim:
        update_manim_progress(
            "completed", 
            f"Completed content generation for course: {course.title}"
        )
    
    print(f"[MANIM GENERATION] Completed content generation for course: {course.title}")
    
    # Commit any remaining changes
    db.session.commit()

def get_chapter_topics_for_course(course_title):
    """Get relevant chapter topics based on course title"""
    # This could be expanded to use OpenRouter API for more dynamic content
    # Here's a simplified version with predefined topics
    
    if "Programming Fundamentals" in course_title:
        return [
            "Introduction to Programming Concepts",
            "Variables and Data Types",
            "Control Structures and Loops",
            "Functions and Modularity",
            "Data Structures Basics"
        ]
    elif "Software Design" in course_title:
        return [
            "Object-Oriented Programming Principles",
            "Design Patterns Introduction",
            "SOLID Principles",
            "Software Architecture Styles",
            "Clean Code Practices"
        ]
    elif "Data Analysis" in course_title:
        return [
            "Introduction to Data Science",
            "Statistical Analysis Fundamentals",
            "Data Cleaning and Preparation",
            "Exploratory Data Analysis",
            "Data Visualization Techniques"
        ]
    elif "Machine Learning" in course_title:
        return [
            "ML Fundamentals",
            "Supervised Learning Algorithms",
            "Unsupervised Learning Techniques",
            "Model Evaluation and Validation",
            "Feature Engineering"
        ]
    elif "Frontend" in course_title:
        return [
            "HTML and CSS Fundamentals",
            "JavaScript Basics",
            "DOM Manipulation",
            "Responsive Design Principles",
            "Frontend Build Tools"
        ]
    elif "Backend" in course_title:
        return [
            "Server-Side Programming",
            "RESTful API Design",
            "Database Integration",
            "Authentication and Authorization",
            "Performance Optimization"
        ]
    else:
        # Default chapters for any course
        return [
            f"Introduction to {course_title}",
            f"Core Concepts in {course_title}",
            f"Advanced Topics in {course_title}",
            f"Practical Applications of {course_title}",
            f"{course_title} in the Real World"
        ]

def generate_manim_script(topic, learning_style, time_availability):
    """Generate a Manim script based on the topic, learning style, and time availability"""
    # Adjust complexity based on time availability
    if time_availability == "low":
        complexity = "basic"
        duration = "3-5 minutes"
    elif time_availability == "medium":
        complexity = "moderate"
        duration = "8-12 minutes"
    else:
        complexity = "detailed"
        duration = "15-20 minutes"
    
    # Adjust visualization style based on learning style
    if learning_style == "visual":
        visualization_focus = "Use vibrant colors, clear animations, and visual metaphors. Minimize text and emphasize graphics."
    elif learning_style == "auditory":
        visualization_focus = "Include step-by-step narration points, use animations that sync with verbal explanations."
    elif learning_style == "hands-on":
        visualization_focus = "Show practical examples, code demonstrations, and interactive scenarios."
    else:
        visualization_focus = "Balance visual elements with explanatory text. Use a mix of animations and static content."
    
    # Create a simple Manim script template
    # In a real implementation, this would be much more sophisticated
    # Ideally using OpenRouter API to generate the script
    script = f"""
from manim import *

class {topic.replace(" ", "")}Scene(Scene):
    def construct(self):
        # Title
        title = Text("{topic}", font_size=40)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Introduction
        intro_text = Text("This {complexity} video covers {topic}", font_size=24)
        self.play(Write(intro_text))
        self.wait(2)
        self.play(FadeOut(intro_text))
        
        # Main content would be generated here based on:
        # - Topic: {topic}
        # - Learning style: {learning_style} 
        # - Visualization focus: {visualization_focus}
        # - Approximate duration: {duration}
        
        # Conclusion
        conclusion = Text("Summary of key points", font_size=28)
        self.play(Write(conclusion))
        self.wait(2)
        
        # Final title
        final_title = Text("Thanks for watching!", font_size=36)
        self.play(ReplacementTransform(conclusion, final_title))
        self.wait(2)
    """ 
    
    return script