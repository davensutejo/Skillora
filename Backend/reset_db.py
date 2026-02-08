from website import create_app, db
from website.models import User, Note, Course, Category, Lesson, Achievement, PasswordReset, EmailVerification, ChatMessage
from website.models import Module, LearningPath, UserProgress, Schedule, Resource
import os

app = create_app()

def reset_database():
    """Reset the database by dropping all tables and recreating them."""
    with app.app_context():
        # Remove existing database file if it exists
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'database.db')
        if os.path.exists(db_path):
            print(f"Removing existing database file: {db_path}")
            os.remove(db_path)
        
        # Create database tables
        print("Creating new database tables...")
        db.create_all()
        print("Database reset completed successfully.")

if __name__ == "__main__":
    reset_database() 