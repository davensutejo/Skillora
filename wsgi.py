"""
WSGI entry point for Vercel deployment.
This file allows Vercel to find and run the Flask application.
"""
import sys
import os

# Add the Backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))

# Import and initialize the Flask app
from website import create_app

# Create the app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=False, port=8000)
