# Skillora

> An AI-powered adaptive learning platform that personalizes education for every learner's unique needs and goals.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)

## Table of Contents

- [What Skillora Does](#what-skillora-does)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Development](#development)
- [Support & Documentation](#support--documentation)
- [Contributing](#contributing)
- [License](#license)

## What Skillora Does

Skillora is an **adaptive learning platform** that revolutionizes education through AI-powered personalization. It delivers customized learning experiences tailored to each student's pace, goals, and learning style—making education more efficient, engaging, and accessible.

Whether you're learning programming, AI, security fundamentals, or pursuing specialized career paths, Skillora adapts to you.

## Key Features

### 🎯 Personalized Learning
- **Adaptive Learning Paths**: Dynamically adjusted paths based on your career goals (Software Engineer, AI Engineer, Game Developer, Systems Engineer, etc.)
- **Career-Focused Curriculum**: Structured modules aligned with industry demands
- **Learning Analytics**: Track progress with detailed statistics and completion milestones

### 📚 Course Management
- **Diverse Course Catalog**: 20+ courses spanning multiple specializations
- **Video-Based Learning**: AI-generated animated educational videos using Manim
- **Course Enrollment**: Seamlessly browse and enroll in courses matching your goals
- **Progress Tracking**: Monitor your advancement through lessons and modules

### 👤 User Experience
- **Personalized Dashboard**: Central hub for all learning activities and progress
- **Interactive Profiles**: Showcase achievements and customize learning preferences
- **Responsive Design**: Optimized for desktop and mobile devices with smooth animations (GSAP)
- **Authentication System**: Secure user sessions with email verification and password reset

### 🤖 AI-Powered Assistance
- **Intelligent Chat Interface**: Get real-time help from Skillora AI assistant
- **Image Analysis**: Upload and share learning materials—AI analyzes images for contextual help
- **Supported Formats**: PNG, JPG, JPEG, GIF, WEBP (up to 5MB)

### 📅 Scheduling & Organization
- **Learning Calendar**: Organize study sessions and set goals
- **Learning Preferences**: Define your availability and preferred learning times
- **Achievement System**: Unlock badges and milestones

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), GSAP animations |
| **Backend** | Flask 2.3.3, Python 3.8+ |
| **Database** | SQLite (dev), SQLAlchemy ORM, Flask-Migrate |
| **Authentication** | Flask-Login, secure session management |
| **Video Generation** | Manim, manim-voiceover, GTTS (text-to-speech) |
| **AI/ML Integration** | OpenRouter API, Claude AI models |
| **Browser Automation** | Playwright |

## Getting Started

### Prerequisites

- **Python 3.8+** — [Download here](https://www.python.org/downloads/)
- **pip** (comes with Python)
- **Git** (optional, for version control)

### Installation

#### 1. Clone the Repository

```bash
# Using Git
git clone https://github.com/yourusername/skillora.git
cd skillora

# Or download and extract the ZIP file
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

#### 4. Initialize Database

```bash
python Backend/reset_db.py
```

This creates a fresh SQLite database with all required tables.

#### 5. Configure Environment (Optional)

Create a `.env` file in the project root for sensitive configuration:

```env
FLASK_ENV=development
FLASK_DEBUG=True
OPENROUTER_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

> **Note**: The application has default configuration but you can override it with `.env`

#### 6. Start the Application

```bash
# Run Flask development server
python Backend/main.py
```

The server starts on `http://127.0.0.1:9000` (or `http://localhost:9000`)

#### 7. Access Skillora

Open your browser and navigate to: **http://127.0.0.1:9000**

## Usage

### First Time Users

1. **Create Account**: Click "Sign Up" and enter your email, password, and name
2. **Verify Email**: Check your email for verification link
3. **Complete Survey**: Answer Computer Science interest survey to help personalize recommendations
4. **Choose Career Path**: Select your learning goal (e.g., Software Engineer, AI Engineer, Game Developer)
5. **Access Dashboard**: View personalized learning paths and recommended courses

### Learning on Skillora

#### Explore Courses
```
Dashboard → Courses → Browse and Enroll
```
- Filter by career path or interest area
- View course description, modules, and estimated duration
- Enroll with one click

#### Track Progress
```
Dashboard → Progress
```
- View statistics: courses enrolled, lessons completed, time invested
- Track achievement milestones and badges
- Compare progress over time

#### Use AI Tutor
```
Tutors → Chat Interface
```
- Ask questions about course content
- Upload images for visual problem-solving
- Get instant AI-powered explanations

#### Manage Profile
```
Settings → Profile
```
- Update personal information
- Configure learning preferences
- Adjust notification settings
- View account security options

### Example Workflows

**Goal: Learn Web Development**
1. Select "Software Engineer" career path
2. Follow suggested path: "Web Development Basics" → "Frontend Frameworks" → "Backend Development"
3. Complete modules progressively
4. Use AI chat for concepts you struggle with
5. Track completion on dashboard

**Goal: Get Help with Course Material**
1. While viewing course
2. Open Tutors section (bottom navigation)
3. Upload screenshot of problem
4. Ask specific question
5. AI analyzes image and provides contextual guidance

## Project Structure

```
Skillora/
├── Backend/                    # Backend application
│   ├── website/               # Main Flask application package
│   │   ├── __init__.py       # Flask app factory & configuration
│   │   ├── auth.py           # Authentication routes (login, signup, password reset)
│   │   ├── views.py          # Main application routes & views
│   │   ├── models.py         # SQLAlchemy database models
│   │   ├── db_utils.py       # Database utility functions
│   │   ├── config.py         # AI/API configuration
│   │   ├── manim.py          # Video generation utilities
│   │   ├── manimconfig.py    # Manim animation settings
│   │   ├── api_utils.py      # External API integrations
│   │   │
│   │   ├── static/           # Frontend static files
│   │   │   ├── css/          # Stylesheets (login, dashboard, themes)
│   │   │   ├── js/           # JavaScript (interactions, animations)
│   │   │   ├── images/       # UI images and assets
│   │   │   ├── courses/      # Course-related static files
│   │   │   │   ├── scripts/  # Manim animation scripts
│   │   │   │   ├── videos/   # Generated course videos
│   │   │   │   └── media/    # Course media assets
│   │   │   └── uploads/      # User-uploaded content
│   │   │       └── chat_images/  # AI chat image uploads
│   │   │
│   │   └── templates/        # HTML templates
│   │       ├── base.html     # Base template with navbar
│   │       ├── index.html    # Home page
│   │       ├── login.html    # Login page
│   │       ├── sign_up.html  # Registration page
│   │       ├── learning_interface.html  # Course learning interface
│   │       ├── learning_path.html       # Personalized learning paths
│   │       ├── progress.html  # Progress dashboard
│   │       ├── tutors.html    # AI chat interface
│   │       ├── profile.html   # User profile management
│   │       ├── my_courses.html # Enrolled courses
│   │       └── settings.html  # Account settings
│   │
│   ├── migrations/           # Database migration scripts (Alembic)
│   ├── logs/                # Application logs
│   ├── instance/            # Instance folder (database.db location)
│   ├── main.py             # Flask application entry point
│   ├── reset_db.py         # Database initialization script
│   ├── check_db.py         # Database inspection utility
│   └── migrate_db.py       # Database migration utility
│
├── requirements.txt        # Python dependencies
├── LICENSE                # MIT License
└── README.md             # This file
```

### Key Directories Explained

- **Backend/website/static/courses/scripts/**: Contains auto-generated Manim scripts for animation-based course videos
- **Backend/website/static/uploads/chat_images/**: Stores images uploaded by users in AI chat
- **Backend/migrations/**: Alembic migration history for database schema changes
- **Backend/instance/**: SQLite database file (`database.db`) stored here

## Development

### Database Management

```bash
# Create fresh database
python Backend/reset_db.py

# Check database status
python Backend/check_db.py

# Apply migrations
python Backend/migrate_db.py
```

### Key Database Models

- **User**: Student accounts with profile info, preferences, and settings
- **Course**: Curriculum content with metadata and learning objectives
- **Lesson**: Individual units within courses
- **UserProgress**: Tracks completion status for courses and lessons
- **Achievement**: Badges and milestones earned by users
- **LearningPath**: Personalized sequences of courses per career path

### Extending the Platform

**Adding a New Course:**
1. Create course entry in database via admin interface
2. Structure lessons and modules
3. Generate Manim animation script (optional)
4. Upload course media to `static/courses/videos/`

**Customizing Learning Paths:**
- Edit career path definitions in [Backend/website/views.py](Backend/website/views.py#L467) (search `@views.route('/learning-path')`)
- Add new modules or reorder course sequences
- Test with different user profiles

**Enhancing AI Features:**
- Configure AI model in [Backend/website/config.py](Backend/website/config.py)
- Update system prompts for different tutoring scenarios
- Adjust API parameters (temperature, max_tokens)

### Running in Debug Mode

```bash
# Development with auto-reload
python Backend/main.py

# Access debug panel at http://localhost:9000/__debug__
```

## Support & Documentation

### Getting Help

- **Documentation**: Review template files for UI implementation
- **Database Help**: See [Backend/models.py](Backend/website/models.py) for data structure details
- **API Integration**: Check [Backend/api_utils.py](Backend/website/api_utils.py) for external API patterns
- **Video Generation**: See [Backend/manim.py](Backend/website/manim.py) for animation examples

### Common Issues

**Issue**: Database not initialized
```bash
Solution: python Backend/reset_db.py
```

**Issue**: Port 9000 already in use
```bash
Solution: python Backend/main.py --port=8000
```

**Issue**: Playwright browser not installed
```bash
Solution: playwright install
```

**Issue**: AI chat not responding
- Check OpenRouter API key in `.env`
- Verify internet connection
- Review logs in `Backend/logs/app.log`

### Troubleshooting Resources

- Review [TODO.md](TODO.md) for roadmap and known issues
- Check Flask error logs: `Backend/logs/app.log`
- Test database connection: `python Backend/check_db.py`

## Contributing

We welcome contributions! Here's how to get started:

### Development Workflow

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/your-username/skillora.git`
3. **Create** a feature branch: `git checkout -b feature/your-feature-name`
4. **Make** your changes with clear commits
5. **Test** thoroughly in development environment
6. **Push** to your fork: `git push origin feature/your-feature-name`
7. **Create** a Pull Request with description of changes

### Code Guidelines

- **Python**: Follow PEP 8 style guide
- **JavaScript**: Use clear variable names and comments
- **HTML/CSS**: Keep templates DRY, organize styles logically
- **Database**: Update models and create migrations for schema changes

### What We Need Help With

See [TODO.md](TODO.md) for features in development:
- Database model enhancements
- Course management improvements
- Learning path optimization
- Analytics and progress tracking features
- Mobile responsiveness improvements

### Reporting Issues

Please include:
- Steps to reproduce the issue
- Expected vs. actual behavior
- Python version and OS
- Error logs from `Backend/logs/app.log`

## Project Roadmap

Current focus areas (see [TODO.md](TODO.md)):
- ✅ Core authentication & user management
- ✅ Course enrollment & basic progress tracking
- ✅ AI-powered chat interface with image support
- 🔄 Advanced analytics and learning metrics
- 🔄 Automated course video generation (Manim integration)
- 🔄 Mobile app (iOS/Android)
- 🔄 Gamification & achievement system
- 🔄 Tutor session booking

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for full details.

**Copyright © 2023 Skillora**

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/) and [SQLAlchemy](https://www.sqlalchemy.org/)
- AI powered by [OpenRouter](https://openrouter.ai/) and Claude
- Animations created with [Manim](https://www.manim.community/)
- Text-to-speech by [GTTS](https://gtts.readthedocs.io/)

---

**Questions?** Feel free to open an issue on GitHub or check our documentation.

**Ready to learn?** Sign up at [http://localhost:9000](http://localhost:9000) and start your personalized learning journey! 