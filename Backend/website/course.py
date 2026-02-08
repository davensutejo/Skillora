import re
import json
import os
import logging
import requests
import traceback

# Configure logger
logger = logging.getLogger(__name__)

def main(course_title, career_path):
    """
    Generate course content for a given title and career path using OpenRouter API.
    
    Args:
        course_title (str): The title of the course
        career_path (str): The career path this course is for
        
    Returns:
        str: Generated course overview
    """
    # Get OpenRouter API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    # Validate API key is available and properly formatted
    if not api_key:
        logger.warning(
            "OPENROUTER_API_KEY not configured. To use AI-powered course generation, "
            "set the OPENROUTER_API_KEY environment variable. "
            "Get a free key at https://openrouter.ai/keys. Using fallback content."
        )
        return fallback_course_content(course_title, career_path)
    
    if not api_key.strip():
        logger.warning(
            "OPENROUTER_API_KEY is empty. Using fallback course content. "
            "Please configure a valid API key."
        )
        return fallback_course_content(course_title, career_path)
    
    # Generate course overview using OpenRouter API
    prompt = (
        f"Create a concise course overview about '{course_title}' for {career_path} career path. "
        "List 4-5 main chapters or modules. "
        "Use a clear list format, like 'Chapter 1: Title', 'Module A: Title', or '1. Introduction'. "
        "Put each chapter/module on a new line."
        "Focus on distinct learning units."
    )
    
    try:
        logger.info(f"Generating course content for: {course_title} ({career_path})")
        
        # Call OpenRouter API instead of using genai directly
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://skillora.com",  # Replace with your actual domain
                "X-Title": "Skillora Learning Platform",
            },
            json={
                "model": "google/gemini-2.5-pro-exp-03-25:free",  # Using Gemini through OpenRouter
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            timeout=30  # Set a reasonable timeout
        )
        
        # Process the response
        if response.status_code == 200:
            response_data = response.json()
            generated_content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if generated_content:
                logger.info(f"Successfully generated course content for: {course_title}")
                return generated_content
            else:
                logger.warning(f"Empty response content from OpenRouter API for: {course_title}")
        else:
            # Log error without exposing sensitive details
            logger.error(
                f"OpenRouter API returned status {response.status_code} for course: {course_title}. "
                "This may indicate an invalid API key, rate limiting, or server issue."
            )
            
        # Fall through to fallback if any issues
        return fallback_course_content(course_title, career_path)
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout connecting to OpenRouter API for course: {course_title}")
        return fallback_course_content(course_title, career_path)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error connecting to OpenRouter API for course: {course_title}: {type(e).__name__}")
        return fallback_course_content(course_title, career_path)
    except Exception as e:
        logger.error(f"Unexpected error generating course content for: {course_title}: {type(e).__name__}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        # Return a fallback course overview
        return fallback_course_content(course_title, career_path)

def fallback_course_content(course_title, career_path):
    """Generate fallback course content when API fails."""
    return f"""
    Course: {course_title}
    For: {career_path}
    
    1. Introduction to {course_title}
    2. Core Concepts and Fundamentals
    3. Advanced Techniques
    4. Practical Applications
    5. Projects and Implementation
    """

def parse_chapters_simple(text):
    """
    Parse chapter titles from course overview text.
    
    Args:
        text (str): The course overview text
        
    Returns:
        list: List of chapter titles
    """
    # Split the text by newlines
    lines = text.split('\n')
    
    # Look for patterns like "Chapter X:", "X.", "Module X:", etc.
    chapters = []
    
    patterns = [
        r'^\s*(?:Chapter|Module|Unit|Section)\s+\d+\s*[:-]\s*(.*?)$',  # Chapter 1: Title, Module 2 - Title
        r'^\s*\d+\.\s*(.*?)$',  # 1. Title
        r'^\s*[A-Z]\.\s*(.*?)$',  # A. Title
        r'^\s*•\s*(.*?)$',  # • Title (bullet point)
        r'^\s*\*\s*(.*?)$',  # * Title (asterisk)
        r'^\s*-\s*(.*?)$',  # - Title (dash)
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try all patterns
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                chapter_title = match.group(1).strip()
                if chapter_title and chapter_title not in chapters:
                    chapters.append(chapter_title)
                break
    
    # If no matches found, try extracting any non-empty lines that might be titles
    if not chapters:
        for line in lines:
            line = line.strip()
            if line and len(line) < 100 and ":" not in line and line not in chapters:
                chapters.append(line)
                if len(chapters) >= 5:  # Limit to 5 chapters
                    break
    
    # Fallback if still no chapters found
    if not chapters:
        chapters = [
            "Introduction and Fundamentals",
            "Core Concepts",
            "Advanced Techniques",
            "Practical Applications",
            "Projects and Implementation"
        ]
    
    return chapters[:5]  # Return at most 5 chapters 