from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Table
from sqlalchemy.orm import relationship
import json


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    
    # Additional profile fields
    username = db.Column(db.String(50), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    job_title = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    timezone = db.Column(db.String(50), nullable=True)
    
    # Account status and settings
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_survey_completed = db.Column(db.Boolean, default=False)  # Track if CS interests survey is completed
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Notification and privacy settings
    email_notifications = db.Column(db.Boolean, default=True)
    public_profile = db.Column(db.Boolean, default=True)
    show_courses = db.Column(db.Boolean, default=True)
    show_achievements = db.Column(db.Boolean, default=True)
    
    # Relationships
    notes = db.relationship('Note')
    courses = db.relationship('Course')
    achievements = db.relationship('Achievement', back_populates='user')
    user_progress = db.relationship('UserProgress', back_populates='user')
    schedules = db.relationship('Schedule', back_populates='user')
    cs_survey = db.relationship('CSInterestSurvey', backref='user', uselist=False)
    learning_path = db.relationship('LearningPath')
    cs_interest = db.relationship('CSInterest')
    quiz_attempts = db.relationship('QuizAttempt')

    def __repr__(self):
        return f'User({self.id}, {self.email})'


# Course and related models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(1000))
    category_name = db.Column(db.String(50))  # Renamed from 'category' to avoid conflicts
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)  # New foreign key
    level = db.Column(db.String(20))  # e.g., "Beginner", "Intermediate", "Advanced"
    image_url = db.Column(db.String(200))  # URL to course image
    order = db.Column(db.Integer)  # Order of course in learning path
    is_bookmarked = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    date_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    modules = db.relationship('Module', backref='course', cascade='all, delete-orphan')
    category = db.relationship('Category', back_populates='courses')  # New relationship


# Course enrollment relationship
user_course = db.Table('user_course',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('enrolled_at', db.DateTime(timezone=True), default=func.now()),
    db.Column('completed_at', db.DateTime(timezone=True), nullable=True),
    db.Column('progress', db.Float, default=0.0)
)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    courses = db.relationship('Course', back_populates='category')


# New Module model
class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(1000))
    content_type = db.Column(db.String(50), default="video")  # video, reading, exercise
    youtube_links = db.Column(db.Text)  # JSON string of YouTube URLs
    manim_video_path = db.Column(db.String(255))  # Path to the generated Manim video
    order = db.Column(db.Integer)  # Order of module in course
    estimated_time_minutes = db.Column(db.Integer, default=30)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Relationships
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    quiz = db.relationship('Quiz', backref='module', uselist=False, cascade='all, delete-orphan')
    lessons = db.relationship('Lesson', back_populates='module')
    
    def get_youtube_links(self):
        """Return the YouTube links as a list"""
        if self.youtube_links:
            return json.loads(self.youtube_links)
        return []
        
    def get_video_url(self):
        """Return the URL to the video (Manim video or first YouTube link)"""
        if self.manim_video_path:
            try:
                # Import from manim.py instead of manim_utils
                from .manim import get_module_video_url
                return get_module_video_url(self)
            except ImportError:
                # Fall back to the old approach if the function is not available
                try:
                    # Try to get a relative path from the absolute path
                    if 'static/' in self.manim_video_path:
                        relative_path = self.manim_video_path.split('static/')[1]
                        from flask import url_for
                        return url_for('static', filename=relative_path)
                    
                    # Try with backslashes for Windows paths
                    if 'static\\' in self.manim_video_path:
                        # Replace backslashes with forward slashes for URL
                        relative_path = self.manim_video_path.split('static\\')[1].replace('\\', '/')
                        from flask import url_for
                        return url_for('static', filename=relative_path)
                    
                    # If we can't determine the relative path, return the full path
                    return self.manim_video_path
                except Exception as e:
                    print(f"Error getting video URL: {e}")
                    # Fall back to YouTube if there's an error
                    youtube_links = self.get_youtube_links()
                    return youtube_links[0] if youtube_links else None
        
        # Fall back to YouTube links if no Manim video
        youtube_links = self.get_youtube_links()
        return youtube_links[0] if youtube_links else None
        
    def has_manim_video(self):
        """Check if this module has a generated Manim video"""
        return bool(self.manim_video_path)
        
    def get_video_metadata(self, api_key=None):
        """Get metadata for the videos to allow for better filtering"""
        if not self.youtube_links or not api_key:
            return []
            
        video_ids = []
        for link in self.get_youtube_links():
            # Extract video ID from YouTube URL
            if 'youtube.com/watch?v=' in link:
                video_id = link.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in link:
                video_id = link.split('/')[-1]
            else:
                continue
            video_ids.append(video_id)
            
        if not video_ids:
            return []
            
        try:
            # This would use the YouTube Data API to get video details
            # In a real implementation, you would make an API call like:
            # https://www.googleapis.com/youtube/v3/videos?id=video_id1,video_id2&part=snippet,contentDetails,statistics&key=YOUR_API_KEY
            # For now, we'll simulate the response
            
            # Sample metadata structure
            metadata = []
            for video_id in video_ids:
                # In a real implementation, this would be fetched from the API
                metadata.append({
                    'id': video_id,
                    'title': 'Video title',
                    'description': 'Video description',
                    'duration': 'PT15M',  # ISO 8601 duration format
                    'viewCount': '10000',
                    'likeCount': '500',
                    'dislikeCount': '50',
                    'tags': ['education', 'tutorial'],
                    'publishedAt': '2021-01-01T00:00:00Z'
                })
            return metadata
        except Exception as e:
            print(f"Error fetching video metadata: {e}")
            return []
            
    def filter_videos_by_preference(self, user_preferences, api_key=None):
        """
        Filter videos based on user preferences
        
        Args:
            user_preferences: Dict containing learning_style and preferred_duration
            api_key: YouTube API key for fetching metadata
            
        Returns:
            List of videos sorted by preference match
        """
        if not self.youtube_links:
            return []
            
        videos = self.get_youtube_links()
        metadata = self.get_video_metadata(api_key)
        
        # Match videos with their metadata
        video_data = []
        for i, video in enumerate(videos):
            video_info = {
                'url': video,
                'score': 0  # Initial score
            }
            
            # Add metadata if available
            if i < len(metadata):
                video_info['metadata'] = metadata[i]
                
                # Calculate duration in minutes if metadata exists
                if 'duration' in metadata[i]:
                    duration_str = metadata[i]['duration']
                    # Parse ISO 8601 duration (simplified)
                    minutes = 0
                    if 'M' in duration_str:
                        m_pos = duration_str.find('M')
                        t_pos = duration_str.find('T')
                        if t_pos != -1 and t_pos < m_pos:
                            minutes_str = duration_str[t_pos+1:m_pos]
                            try:
                                minutes = int(minutes_str)
                            except ValueError:
                                pass
                    video_info['duration_minutes'] = minutes
                    
                    # Score based on preferred duration
                    if 'preferred_duration' in user_preferences:
                        preferred_minutes = user_preferences['preferred_duration']
                        # Higher score for videos closer to preferred duration
                        duration_diff = abs(minutes - preferred_minutes)
                        if duration_diff <= 5:
                            video_info['score'] += 3  # Very close to preferred time
                        elif duration_diff <= 10:
                            video_info['score'] += 2  # Reasonably close
                        elif duration_diff <= 15:
                            video_info['score'] += 1  # Still acceptable
                        
                # Score based on engagement metrics
                if 'viewCount' in metadata[i] and 'likeCount' in metadata[i]:
                    try:
                        views = int(metadata[i]['viewCount'])
                        likes = int(metadata[i]['likeCount'])
                        
                        # Engagement ratio (likes/views)
                        if views > 0:
                            engagement = likes / views
                            if engagement > 0.1:  # More than 10% engagement
                                video_info['score'] += 3
                            elif engagement > 0.05:  # More than 5% engagement
                                video_info['score'] += 2
                            elif engagement > 0.01:  # More than 1% engagement
                                video_info['score'] += 1
                    except (ValueError, ZeroDivisionError):
                        pass
                
                # Score based on learning style
                if 'learning_style' in user_preferences and 'tags' in metadata[i]:
                    style = user_preferences['learning_style']
                    tags = metadata[i]['tags']
                    
                    style_keywords = {
                        'visual': ['visual', 'demonstration', 'animation', 'diagram'],
                        'auditory': ['lecture', 'discussion', 'explanation', 'talk'],
                        'hands-on': ['practical', 'tutorial', 'hands-on', 'exercise', 'project']
                    }
                    
                    # Check if video tags match the learning style
                    if style in style_keywords:
                        matching_tags = set(tags).intersection(style_keywords[style])
                        video_info['score'] += len(matching_tags)  # Score based on number of matching tags
                        
                    # Extra points if title or description contains style keywords
                    title_desc = metadata[i]['title'] + ' ' + metadata[i]['description']
                    title_desc = title_desc.lower()
                    
                    for keyword in style_keywords.get(style, []):
                        if keyword.lower() in title_desc:
                            video_info['score'] += 1
                            
            video_data.append(video_info)
        
        # Sort videos by score (highest first)
        sorted_videos = sorted(video_data, key=lambda x: x.get('score', 0), reverse=True)
        
        # Return the sorted list of video URLs
        return [video['url'] for video in sorted_videos]


# Updated Lesson model
class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    duration = db.Column(db.Integer, nullable=True)  # Duration in minutes
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    course = db.relationship('Course')
    module = db.relationship('Module', back_populates='lessons')
    resources = db.relationship('Resource', back_populates='lesson')


# New LearningPath model
class LearningPath(db.Model):
    __tablename__ = 'learning_path'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    career_path = db.Column(db.String(100))  # e.g., "Software Engineer", "Data Scientist"
    focus_areas = db.Column(db.String(500))  # JSON string of focus areas
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    date_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def get_focus_areas(self):
        """Return the focus areas as a list"""
        if self.focus_areas:
            return json.loads(self.focus_areas)
        return []


# Learning path and course relationship
learning_path_course = db.Table('learning_path_course',
    db.Column('learning_path_id', db.Integer, db.ForeignKey('learning_path.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True),
    db.Column('order', db.Integer, default=0)
)


# New UserProgress model
class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_position_seconds = db.Column(db.Integer, default=0)  # Video position
    is_completed = db.Column(db.Boolean, default=False)
    completion_date = db.Column(db.DateTime(timezone=True))
    date_updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'))
    
    # Add the missing relationship to User
    user = db.relationship('User', back_populates='user_progress')
    module = db.relationship('Module', backref='progress', lazy=True)


# New Schedule model
class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(100), nullable=True)  # daily, weekly, monthly
    recurrence_end_date = db.Column(db.DateTime(timezone=True), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    user = db.relationship('User', back_populates='schedules')
    course = db.relationship('Course')
    lesson = db.relationship('Lesson')


# New Resource model
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False)  # file, link, video, article, etc.
    url = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(255), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    course = db.relationship('Course')
    lesson = db.relationship('Lesson', back_populates='resources')


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True)
    date_earned = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = db.relationship('User', back_populates='achievements')
    course = db.relationship('Course')


class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    token = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User')


class EmailVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    token = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User')


# Add this new model for Chat Messages
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Define relationship with User
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))
    
    def __repr__(self):
        return f'<ChatMessage {self.id}: {self.role}>'
    
    @staticmethod
    def get_chat_history(user_id, limit=10):
        """Get the chat history for a user with the most recent messages first"""
        return ChatMessage.query.filter_by(user_id=user_id).order_by(
            ChatMessage.created_at.desc()
        ).limit(limit).all()
        
    @staticmethod
    def add_message(user_id, role, content):
        """Add a new message to the chat history"""
        message = ChatMessage(user_id=user_id, role=role, content=content)
        db.session.add(message)
        db.session.commit()
        return message
        
    @staticmethod
    def clear_chat_history(user_id):
        """Clear all chat messages for a user"""
        ChatMessage.query.filter_by(user_id=user_id).delete()
        db.session.commit()


# Add this model at the end of the file
class CSInterestSurvey(db.Model):
    __tablename__ = 'cs_interest_survey'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Interest areas on scale 1-5
    algorithms_interest = db.Column(db.Integer, nullable=True)
    data_science_interest = db.Column(db.Integer, nullable=True)
    web_development_interest = db.Column(db.Integer, nullable=True)
    mobile_development_interest = db.Column(db.Integer, nullable=True)
    cybersecurity_interest = db.Column(db.Integer, nullable=True)
    artificial_intelligence_interest = db.Column(db.Integer, nullable=True)
    game_development_interest = db.Column(db.Integer, nullable=True)
    systems_programming_interest = db.Column(db.Integer, nullable=True)
    
    # Preferred learning style
    preferred_learning_style = db.Column(db.String(50), nullable=True)  # visual, auditory, reading/writing, kinesthetic
    
    # Career goals
    career_goal = db.Column(db.String(100), nullable=True)
    
    # Additional information
    prior_experience = db.Column(db.Text, nullable=True)
    learning_time_availability = db.Column(db.String(50), nullable=True)  # less than 5 hours, 5-10 hours, 10+ hours per week
    
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f'CSInterestSurvey(user_id={self.user_id})'


# Add CSInterest which will store the user's learning preferences
class CSInterest(db.Model):
    __tablename__ = 'cs_interest'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    programming_experience = db.Column(db.String(50))
    favorite_language = db.Column(db.String(50))
    learning_style = db.Column(db.String(50))  # visual, auditory, reading, hands-on
    study_time_weekly = db.Column(db.Integer)  # hours per week
    career_interests = db.Column(db.String(200))
    date = db.Column(db.DateTime(timezone=True), default=func.now())


# Quiz model for module assessments
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(500))
    passing_score = db.Column(db.Integer, default=70)  # Percentage needed to pass
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Relationships
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'))
    questions = db.relationship('QuizQuestion', backref='quiz', cascade='all, delete-orphan')


# Quiz Question model
class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500))
    question_type = db.Column(db.String(20))  # multiple_choice, fill_in_blank, short_answer
    options = db.Column(db.Text)  # JSON string of options for multiple choice
    correct_answer = db.Column(db.String(500))
    order = db.Column(db.Integer)
    points = db.Column(db.Integer, default=1)
    
    # Relationships
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))
    
    def get_options(self):
        """Return options as a list for multiple choice questions"""
        if self.options:
            return json.loads(self.options)
        return []


# User Quiz Attempt model
class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)  # Score as a percentage
    answers = db.Column(db.Text)  # JSON string of user's answers
    is_passed = db.Column(db.Boolean, default=False)
    date_attempted = db.Column(db.DateTime(timezone=True), default=func.now())
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))


class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    theme = db.Column(db.String(20), default='light')  # 'light' or 'dark'
    preferred_video_duration = db.Column(db.Integer, default=15)  # in minutes
    notification_enabled = db.Column(db.Boolean, default=True)
    daily_goal_minutes = db.Column(db.Integer, default=30)
    language = db.Column(db.String(10), default='en')
    
    # Relationships
    user = db.relationship('User', backref='settings')