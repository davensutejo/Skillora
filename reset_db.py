#!/usr/bin/env python
"""
Database Reset Script for Skillora application
This script will drop all tables and recreate them, giving you a fresh database.
"""

import os
import sys
from website import create_app, db
from website.models import User, Course, Category, Module, Quiz, QuizQuestion, UserProgress, Achievement, LearningPath

# Add confirmation to prevent accidental execution
if len(sys.argv) > 1 and sys.argv[1] == '--force':
    force = True
else:
    force = False
    
    print("WARNING: This will delete all data in your database!")
    print("To confirm, type 'reset' and press Enter:")
    confirmation = input("> ").strip().lower()
    
    if confirmation == 'reset':
        force = True
    
if not force:
    print("Database reset canceled.")
    sys.exit(0)

# Create the application instance
app = create_app()

# Create a context to work with the app
with app.app_context():
    # Drop all tables
    print("Dropping all tables...")
    db.drop_all()
    
    # Create all tables
    print("Creating all tables...")
    db.create_all()
    
    # Optionally add seed data
    if len(sys.argv) > 1 and sys.argv[1] == '--seed':
        print("Adding seed data...")
        
        # Create categories
        categories = [
            Category(name="Web Development", description="Learn to build websites and web applications"),
            Category(name="Data Science", description="Learn data analysis and machine learning"),
            Category(name="Mobile Development", description="Build mobile apps for iOS and Android"),
            Category(name="Design", description="Learn UI/UX design principles"),
            Category(name="Business", description="Business and entrepreneurship courses")
        ]
        
        for category in categories:
            db.session.add(category)
        
        # Create admin user
        admin_user = User(
            email="admin@skillora.com",
            password="pbkdf2:sha256:260000$6EqFvv0ToRiZkVnW$c22a0a4e443e20bbb0adce46ec9c27a41038534e25fbe72f6e8442c0f5971c7a",  # Password: Admin123!
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_admin=True,
            created_at=db.func.now()
        )
        db.session.add(admin_user)
        
        # Create demo user
        demo_user = User(
            email="demo@skillora.com",
            password="pbkdf2:sha256:260000$q7zdFbNH1bAYFR6M$ecd82c35a201f3e97b2e6fc99cfccee8dae3c39035b650c10a4b7b5d797f7b57",  # Password: Demo123!
            first_name="Demo",
            last_name="User",
            is_active=True,
            created_at=db.func.now()
        )
        db.session.add(demo_user)
        
        # Create sample courses
        courses = [
            {
                "title": "Introduction to Web Development",
                "description": "Learn the fundamentals of web development including HTML, CSS, and JavaScript to build your first website.",
                "level": "Beginner",
                "duration": "8 hours",
                "price": 0.00,  # Free course
                "category_id": 1,
                "image_url": "/static/images/courses/web-dev.jpg"
            },
            {
                "title": "Python for Data Science",
                "description": "Learn how to use Python for data analysis, visualization, and basic machine learning models.",
                "level": "Intermediate",
                "duration": "15 hours",
                "price": 49.99,
                "category_id": 2,
                "image_url": "/static/images/courses/python-data.jpg"
            },
            {
                "title": "Advanced JavaScript Programming",
                "description": "Master modern JavaScript concepts like promises, async/await, closures, and ES6+ features.",
                "level": "Advanced",
                "duration": "12 hours",
                "price": 59.99,
                "category_id": 1,
                "image_url": "/static/images/courses/javascript.jpg"
            },
            {
                "title": "UX/UI Design Fundamentals",
                "description": "Learn the principles of user experience and interface design to create intuitive and beautiful digital products.",
                "level": "Intermediate",
                "duration": "10 hours",
                "price": 39.99,
                "category_id": 4,
                "image_url": "/static/images/courses/ux-design.jpg"
            }
        ]
        
        for course_data in courses:
            course = Course(**course_data)
            db.session.add(course)
        
        # Commit all seed data
        db.session.commit()
        print("Seed data added successfully!")
    
    print("Database has been reset successfully!") 