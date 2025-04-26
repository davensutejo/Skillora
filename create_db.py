from website import db , create_app
from website.models import User, Note, Course, Category, Lesson, Achievement, PasswordReset, EmailVerification, ChatMessage
from website.models import Module, LearningPath, UserProgress, Schedule, Resource

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables created successfully.")