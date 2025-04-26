from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from . import db
from .models import Course, UserProgress, Achievement, LearningPath, Module, Quiz, QuizAttempt, CSInterestSurvey, user_course, learning_path_course, Note, User
from datetime import datetime, timedelta
import json
import random
import traceback
import requests
from . import config  # Import the config module
import asyncio

views = Blueprint('views', __name__)

@views.route('/')
def index():
    # If user is already logged in, redirect them appropriately
    if current_user.is_authenticated:
        # If they haven't completed the survey, redirect to survey
        if not current_user.is_survey_completed:
            return redirect(url_for('views.cs_interest_survey'))
        # Otherwise send them to the dashboard
        return redirect(url_for('views.dashboard'))
        
    # Not logged in, show the landing page
    return render_template('index.html')

@views.route('/dashboard')
@login_required
def dashboard():
    # Get user's courses
    enrolled_courses = []
    completed_courses = []
    in_progress_courses = []
    
    # Sample weekly streak data (Mon-Sun)
    weekly_streak = [
        {"label": "M", "status": "completed"},
        {"label": "T", "status": "completed"},
        {"label": "W", "status": "completed"},
        {"label": "T", "status": "today"},
        {"label": "F", "status": None},
        {"label": "S", "status": None},
        {"label": "S", "status": None}
    ]
    
    # Sample achievement data
    achievements = [
        {"title": "Fast Learner", "description": "Completed 3 courses in a week", "icon": "fas fa-bolt"},
        {"title": "Quiz Master", "description": "Scored 100% on 5 quizzes", "icon": "fas fa-crown"},
        {"title": "Dedication", "description": "Maintained a 7-day streak", "icon": "fas fa-fire"}
    ]
    
    # Sample recent activities
    recent_activities = [
        {"description": "Completed 'Introduction to Python' module", "time_ago": "2 hours ago", "type": "course_progress"},
        {"description": "Earned 'Fast Learner' achievement", "time_ago": "Yesterday", "type": "achievement"},
        {"description": "Scored 90% on 'Data Types Quiz'", "time_ago": "2 days ago", "type": "quiz"}
    ]
    
    # Sample learning path data (same as in learning_path route)
    path_details = {
        "title": "Web Development Path",
        "icon": "fa-code",
        "duration": "6 months",
        "courses": 12,
        "modules": 3,
        "description": "Master web development from fundamentals to advanced frameworks."
    }
    
    # Sample modules
    modules = [
        {
            "title": "Programming Fundamentals",
            "status": "completed",
            "progress": 100,
            "no_of_courses": 4,
            "duration": "4 weeks",
            "description": "Learn the fundamentals of programming with HTML, CSS and JavaScript.",
            "courses": ["HTML Fundamentals", "CSS Basics", "JavaScript Essentials", "Responsive Design"],
            "projects": ["Personal Portfolio"]
        },
        {
            "title": "Frameworks & Advanced Development",
            "status": "current",
            "progress": 45,
            "no_of_courses": 5,
            "no_of_projects": 2,
            "duration": "8 weeks",
            "description": "Master modern frameworks and advanced development techniques.",
            "courses": ["React Fundamentals", "Node.js Basics", "MongoDB Essentials", "RESTful APIs", "Authentication & Security"],
            "projects": ["Dynamic Web Application", "REST API Service"]
        },
        {
            "title": "Real Projects & Career Preparation",
            "status": "locked",
            "progress": 0,
            "no_of_courses": 3,
            "no_of_projects": 1,
            "duration": "12 weeks",
            "description": "Apply your skills to real-world projects and prepare for your career.",
            "courses": ["Full-Stack Project", "Deployment & DevOps", "Performance Optimization"],
            "projects": ["Professional Web Application"]
        }
    ]
    
    # Calculate overall path progress
    progress_percentage = 45
    
    # Sample learning path courses
    learning_path_courses = [
        {"title": "HTML & CSS Fundamentals", "is_completed": True, "is_current": False},
        {"title": "JavaScript Basics", "is_completed": True, "is_current": False},
        {"title": "Advanced JavaScript", "is_completed": False, "is_current": True},
        {"title": "React Framework", "is_completed": False, "is_current": False},
        {"title": "Backend with Node.js", "is_completed": False, "is_current": False}
    ]
    
    user_streak = 3
    daily_goal_text = "Complete today's lesson"

    return render_template(
        "dashboard.html", 
        user=current_user,
        enrolled_courses=enrolled_courses,
        completed_courses=completed_courses,
        in_progress_courses=in_progress_courses,
        weekly_streak=weekly_streak,
        achievements=achievements,
        recent_activities=recent_activities,
        user_streak=user_streak,
        daily_goal_text=daily_goal_text,
        learning_path=True,
        learning_path_courses=learning_path_courses,
        path_details=path_details,
        modules=modules,
        progress_percentage=progress_percentage
    )

@views.route('/learning-path')
@login_required
def learning_path():
    # This page will display the user's complete learning path
    
    # Get the user's learning path
    user_learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
    
    # Default sample data for the learning path if none exists
    if not user_learning_path:
        path_name = "Web Developer"  # Default path
    else:
        path_name = user_learning_path.career_path
    
    # Sample path details based on career path
    path_details = {
        "title": path_name,
        "icon": "fa-code",  # Default icon
        "duration": "6-8 months",
        "courses": 12,
        "modules": 4,
        "description": "This learning path is designed to help you become a proficient " + path_name + ". Follow the curriculum to build your skills progressively."
    }
    
    # Set different icons based on career path
    if "Data" in path_name:
        path_details["icon"] = "fa-chart-bar"
    elif "Web" in path_name:
        path_details["icon"] = "fa-globe"
    elif "Mobile" in path_name:
        path_details["icon"] = "fa-mobile-alt"
    elif "Security" in path_name or "Cyber" in path_name:
        path_details["icon"] = "fa-shield-alt"
    elif "AI" in path_name or "Machine" in path_name:
        path_details["icon"] = "fa-robot"
    elif "Game" in path_name:
        path_details["icon"] = "fa-gamepad"
    
    # Sample modules for the learning path
    modules = [
        {
            "title": "Programming Fundamentals",
            "status": "completed",
            "progress": 100,
            "no_of_courses": 3,
            "duration": "4 weeks",
            "description": "Learn the basics of programming including variables, data types, conditionals, loops, and functions.",
            "courses": ["Introduction to Programming", "Python Basics", "Data Structures"],
            "projects": []
        },
        {
            "title": "Frameworks & Advanced Development",
            "status": "current",
            "progress": 45,
            "no_of_courses": 4,
            "duration": "6 weeks",
            "description": "Build on your programming knowledge by learning popular frameworks and advanced development techniques.",
            "courses": ["Web Frameworks", "APIs", "Database Integration", "Testing Strategies"],
            "projects": []
        },
        {
            "title": "Real Projects & Career Preparation",
            "status": "locked",
            "progress": 0,
            "no_of_courses": 3,
            "no_of_projects": 2,
            "duration": "8 weeks",
            "description": "Apply your skills to real-world projects and prepare for your career in the industry.",
            "courses": ["Project Management", "Deployment", "Career Strategies"],
            "projects": ["Capstone Project", "Portfolio Development"]
        }
    ]
    
    # Calculate overall progress percentage
    completed_modules = sum(1 for module in modules if module["status"] == "completed")
    current_progress = sum(module["progress"] for module in modules if module["status"] == "current") / 100
    total_modules = len(modules)
    progress_percentage = int((completed_modules + current_progress) / total_modules * 100)
    
    return render_template(
        'learning_path.html',
        user=current_user,
        path_details=path_details,
        modules=modules,
        progress_percentage=progress_percentage,
        path_name=path_name
    )

@views.route('/courses')
@login_required
def courses():
    # This function is the new courses route that will display all courses
    # It basically has the same functionality as my_courses but with a different URL
    
    # Initialize variables
    learning_path_courses = []
    recommended_courses = []
    in_progress_courses = []
    completed_courses = []
    bookmarked_courses = []
    
    # Check if user has completed the CS interest survey
    if not current_user.is_survey_completed:
        # User hasn't completed the survey yet, return template with empty data
        # and a message encouraging them to complete the survey
        return render_template(
            'courses.html',
            user=current_user,
            learning_path_courses=[],
            recommended_courses=[],
            in_progress_courses=[],
            completed_courses=[],
            bookmarked_courses=[],
            survey_completed=False
        )
    
    # Get the user's learning path
    user_learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
    
    # If user doesn't have a learning path, create one
    if not user_learning_path:
        # Logic for creating a learning path would go here
        # For now, just display an empty course list
        return render_template(
            'courses.html',
            user=current_user,
            learning_path_courses=[],
            recommended_courses=[],
            in_progress_courses=[],
            completed_courses=[],
            bookmarked_courses=[],
            survey_completed=True
        )
    
    # If user has a learning path, get courses from it
        # Get courses from learning_path_course association table
        path_courses = db.session.query(Course, learning_path_course.c.order)\
            .join(learning_path_course, Course.id == learning_path_course.c.course_id)\
            .filter(learning_path_course.c.learning_path_id == user_learning_path.id)\
            .order_by(learning_path_course.c.order).all()
        
        # Format courses with additional info
        for course, order in path_courses:
            # Get enrollment status and progress
            enrollment = db.session.query(user_course).filter_by(
                user_id=current_user.id, 
                course_id=course.id
            ).first()
            
            progress = 0
            is_enrolled = False
            is_completed = False
            
            if enrollment:
                is_enrolled = True
                progress = enrollment.progress if enrollment.progress else 0
                is_completed = True if enrollment.completed_at else False
            
            course_data = {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "image_url": course.image_url,
                "level": course.level,
                "category": course.category_name,
                "is_enrolled": is_enrolled,
                "is_completed": is_completed,
                "progress": progress,
                "order": order,
                "is_bookmarked": course.is_bookmarked
            }
            
            learning_path_courses.append(course_data)
            
            # Categorize courses by status
            if is_completed:
                completed_courses.append(course_data)
            elif is_enrolled and progress > 0:
                in_progress_courses.append(course_data)
            
            if course.is_bookmarked:
                bookmarked_courses.append(course_data)
    
    # Recommend other courses based on user's interests from survey
    user_survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
    if user_survey:
        # Sample logic to recommend courses based on survey interests
        # In a real app, this would be more sophisticated
        high_interest_areas = []
        
        if user_survey.web_development_interest and user_survey.web_development_interest >= 4:
            high_interest_areas.append('Web Development')
        if user_survey.data_science_interest and user_survey.data_science_interest >= 4:
            high_interest_areas.append('Data Science')
        if user_survey.cybersecurity_interest and user_survey.cybersecurity_interest >= 4:
            high_interest_areas.append('Cybersecurity')
        if user_survey.mobile_development_interest and user_survey.mobile_development_interest >= 4:
            high_interest_areas.append('Mobile Development')
        if user_survey.artificial_intelligence_interest and user_survey.artificial_intelligence_interest >= 4:
            high_interest_areas.append('Artificial Intelligence')
        
        if high_interest_areas:
            # Find courses that match user's interests but aren't in their learning path
            all_enrolled_course_ids = [course["id"] for course in learning_path_courses]
            
            for area in high_interest_areas:
                interest_courses = Course.query.filter(
                    Course.category_name.like(f"%{area}%"),
                    ~Course.id.in_(all_enrolled_course_ids) if all_enrolled_course_ids else True
                ).limit(3).all()
                
                for course in interest_courses:
                    recommended_courses.append({
                        "id": course.id,
                        "title": course.title,
                        "description": course.description,
                        "image_url": course.image_url,
                        "level": course.level,
                        "category": course.category_name,
                        "interest_area": area
                    })
    
    return render_template(
        'courses.html',
        user=current_user,
        learning_path_courses=learning_path_courses,
        recommended_courses=recommended_courses,
        in_progress_courses=in_progress_courses,
        completed_courses=completed_courses,
        bookmarked_courses=bookmarked_courses,
        survey_completed=True
    )

@views.route('/my-courses')
@login_required
def my_courses():
    # Redirect to the courses route to maintain backwards compatibility
    return redirect(url_for('views.courses'))

@views.route('/course/<int:course_id>')
@login_required
def course(course_id):
    # This page will display a single course
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)

@views.route('/module/<int:module_id>')
@login_required
def module(module_id):
    # This page will display a lesson/module
    module = Module.query.get_or_404(module_id)
    return render_template('module.html', module=module)

@views.route('/progress')
@login_required
def progress():
    # Get user's learning progress data
    
    # Overall stats
    overall_stats = {
        "completion_rate": 67,
        "courses_completed": 12,
        "hours_learned": 86,
        "achievements_earned": 9
    }
    
    # Sample course progress data
    courses_progress = [
        {
            "name": "Python for Data Science", 
            "progress": 85, 
            "total_lessons": 20, 
            "completed_lessons": 17,
            "last_accessed": "2 days ago"
        },
        {
            "name": "Web Development Fundamentals", 
            "progress": 65, 
            "total_lessons": 20, 
            "completed_lessons": 13,
            "last_accessed": "yesterday"
        },
        {
            "name": "Machine Learning Basics", 
            "progress": 40, 
            "total_lessons": 15, 
            "completed_lessons": 6,
            "last_accessed": "5 days ago"
        }
    ]
    
    # Learning progress chart data
    chart_data = {
        "week": {
            "labels": ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            "hours": [2.5, 3.2, 1.8, 4.0, 2.7, 3.5, 1.9],
            "lessons": [3, 2, 1, 4, 2, 3, 2]
        },
        "month": {
            "labels": ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            "hours": [15.2, 18.7, 12.9, 20.1],
            "lessons": [12, 15, 10, 18]
        },
        "year": {
            "labels": ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            "hours": [35, 42, 38, 45, 40, 50, 55, 42, 47, 53, 48, 52],
            "lessons": [28, 32, 30, 35, 29, 38, 42, 32, 36, 40, 35, 39]
        }
    }
    
    # Achievements data
    achievements = [
        {
            "name": "Quick Starter",
            "description": "Complete first course within a week",
            "icon": "fas fa-rocket",
            "is_locked": False
        },
        {
            "name": "On Fire",
            "description": "Maintain a 7-day learning streak",
            "icon": "fas fa-fire",
            "is_locked": False
        },
        {
            "name": "Knowledge Hunter",
            "description": "Complete 10 different topics",
            "icon": "fas fa-brain",
            "is_locked": False
        },
        {
            "name": "Master Student",
            "description": "Complete 50 lessons with 95% score",
            "icon": "fas fa-award",
            "is_locked": True
        },
        {
            "name": "Coding Champion",
            "description": "Complete all programming courses",
            "icon": "fas fa-crown",
            "is_locked": True
        }
    ]
    
    # Learning streak data
    streak_data = {
        "current_streak": 5,
        "days": [
            {"day": "M", "date": 15, "is_active": True},
            {"day": "T", "date": 16, "is_active": True},
            {"day": "W", "date": 17, "is_active": True},
            {"day": "T", "date": 18, "is_active": True},
            {"day": "F", "date": 19, "is_active": True, "is_today": True},
            {"day": "S", "date": 20, "is_active": False},
            {"day": "S", "date": 21, "is_active": False}
        ]
    }
    
    # Learning milestones data
    milestones = [
        {
            "title": "Web Development Journey",
            "description": "Complete all HTML, CSS and JavaScript courses",
            "progress": 65,
            "total_lessons": 20,
            "completed_lessons": 13
        },
        {
            "title": "Data Science Path",
            "description": "Master Python, Statistics, and Machine Learning",
            "progress": 40,
            "total_lessons": 20,
            "completed_lessons": 8
        },
        {
            "title": "Cloud Computing",
            "description": "Learn AWS, Azure, and cloud architecture",
            "progress": 25,
            "total_lessons": 20,
            "completed_lessons": 5
        }
    ]
    
    # Recent activity data
    recent_activities = [
        {
            "title": "Completed Lesson",
            "details": "Advanced Python Functions - Python for Data Science",
            "time": "Today, 10:25 AM"
        },
        {
            "title": "Quiz Passed",
            "details": "HTML/CSS Fundamentals Quiz - Web Development Fundamentals",
            "time": "Yesterday, 3:40 PM"
        },
        {
            "title": "Started Course",
            "details": "Machine Learning Basics",
            "time": "5 days ago"
        },
        {
            "title": "Earned Achievement",
            "details": "Quick Learner - Complete 5 lessons in a day",
            "time": "1 week ago"
        }
    ]
    
    return render_template(
        'progress.html',
        user=current_user,
        overall_stats=overall_stats,
        courses_progress=courses_progress,
        chart_data=chart_data,
        achievements=achievements,
        streak_data=streak_data,
        milestones=milestones,
        recent_activities=recent_activities
    )

@views.route('/module_interface/<int:module_id>')
@login_required
def learning_interface(module_id):
    # Get the module from the database
    module = Module.query.get_or_404(module_id)
    
    # Sample module content sections
    content_sections = [
        {
            "title": "Introduction",
            "type": "text",
            "content": "<p>Welcome to this module! In this lesson, you will learn about the fundamental concepts related to this topic.</p>"
        },
        {
            "title": "Key Concepts",
            "type": "text",
            "content": "<h3>Important Terminology</h3><ul><li>Concept 1: Description of concept 1</li><li>Concept 2: Description of concept 2</li><li>Concept 3: Description of concept 3</li></ul>"
        },
        {
            "title": "Video Explanation",
            "type": "video",
            "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "duration": "10:30"
        },
        {
            "title": "Practice Exercise",
            "type": "interactive",
            "exercise_id": 123,
            "description": "Try solving these exercises to test your understanding."
        },
        {
            "title": "Summary",
            "type": "text",
            "content": "<p>In this module, you learned about several key concepts and how to apply them in practical scenarios.</p>"
        }
    ]
    
    # Related modules
    related_modules = [
        {"id": 1, "title": "Introduction to the Topic", "is_completed": True},
        {"id": 2, "title": "Advanced Applications", "is_completed": False},
        {"id": 3, "title": "Practical Examples", "is_completed": False}
    ]
    
    return render_template(
        'module_interface.html',
        user=current_user,
        module=module,
        content_sections=content_sections,
        related_modules=related_modules,
    )

@views.route('/tutors')
@login_required
def tutors():
    # Create a sample tutor object to pass to the template
    tutor = {
        'id': 1,
        'name': 'AI Learning Assistant',
        'description': 'Your personal learning assistant to help with any questions',
        'icon': 'fas fa-robot',
        'welcome_message': '<p>Hello! I\'m your AI learning assistant. Ask me any questions you have about your courses or learning path.</p>',
        'suggestions': [
            'How do I start learning Python?', 
            'What are the best resources for web development?', 
            'Explain algorithms and data structures'
        ],
        'model': 'OpenRouter AI'
    }
    
    # Sample chat history (empty by default)
    chat_history = []
    
    # Get current time for welcome message
    current_time = datetime.now().strftime("%H:%M")
    
    # This page will display the AI tutor chat interface
    return render_template('tutors.html', 
                          tutor=tutor, 
                          chat_history=chat_history,
                          current_time=current_time,
                          user=current_user)

# API Routes for the AI Tutor functionality
@views.route('/chat', methods=['POST'])
@login_required
def chat():
    """API endpoint for AI chat using OpenRouter."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'message': 'No message provided'}), 400
            
        user_message = data['message']
        
        # Get preferences from request if available
        preferences = data.get('preferences', {})
        response_style = preferences.get('response_style', 'balanced')
        
        # Check if we have a model configured
        if not config.OPENROUTER_MODEL:
            return jsonify({
                'success': True,
                'response': f"I received your message: {user_message}\n\nThis is a placeholder response since no AI model is configured in config.py."
            })
        
        # Prepare the request to OpenRouter
        headers = {
            'Authorization': f'Bearer {config.OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': request.host_url,  # Required by OpenRouter
            'X-Title': 'Skillora Learning Platform'  # Help identify your app to the API
        }
        
        # Create message payload with enhanced system instructions
        messages = [
            {
                "role": "system", 
                "content": config.GEMINI_SYSTEM_PROMPT
            },
            # Add a message to explicitly override the model's default behavior
            {
                "role": "assistant",
                "content": "I am Skillora AI, your educational learning assistant. How can I help you today?"
            },
            {
                "role": "user", 
                "content": user_message
            }
        ]
        
        # Set temperature based on response style
        temperature = config.TEMPERATURE
        if response_style == 'creative':
            temperature = min(temperature + 0.2, 1.0)
        elif response_style == 'precise':
            temperature = max(temperature - 0.3, 0.1)
        
        # Create the request payload
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": config.MAX_TOKENS
        }
        
        # Call the OpenRouter API
        response = requests.post(
            config.OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30  # Set a timeout to avoid hanging requests
        )
        
        # Check if the request was successful
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the assistant's message from the response
        ai_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        if not ai_response:
            ai_response = "I apologize, but I couldn't generate a proper response. Please try again."
        
        # Check if the response contains any forbidden self-identifications
        forbidden_phrases = [
            "I am a large language model",
            "I am an AI assistant created by Google",
            "I am an AI language model",
            "I was trained by Google",
            "I'm a text-based AI and cannot",
            "As an AI language model",
            "As a large language model"
        ]
        
        for phrase in forbidden_phrases:
            if phrase.lower() in ai_response.lower():
                ai_response = "As Skillora AI, " + ai_response.split(".", 1)[1].strip() if "." in ai_response else "I'm Skillora AI, your educational assistant. How can I help you with your learning journey?"
                break
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
    except requests.exceptions.RequestException as e:
        print(f"ERROR in OpenRouter API request: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error communicating with AI service: {str(e)}',
            'error_type': 'connectivity'
        }), 500
    except Exception as e:
        print(f"ERROR in chat: {str(e)}")
        traceback.print_exc()  # Print the full stack trace for debugging
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@views.route('/chat/clear', methods=['POST'])
@login_required
def clear_chat():
    """Clear the chat history stored in the database"""
    try:
        # In a real app, we would clear chat history from database
        # For now, just return success
        return jsonify({'success': True, 'message': 'Chat history cleared successfully'})
    except Exception as e:
        print(f"Error clearing chat history: {str(e)}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@views.route('/upload-image', methods=['POST'])
@login_required
def upload_image():
    """API endpoint for uploading images for chat"""
    try:
        # Check if a file was uploaded
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image provided'}), 400
            
        file = request.files['image']
        
        # Check if the file has a filename
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400
            
        # In a real app, we would save the file and store reference in database
        # For now, just return a success message with a mock URL
        image_url = url_for('static', filename='img/placeholder.jpg')
        
        return jsonify({
            'success': True, 
            'imageUrl': image_url,
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        print(f"ERROR in upload_image: {str(e)}")
        return jsonify({'success': False, 'message': f'Error uploading image: {str(e)}'}), 500

@views.route('/settings')
@login_required
def settings():
    # Default notification settings (in a real app, get these from the database)
    notification_settings = {
        'email_course_updates': True,
        'email_new_courses': True,
        'email_achievement': True,
        'email_reminders': False
    }
    
    # Default privacy settings
    privacy_settings = {
        'show_progress_public': True,
        'show_achievements_public': True,
        'enable_study_analytics': True
    }
    
    return render_template(
        'settings.html',
        user=current_user,
        notification_settings=notification_settings,
        privacy_settings=privacy_settings
    )

@views.route('/schedule')
@login_required
def schedule():
    # This is a placeholder for the schedule functionality
    flash('Schedule feature coming soon!', 'info')
    return redirect(url_for('views.dashboard'))

@views.route('/library')
@login_required
def library():
    # This is a placeholder for the library functionality
    flash('Library feature coming soon!', 'info')
    return redirect(url_for('views.dashboard'))

@views.route('/help')
@login_required
def help():
    # This is a placeholder for the help functionality
    return render_template('dashboard.html', user=current_user, 
                         help_active=True, 
                         title="Help & Support")

@views.route('/interests-survey', methods=['GET', 'POST'])
@login_required
def interests_survey():
    # This page will handle the CS interests survey
    if request.method == 'POST':
        # Process survey submission
        pass
    return render_template('interests_survey.html')

@views.route('/create-learning-path')
@login_required
def create_learning_path():
    # This page will let users create a learning path
    return render_template('create_learning_path.html')

@views.route('/cs-interest-survey', methods=['GET', 'POST'])
@login_required
def cs_interest_survey():
    """Handle the CS interest survey page"""
    
    # Redirect if already completed (can be disabled for testing)
    if current_user.is_survey_completed and request.method == 'GET':
        flash('You have already completed the survey.', category='info')
        return redirect(url_for('views.dashboard'))

    # Handle form submission
    if request.method == 'POST':
        try:
            # Get form data for interest areas
            algorithms = request.form.get('algorithms_interest', type=int)
            data_science = request.form.get('data_science_interest', type=int)
            web_dev = request.form.get('web_development_interest', type=int)
            mobile_dev = request.form.get('mobile_development_interest', type=int)
            cybersecurity = request.form.get('cybersecurity_interest', type=int)
            ai = request.form.get('artificial_intelligence_interest', type=int)
            game_dev = request.form.get('game_development_interest', type=int)
            systems = request.form.get('systems_programming_interest', type=int)

            # Get other form data
            learning_style = request.form.get('preferred_learning_style')
            time_availability = request.form.get('learning_time_availability')
            prior_experience = request.form.get('prior_experience')
            
            # Get career goal - handle the "Other" option
            career_goal = request.form.get('career_goal')
            if career_goal == 'Other':
                career_goal = request.form.get('other_career_goal')

            # Check if user already has a survey record
            survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()

            if not survey:
                # Create new survey
                survey = CSInterestSurvey(user_id=current_user.id)
                db.session.add(survey)
            
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
            survey.learning_time_availability = time_availability
            survey.prior_experience = prior_experience
            survey.career_goal = career_goal
            survey.updated_at = datetime.now()
            
            # Mark the survey as completed for the user
            current_user.is_survey_completed = True
            
            # Determine recommended career path based on highest interests
            interests = {
                'Software Engineer': algorithms,
                'Data Scientist': data_science,
                'Web Developer': web_dev,
                'Mobile App Developer': mobile_dev,
                'Cybersecurity Specialist': cybersecurity,
                'AI/ML Engineer': ai,
                'Game Developer': game_dev,
                'Systems Engineer': systems
            }
            
            # Use the user's chosen career path instead of highest interest if provided
            recommended_career = career_goal if career_goal else max(interests, key=interests.get)

            # Create or update learning path
            learning_path = LearningPath.query.filter_by(user_id=current_user.id).first()
            if not learning_path:
                learning_path = LearningPath(
                    user_id=current_user.id,
                    career_path=recommended_career,
                    date_created=datetime.now()
                )
                db.session.add(learning_path)
            else:
                learning_path.career_path = recommended_career
                learning_path.date_updated = datetime.now()
            
            # Commit the changes
            db.session.commit()
            
            flash('Thank you for completing the survey! We\'ve created a personalized learning path for you.', category='success')
            
            # Redirect to dashboard
            return redirect(url_for('views.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR submitting survey: {str(e)}")
            flash('An error occurred while submitting the survey. Please try again.', category='error')
            return render_template('cs_interest_survey.html', user=current_user)

    # GET request - show the survey form
    # Check if there's existing survey data to pre-fill the form
    existing_survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
    return render_template('cs_interest_survey.html', user=current_user, survey_data=existing_survey)

@views.route('/profile')
@login_required
def profile():
    # Get user's survey data
    survey_data = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
    
    # In a real app, we would retrieve these from the database
    # Default user profile data
    user_profile = {
        'bio': 'I am passionate about learning new technology skills.',
        'location': 'New York, NY',
        'website': 'https://example.com'
    }
    
    # Sample education history
    education_history = []
    
    # Calculate joined date
    joined_date = current_user.date_created.strftime("%B %Y") if hasattr(current_user, 'date_created') else "January 2023"
    
    # Get achievement data
    achievements = [
        {"title": "Fast Learner", "description": "Completed 3 courses in a week", "icon": "fas fa-bolt"},
        {"title": "Quiz Master", "description": "Scored 100% on 5 quizzes", "icon": "fas fa-crown"},
        {"title": "Dedication", "description": "Maintained a 7-day streak", "icon": "fas fa-fire"}
    ]
    
    # Sample data for other statistics
    enrolled_courses = []
    completed_courses = []
    user_streak = 7  # Days
    
    return render_template(
        'profile.html',
        user=current_user,
        survey_data=survey_data,
        user_profile=user_profile,
        education_history=education_history,
        achievements=achievements,
        enrolled_courses=enrolled_courses,
        completed_courses=completed_courses,
        user_streak=user_streak,
        joined_date=joined_date
    )

# CRUD Operations for Profile

@views.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            bio = request.form.get('bio')
            location = request.form.get('location')
            website = request.form.get('website')
            
            # Update the user model
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.email = email
            
            # In a real app, we would update or create a user profile model
            # profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            # if not profile:
            #     profile = UserProfile(user_id=current_user.id)
            #     db.session.add(profile)
            # profile.bio = bio
            # profile.location = location
            # profile.website = website
            
            # Commit changes
            db.session.commit()
            
            flash('Profile updated successfully!', category='success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', category='error')
        
        return redirect(url_for('views.profile'))

@views.route('/update-preferences', methods=['POST'])
@login_required
def update_preferences():
    if request.method == 'POST':
        try:
            # Get form data
            career_goal = request.form.get('career_goal')
            learning_style = request.form.get('preferred_learning_style')
            time_availability = request.form.get('learning_time_availability')
            prior_experience = request.form.get('prior_experience')
            
            # Update survey data
            survey = CSInterestSurvey.query.filter_by(user_id=current_user.id).first()
            if survey:
                survey.career_goal = career_goal
                survey.preferred_learning_style = learning_style
                survey.learning_time_availability = time_availability
                survey.prior_experience = prior_experience
                survey.updated_at = datetime.now()
                
                # Commit changes
                db.session.commit()
                
                flash('Learning preferences updated successfully!', category='success')
            else:
                flash('No survey data found to update.', category='error')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating preferences: {str(e)}', category='error')
        
        return redirect(url_for('views.profile'))

@views.route('/add-education', methods=['POST'])
@login_required
def add_education():
    if request.method == 'POST':
        try:
            # Get form data
            education_id = request.form.get('education_id')
            institution = request.form.get('institution')
            degree = request.form.get('degree')
            field = request.form.get('field')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            # In a real app, we would create or update an education model
            # if education_id and education_id.isdigit():
            #     # Update existing education
            #     edu = Education.query.get(int(education_id))
            #     if edu and edu.user_id == current_user.id:
            #         edu.institution = institution
            #         edu.degree = degree
            #         edu.field = field
            #         edu.start_date = start_date
            #         edu.end_date = end_date
            #         flash('Education updated successfully!', category='success')
            #     else:
            #         flash('Education entry not found.', category='error')
            # else:
            #     # Create new education entry
            #     new_edu = Education(
            #         user_id=current_user.id,
            #         institution=institution,
            #         degree=degree,
            #         field=field,
            #         start_date=start_date,
            #         end_date=end_date
            #     )
            #     db.session.add(new_edu)
            #     flash('Education added successfully!', category='success')
            
            # Commit changes
            # db.session.commit()
            
            flash('Education information saved successfully!', category='success')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error saving education: {str(e)}', category='error')
        
        return redirect(url_for('views.profile'))

@views.route('/delete-education/<int:education_id>', methods=['POST'])
@login_required
def delete_education(education_id):
    if request.method == 'POST':
        try:
            # In a real app, we would delete the education entry
            # edu = Education.query.get(education_id)
            # if edu and edu.user_id == current_user.id:
            #     db.session.delete(edu)
            #     db.session.commit()
            #     flash('Education entry deleted successfully!', category='success')
            # else:
            #     flash('Education entry not found or unauthorized.', category='error')
            
            flash('Education entry deleted successfully!', category='success')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error deleting education: {str(e)}', category='error')
        
        return redirect(url_for('views.profile'))

# CRUD Operations for Settings

@views.route('/update-account-settings', methods=['POST'])
@login_required
def update_account_settings():
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Verify that the current password is correct
            # In a real app, we would check the password hash
            # if check_password_hash(current_user.password, current_password):
            #     if new_password and new_password == confirm_password:
            #         # Update password
            #         current_user.password = generate_password_hash(new_password)
            #         db.session.commit()
            #         flash('Password updated successfully!', category='success')
            #     elif new_password:
            #         flash('New passwords do not match.', category='error')
            # else:
            #     flash('Current password is incorrect.', category='error')
            
            flash('Password updated successfully!', category='success')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error updating account settings: {str(e)}', category='error')
        
        return redirect(url_for('views.settings'))

@views.route('/update-notification-settings', methods=['POST'])
@login_required
def update_notification_settings():
    if request.method == 'POST':
        try:
            # Get form data
            email_course_updates = 'email_course_updates' in request.form
            email_new_courses = 'email_new_courses' in request.form
            email_achievement = 'email_achievement' in request.form
            email_reminders = 'email_reminders' in request.form
            
            # In a real app, we would update notification settings
            # notification_settings = NotificationSettings.query.filter_by(user_id=current_user.id).first()
            # if not notification_settings:
            #     notification_settings = NotificationSettings(user_id=current_user.id)
            #     db.session.add(notification_settings)
            # 
            # notification_settings.email_course_updates = email_course_updates
            # notification_settings.email_new_courses = email_new_courses
            # notification_settings.email_achievement = email_achievement
            # notification_settings.email_reminders = email_reminders
            # 
            # db.session.commit()
            
            flash('Notification settings updated successfully!', category='success')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error updating notification settings: {str(e)}', category='error')
        
        return redirect(url_for('views.settings'))

@views.route('/update-privacy-settings', methods=['POST'])
@login_required
def update_privacy_settings():
    if request.method == 'POST':
        try:
            # Get form data
            show_progress_public = 'show_progress_public' in request.form
            show_achievements_public = 'show_achievements_public' in request.form
            enable_study_analytics = 'enable_study_analytics' in request.form
            
            # In a real app, we would update privacy settings
            # privacy_settings = PrivacySettings.query.filter_by(user_id=current_user.id).first()
            # if not privacy_settings:
            #     privacy_settings = PrivacySettings(user_id=current_user.id)
            #     db.session.add(privacy_settings)
            # 
            # privacy_settings.show_progress_public = show_progress_public
            # privacy_settings.show_achievements_public = show_achievements_public
            # privacy_settings.enable_study_analytics = enable_study_analytics
            # 
            # db.session.commit()
            
            flash('Privacy settings updated successfully!', category='success')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error updating privacy settings: {str(e)}', category='error')
        
        return redirect(url_for('views.settings'))

@views.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        try:
            # Get form data
            delete_confirmation = request.form.get('delete_confirmation')
            password_confirmation = request.form.get('password_confirmation')
            
            # Check confirmation text and password
            if delete_confirmation == 'DELETE':
                # In a real app, we would verify the password and delete the account
                # if check_password_hash(current_user.password, password_confirmation):
                #     user_id = current_user.id
                #     logout_user()
                #     user = User.query.get(user_id)
                #     db.session.delete(user)
                #     db.session.commit()
                #     flash('Your account has been deleted.', category='info')
                #     return redirect(url_for('auth.login'))
                # else:
                #     flash('Password is incorrect.', category='error')
                
                flash('Your account has been scheduled for deletion. You will be logged out shortly.', category='info')
                return redirect(url_for('auth.logout'))
            else:
                flash('Confirmation text is incorrect.', category='error')
            
        except Exception as e:
            # db.session.rollback()
            flash(f'Error deleting account: {str(e)}', category='error')
        
        return redirect(url_for('views.settings'))

# Helper functions
def get_time_ago(date):
    """Convert a datetime to a 'time ago' string"""
    if not date:
        return "Unknown time"
    
    now = datetime.now()
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def parse_time_ago(time_ago):
    """Convert a 'time ago' string back to a relative timestamp for sorting"""
    if time_ago == "Just now":
        return datetime.now()
    
    # Extract the number and unit
    parts = time_ago.split()
    if len(parts) < 3:
        return datetime.now()
    
    value = int(parts[0])
    unit = parts[1]
    
    now = datetime.now()
    
    if 'year' in unit:
        return now - timedelta(days=value * 365)
    elif 'month' in unit:
        return now - timedelta(days=value * 30)
    elif 'day' in unit:
        return now - timedelta(days=value)
    elif 'hour' in unit:
        return now - timedelta(hours=value)
    elif 'minute' in unit:
        return now - timedelta(minutes=value)
    else:
        return now

def calculate_user_streak(user_id):
    """Calculate the user's current learning streak in days"""
    # For demo purposes, generate a random streak
    # In a real app, we would track daily logins or activity
    return random.randint(1, 14)

def calculate_daily_goal_progress(user_id):
    """Calculate the user's progress towards their daily learning goal"""
    # For demo purposes, generate random progress
    progress = random.randint(0, 100)
    goal_text = "30 minutes of learning"
    
    return progress, goal_text

def generate_weekly_streak(user_id):
    """Generate the user's weekly streak data"""
    # For demo purposes, generate random streak data
    days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
    streak = []
    
    # Get the current day of the week (0 = Monday, 6 = Sunday)
    today = datetime.now().weekday()
    
    for i in range(7):
        if i < today:
            # Past days are either completed or not
            status = 'completed' if random.random() > 0.3 else ''
        elif i == today:
            # Today might be in progress
            status = 'today'
        else:
            # Future days have no status
            status = ''
            
        streak.append({
            'label': days[i],
            'status': status
        })
    
    return streak


def get_chapters_for_career_path(career_path):
    """Returns a list of standard chapter/module titles for a career path."""
    # This should ideally come from your Course/Module models or a config
    # Hardcoded example:
    path_modules = {
        "Data Scientist": [
            "Introduction to Data Science",
            "Python for Data Analysis (Pandas & NumPy)",
            "Data Visualization (Matplotlib & Seaborn)",
            "Introduction to Machine Learning",
            "SQL for Data Scientists",
            "Statistics Fundamentals",
            "Feature Engineering",
            "Model Evaluation and Selection",
            "Deep Learning Basics",
            "Data Science Capstone Project Ideas"
        ],
        "Web Developer": [
            "HTML Fundamentals",
            "CSS Styling and Layouts",
            "JavaScript Basics and DOM Manipulation",
            "Responsive Web Design",
            "Version Control with Git",
            "Introduction to Frontend Frameworks (e.g., React or Vue)",
            "Backend Development Basics (e.g., Node.js/Express or Python/Flask)",
            "Database Fundamentals (SQL or NoSQL)",
            "API Basics (REST)",
            "Deployment Essentials"
        ],
        # Add mappings for ALL career paths you support
        "Software Engineer": [ # Example
            "Programming Fundamentals (Choose Language: Python/Java/C++)",
            "Data Structures",
            "Algorithms",
            "Object-Oriented Design Principles",
            "Version Control (Git)",
            "Databases (SQL Basics)",
            "Operating Systems Concepts",
            "Networking Basics",
            "Software Testing Fundamentals",
            "Introduction to Agile/Scrum"
        ]
        # ... add other paths
    }
    # Default if path not found
    default_modules = [f"Module {i+1} for {career_path}" for i in range(5)]
    return path_modules.get(career_path, default_modules)[:10] # Limit to 10 videos as per example

# views.py

# Wrapper function to run the async video finder and update the DB
def background_video_finder_task(app_context, learning_path_id):
    """Runs the async video finder for relevant modules and updates the DB."""
    with app_context: # Essential for DB access in background thread
        print(f"[Executor Task] Starting video finding for LearningPath ID: {learning_path_id}")
        learning_path = None
        try:
            # 1. Get Learning Path and Survey Data
            learning_path = LearningPath.query.get(learning_path_id)
            if not learning_path:
                print(f"[Executor Task] Error: LearningPath {learning_path_id} not found.")
                return

            survey = CSInterestSurvey.query.filter_by(user_id=learning_path.user_id).first()
            if not survey:
                print(f"[Executor Task] Warning: CSInterestSurvey not found for user {learning_path.user_id}. Using defaults.")
                # Assign default preferences if needed by the finder function
                learning_style = "Visual"
                time_availability = "5-10 hours"
            else:
                learning_style = survey.preferred_learning_style or "Visual"
                time_availability = survey.learning_time_availability or "5-10 hours"

            topic = learning_path.career_path
            print(f"[Executor Task] Path: {topic}, Style: {learning_style}, Time: {time_availability}")
            # 2. Determine Chapters/Modules to process
            # --- Logic to Create/Find Courses & Modules ---
            # This is CRITICAL and needs to be robust
            target_chapter_titles = get_chapters_for_career_path(topic)
            print(f"[Executor Task] Target chapters: {target_chapter_titles}")

            # Ensure Course/Module records exist in DB for these titles
            # You might need a helper function: ensure_modules_exist(user_id, learning_path_id, topic, target_chapter_titles)
            # This function would query for existing courses/modules or create them.
            # For now, we'll just query based on title assuming they might exist.

            modules_in_db = Module.query.join(Course).filter(
                Course.user_id == learning_path.user_id, # Ensure they belong to the user
                Course.category_name == topic, # Match the learning path topic
                Module.title.in_(target_chapter_titles)
            ).all()

            module_map = {module.title: module.id for module in modules_in_db}
            print(f"[Executor Task] Found {len(module_map)} existing modules in DB for target titles.")

            # If modules don't exist, you need to create them here before proceeding.
            # This example proceeds assuming they exist or creation logic is added.
            if len(module_map) != len(target_chapter_titles):
                 print("[Executor Task] Warning: Not all target chapters have corresponding Module records in the DB. Video links for missing modules cannot be saved.")
                 # Filter the list to only those we have module IDs for
                 target_chapter_titles = [title for title in target_chapter_titles if title in module_map]


            if not target_chapter_titles:
                print(f"[Executor Task] No existing modules match target chapters for path {learning_path_id}. Cannot find videos.")
                # Update path status maybe?
                learning_path.generation_status = "error: no modules"
                db.session.commit()
                return

            # 3. Run the async finder function
            num_workers = current_app.config.get('EXECUTOR_MAX_WORKERS', 2)
            video_results_dict = asyncio.run(
                find_videos_for_course_chapters(
                    topic=topic,
                    chapter_titles=target_chapter_titles,
                    learning_style=learning_style,
                    time_availability=time_availability,
                    num_concurrent_agents=num_workers
                    )
            )

            print(f"[Executor Task] Video finder finished. Results received for {len(video_results_dict)} chapters.")

            # 4. Update Database Modules
            updated_count = 0
            for chapter_title, video_url in video_results_dict.items():
                module_id = module_map.get(chapter_title) # Find module ID using the title
                if module_id:
                    module_to_update = Module.query.get(module_id) # Fetch specific module
                    if module_to_update:
                        if video_url:
                            module_to_update.youtube_links = json.dumps([video_url])
                            module_to_update.content_type = 'video'
                            print(f"  -> Updating Module {module_id} ('{chapter_title}') with URL.")
                            updated_count += 1
                        else:
                            # Only update if it doesn't already have an error/link
                            if not module_to_update.youtube_links or module_to_update.youtube_links in ('[]', 'None', None):
                                 module_to_update.youtube_links = json.dumps(["ERROR: Video not found"])
                                 print(f"  -> Marking Module {module_id} ('{chapter_title}') as 'Not Found'.")
                                 updated_count += 1
                    else:
                        print(f"[Executor Task] Warning: Module ID {module_id} (from map) not found during update.")
                else:
                     print(f"[Executor Task] Warning: Could not find module ID for chapter '{chapter_title}' during update.")

            if updated_count > 0:
                learning_path.generation_status = "complete" # Mark path as done
                db.session.commit()
                print(f"[Executor Task] Database commit successful for {updated_count} modules.")
            else:
                print("[Executor Task] No modules were updated in the database.")
                if learning_path.generation_status == 'pending': # Avoid overwriting error status
                     learning_path.generation_status = "complete: no updates"
                     db.session.commit()


        except Exception as task_exc:
            print(f"[Executor Task] !!! EXCEPTION IN BACKGROUND TASK for LearningPath {learning_path_id}: {task_exc}")
            traceback.print_exc()
            if learning_path:
                try:
                     learning_path.generation_status = f"error: {type(task_exc).__name__}"
                     db.session.commit()
                except Exception as db_err:
                     print(f"[Executor Task] Error updating LearningPath status on failure: {db_err}")
        finally:
            print(f"[Executor Task] Finished processing for LearningPath ID: {learning_path_id}")



