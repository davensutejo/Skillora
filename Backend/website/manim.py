import json
import os
import subprocess
import time
from . import manimconfig
import requests
import logging
from typing import Dict, List, Optional, Union, Any
from tqdm import tqdm  # Add progress bar support
import re
from collections import deque
from datetime import datetime, timedelta
import shutil
from flask import url_for

# --- Configure Logging ---
import os
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manim_generator.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Manim generator initialized")  # Add this line to test logging

# --- Setup Rate Limiting ---
# This helps prevent hitting API rate limits
request_timestamps = deque(maxlen=manimconfig.RATE_LIMIT_REQUESTS if hasattr(manimconfig, 'RATE_LIMIT_REQUESTS') else 10)
rate_limit_window = manimconfig.RATE_LIMIT_WINDOW if hasattr(manimconfig, 'RATE_LIMIT_WINDOW') else 60  # seconds

def wait_for_rate_limit():
    """
    Implements a simple rate limiting mechanism to prevent
    hitting API provider quotas.
    """
    if not request_timestamps:
        # No previous requests, no need to wait
        return
    
    # If we've made the maximum number of requests in the window
    if len(request_timestamps) >= request_timestamps.maxlen:
        # Calculate how long we need to wait
        oldest_timestamp = request_timestamps[0]
        time_since_oldest = (datetime.now() - oldest_timestamp).total_seconds()
        
        if time_since_oldest < rate_limit_window:
            wait_time = rate_limit_window - time_since_oldest + 1  # Add 1 second buffer
            logger.info(f"Rate limiting: waiting {wait_time:.1f} seconds before next request")
            time.sleep(wait_time)
    
    # Add a small delay between requests regardless
    # This helps spread out requests even if we haven't hit our limit
    time.sleep(1)
    
    # Record this request
    request_timestamps.append(datetime.now())

# --- Configure OpenRouter API ---
try:
    # Get API configuration from config.py
    api_key = manimconfig.OPENROUTER_API_KEY
    api_base_url = manimconfig.OPENROUTER_API_BASE_URL
    default_model = manimconfig.DEFAULT_MODEL
    default_max_tokens = manimconfig.DEFAULT_MAX_TOKENS
    default_temperature = manimconfig.DEFAULT_TEMPERATURE
    request_timeout = manimconfig.REQUEST_TIMEOUT
    max_retries = manimconfig.MAX_RETRIES
    manim_packages = manimconfig.MANIM_PACKAGES if hasattr(manimconfig, 'MANIM_PACKAGES') else []
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in config.py")

except ValueError as e:
    logger.error(f"API Key Error: {e}")
    logger.error("Please set the OPENROUTER_API_KEY in config.py.")
    exit(1)
except Exception as e:
    logger.error(f"Error configuring OpenRouter API: {e}")
    exit(1)

# --- API Call Functions ---

def call_openrouter_api(prompt: str, system_prompt: str = None) -> str:
    """
    Calls the OpenRouter API with the given prompt.

    Args:
        prompt: The text prompt for the model.
        system_prompt: Optional system prompt to guide the model.

    Returns:
        The generated text content, or an empty string if generation fails or is blocked.

    Raises:
        Exception: If a critical API error occurs.
    """
    try:
        # Log the API key and configuration for debugging
        logger.info(f"API Key (first 5 chars): {api_key[:5]}...")
        logger.info(f"API URL: {api_base_url}")
        logger.info(f"Using model: {default_model}")
        
        # Apply rate limiting to avoid hitting provider quotas
        wait_for_rate_limit()
        
        logger.info(f"Calling OpenRouter API... (Prompt length: {len(prompt)} chars)")
        
        # Prepare the API request - SIMPLIFY HEADERS to reduce potential issues
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build messages array - USING SIMPLER FORMAT
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build a basic payload without extra parameters that might cause issues
        payload = {
            "model": default_model,
            "messages": messages
        }
        
        # Log the actual request being sent
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
        
        # Make the API call with retry logic
        response = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Request attempt {attempt+1}/{max_retries}")
                
                # IMPORTANT: Use direct URL formatting for the API endpoint 
                # as some interfaces have issues with f-strings in URLs
                api_endpoint = api_base_url + "/chat/completions"
                logger.info(f"Full API endpoint: {api_endpoint}")
                
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=request_timeout
                )
                
                # Log raw response for debugging
                if response.status_code != 200:
                    logger.error(f"API Error: Status code {response.status_code}")
                    logger.error(f"Response content: {response.text}")
                    
                    # Special handling for common error codes
                    if response.status_code == 401:
                        logger.error("Authentication error - check your API key")
                    elif response.status_code == 400:
                        logger.error("Bad request - check your request format")
                    elif response.status_code == 404:
                        logger.error("Not found - check your API endpoint")
                    elif response.status_code == 429:
                        logger.error("Rate limit exceeded - waiting longer before retry")
                        wait_time = 30 + (30 * attempt)  # Longer wait for rate limits
                        logger.info(f"Waiting {wait_time} seconds before retry due to rate limit...")
                        time.sleep(wait_time)
                        continue
                    
                response.raise_for_status()
                break  # Exit the retry loop if successful
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:  # Don't wait after the last attempt
                    logger.warning(f"API request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed. Last error: {str(e)}")
                    raise  # Re-raise the exception after all retry attempts
        
        # Parse the response
        if response and response.status_code == 200:
            # Log the entire raw response as debug info
            try:
                response_text = response.text
                logger.debug(f"Raw API response: {response_text}")
                response_json = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return ""
            
            # Flexible extraction of content from various response formats
            content = None
            
            # Standard OpenAI format
            if "choices" in response_json and len(response_json["choices"]) > 0:
                if "message" in response_json["choices"][0] and "content" in response_json["choices"][0]["message"]:
                    content = response_json["choices"][0]["message"]["content"]
                    logger.info("Retrieved content from standard format")
                    return content
                # Alternative format
                elif "content" in response_json["choices"][0]:
                    content = response_json["choices"][0]["content"]
                    logger.info("Retrieved content from alternative format")
                    return content
            # For direct response format sometimes used by certain models
            elif "content" in response_json:
                content = response_json["content"]
                logger.info("Retrieved content from direct format")
                return content
            # For Anthropic/Claude-style responses
            elif "response" in response_json:
                content = response_json["response"]
                logger.info("Retrieved content from response field")
                return content
            # Extract from nested structure if needed
            elif "result" in response_json:
                if isinstance(response_json["result"], dict) and "content" in response_json["result"]:
                    content = response_json["result"]["content"]
                    logger.info("Retrieved content from nested result structure")
                    return content
                elif isinstance(response_json["result"], str):
                    content = response_json["result"]
                    logger.info("Retrieved content from result string")
                    return content
            
            if content:
                # Clean up the content - remove any leading/trailing quotes or whitespace
                if isinstance(content, str):
                    content = content.strip().strip('"\'')
                    logger.info(f"API call successful, retrieved {len(content)} chars")
                    return content
                else:
                    logger.error(f"Content is not a string: {type(content)}")
                    return ""
            else:
                # Last attempt to extract anything useful from the response
                logger.error("Could not find content in standard locations of the response")
                logger.error(f"Response structure: {json.dumps(response_json, indent=2)}")
                
                # Desperate attempt to find any text content
                if isinstance(response_json, dict):
                    for key, value in response_json.items():
                        if isinstance(value, str) and len(value) > 50:  # Somewhat arbitrary length check
                            logger.warning(f"Found potential content in non-standard field '{key}'")
                            return value
                
                return ""
        else:
            error_msg = f"API response status code {response.status_code if response else 'None'}"
            logger.error(error_msg)
            if response:
                logger.error(f"Response content: {response.text}")
            return ""

    except Exception as e:
        logger.error(f"Error during OpenRouter API call: {str(e)}")
        # Get more information about the error
        if 'response' in locals() and response is not None:
            logger.error(f"Response status: {response.status_code}")
            logger.error(f"Response content: {response.text}")
        return ""  # Return empty string instead of raising to allow fallback mechanisms to work


def get_course_overview(prompt: str) -> Dict[str, Any]:
    """
    Uses the OpenRouter API to get a course overview structured as JSON.

    Args:
        prompt: The user's topic (e.g., "Introduction to Python Programming").

    Returns:
        A dictionary representing the course structure, or an empty dict on failure.
    """
    # Use a much simpler system prompt
    system_prompt = "You are a helpful assistant who creates course outlines in JSON format."
    
    # Use a simpler prompt with a clear example
    api_prompt = (
        f"Create a course outline for the topic: {prompt}\n\n"
        "Format your response as a JSON object with the following structure:\n"
        "{\n"
        '  "title": "The Course Title",\n'
        '  "chapters": [\n'
        '    {\n'
        '      "title": "Chapter 1: Introduction",\n'
        '      "id": "ch1_intro",\n'
        '      "key_concepts": ["Concept 1", "Concept 2", "Concept 3"]\n'
        '    },\n'
        '    {\n'
        '      "title": "Chapter 2: Basic Concepts",\n'
        '      "id": "ch2_basics",\n'
        '      "key_concepts": ["Concept 1", "Concept 2", "Concept 3"]\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Include 4-6 chapters. Each chapter should have a title, a short id (using lowercase letters, numbers, and underscores), "
        "and 3-5 key concepts. The id should be filesystem-safe (no spaces or special characters).\n\n"
        "Respond with ONLY the JSON."
    )
    
    try:
        response_text = call_openrouter_api(api_prompt, system_prompt)
        if not response_text:
            logger.error("Received empty response from API for course overview.")
            return {}

        # Clean potential markdown code fences and surrounding whitespace
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.removeprefix("```json").removesuffix("```").strip()
        elif response_text.startswith("```"):
            response_text = response_text.removeprefix("```").removesuffix("```").strip()

        # Try to find JSON content within the response if it contains other text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        if json_start >= 0 and json_end > json_start:
            potential_json = response_text[json_start:json_end+1]
            try:
                # See if we can parse just this part
                parsed_json = json.loads(potential_json)
                logger.info("Extracted JSON from within response")
                response_text = potential_json
            except json.JSONDecodeError:
                # If not, stick with the original text
                pass

        # Attempt to parse the JSON response
        try:
            course_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode API response into JSON. Details: {e}")
            logger.error(f"Received text was:\n---\n{response_text}\n---")
            
            # Try a last-resort approach: manually construct a basic structure
            logger.info("Attempting to extract course structure manually")
            title_match = re.search(r'"title"\s*:\s*"([^"]*)"', response_text)
            title = title_match.group(1) if title_match else prompt
            
            # Construct a basic course
            fallback_course = {
                "title": title,
                "chapters": [
                    {"title": "Chapter 1: Introduction", "id": "ch1_intro", 
                     "key_concepts": ["Basic Concepts", "Fundamentals", "Overview"]},
                    {"title": "Chapter 2: Core Concepts", "id": "ch2_core", 
                     "key_concepts": ["Key Principles", "Main Ideas", "Applications"]},
                    {"title": "Chapter 3: Advanced Topics", "id": "ch3_advanced", 
                     "key_concepts": ["Advanced Techniques", "Complex Examples", "Practical Usage"]}
                ]
            }
            logger.warning("Using fallback course structure")
            return fallback_course

        # Basic validation
        if isinstance(course_data, dict) and "title" in course_data and "chapters" in course_data:
            if isinstance(course_data["chapters"], list) and len(course_data["chapters"]) > 0:
                # Basic cleanup and validation of chapters
                valid_chapters = []
                for i, ch in enumerate(course_data["chapters"]):
                    if isinstance(ch, dict) and "title" in ch:
                        # Ensure id exists and is valid
                        if not ch.get("id") or not isinstance(ch.get("id"), str):
                            ch["id"] = f"ch{i+1}_{''.join(c for c in ch['title'].lower() if c.isalnum() or c == '_')[:10]}"
                            
                        # Ensure key_concepts exists
                        if not ch.get("key_concepts") or not isinstance(ch.get("key_concepts"), list):
                            ch["key_concepts"] = [f"Concept {j+1}" for j in range(3)]
                            
                        valid_chapters.append(ch)
                
                if valid_chapters:
                    course_data["chapters"] = valid_chapters
                    logger.info(f"Course overview structure is valid with {len(valid_chapters)} chapters")
                    return course_data
                else:
                    logger.error("No valid chapters found in the response")
            else:
                logger.error(f"'chapters' field is not a valid list. Found: {type(course_data.get('chapters'))}")
        else:
            logger.error("Parsed JSON does not match expected structure (missing 'title' or 'chapters')")

        # If we got here, the structure is invalid - create a fallback
        logger.warning("Using fallback course structure due to invalid response")
        fallback_course = {
            "title": prompt,
            "chapters": [
                {"title": "Chapter 1: Introduction", "id": "ch1_intro", 
                 "key_concepts": ["Basic Concepts", "Fundamentals", "Overview"]},
                {"title": "Chapter 2: Core Concepts", "id": "ch2_core", 
                 "key_concepts": ["Key Principles", "Main Ideas", "Applications"]},
                {"title": "Chapter 3: Advanced Topics", "id": "ch3_advanced", 
                 "key_concepts": ["Advanced Techniques", "Complex Examples", "Practical Usage"]}
            ]
        }
        return fallback_course
        
    except Exception as e:
        logger.error(f"Error getting or parsing course overview: {e}")
        # Return a minimal fallback course instead of empty
        return {
            "title": prompt,
            "chapters": [
                {"title": "Chapter 1: Introduction", "id": "ch1_intro", 
                 "key_concepts": ["Basic Concepts", "Fundamentals", "Overview"]},
                {"title": "Chapter 2: Core Concepts", "id": "ch2_core", 
                 "key_concepts": ["Key Principles", "Main Ideas", "Applications"]},
                {"title": "Chapter 3: Advanced Topics", "id": "ch3_advanced", 
                 "key_concepts": ["Advanced Techniques", "Complex Examples", "Practical Usage"]}
            ]
        }


def create_fallback_script(chapter_title: str, key_concepts: List[str] = None) -> str:
    """
    Creates a basic fallback script when the API call fails.
    
    Args:
        chapter_title: The title of the chapter.
        key_concepts: Optional list of key concepts to include.
        
    Returns:
        A basic but functional script.
    """
    # Ensure we have some concepts to work with
    if not key_concepts or not isinstance(key_concepts, list) or len(key_concepts) == 0:
        key_concepts = ["Basic concept 1", "Basic concept 2", "Basic concept 3"]
    
    # Create a template script
    script = f"""[INTRO]
Welcome to {chapter_title}. In this video, we will explore several key concepts and understand their significance.
(Visual: Show a title card with '{chapter_title}')

[CONCEPT 1]
Let's begin with our first concept: {key_concepts[0]}.
(Visual: Display text '{key_concepts[0]}' with a circle underneath)
This concept forms the foundation of our understanding of this topic.
(Visual: Transform the circle into a square)

[CONCEPT 2]
Now, let's move on to our second concept: {key_concepts[min(1, len(key_concepts)-1)]}.
(Visual: Create a new text element for this concept with an arrow pointing to it)
This builds upon our first concept and extends our knowledge.
(Visual: Show a connection between the first and second concepts)

"""

    # Add more concepts if available
    if len(key_concepts) > 2:
        script += f"""[CONCEPT 3]
Our third key concept is: {key_concepts[2]}.
(Visual: Add a new element showing '{key_concepts[2]}')
This concept completes our fundamental understanding of the topic.
(Visual: Connect all concepts in a triangle or network)

"""

    # Add example and summary sections
    script += f"""[EXAMPLE]
Let's see a practical example of how these concepts work together.
(Visual: Demonstrate a simple application with animated elements)
Notice how each concept contributes to the overall system.

[SUMMARY]
To summarize what we've learned in this chapter:
(Visual: List each key concept with a check mark appearing next to each)
- {key_concepts[0]}
- {key_concepts[min(1, len(key_concepts)-1)]}
"""

    # Add the third concept to summary if available
    if len(key_concepts) > 2:
        script += f"- {key_concepts[2]}\n"
    
    script += """
Thank you for watching, and we'll see you in the next chapter.
(Visual: Fade out all elements)
"""
    
    return script


def get_video_script(chapter_title: str, course_title: str, key_concepts: List[str] = None) -> str:
    """
    Uses the OpenRouter API to get a ~5-minute video script for a chapter.
    Falls back to a template script if API fails.

    Args:
        chapter_title: The title of the chapter.
        course_title: The title of the overall course for context.
        key_concepts: Optional list of key concepts to cover.

    Returns:
        A string containing the video script, or a fallback script if generation fails.
    """
    # Much simpler system prompt
    system_prompt = "You are a helpful assistant who creates educational scripts for videos."
    
    # Ensure we have key concepts to work with
    if not key_concepts or not isinstance(key_concepts, list) or len(key_concepts) == 0:
        key_concepts = ["Basic concept 1", "Basic concept 2", "Basic concept 3"]
    
    # Build a list of concepts to include
    concepts_text = "\n".join([f"- {concept}" for concept in key_concepts[:5]])
    
    # Simpler, clearer prompt focused on what we need
    api_prompt = (
        f"Write a script for a 5 minute educational video ( 100wpm == around 700 words) about '{chapter_title}' for the course '{course_title}'.\n\n"
        f"Include these key concepts:\n{concepts_text}\n\n"
        "FORMAT REQUIREMENTS:\n"
        "1. Use these section headers:\n"
        "   [INTRO]\n"
        "   [CONCEPT 1]\n"
        "   [CONCEPT 2]\n"
        "   [EXAMPLE]\n"
        "   [SUMMARY]\n\n"
        "2. Include visual directions in parentheses like this:\n"
        "   (Visual: Show a title card with 'Key Concept')\n"
        "   (Visual: Draw a circle that transforms into a square)\n\n"
        "Keep the language clear, educational, and engaging. Focus on explaining the concepts clearly."
    )
    
    try:
        # Try the API call
        script_content = call_openrouter_api(api_prompt, system_prompt)
        
        # Check if we got a valid response
        if script_content and len(script_content) > 200:  # Reasonable minimum length for a script
            logger.info(f"Successfully generated script for '{chapter_title}' ({len(script_content)} chars)")
            return script_content
        else:
            logger.warning(f"API returned empty or too short script for '{chapter_title}'. Using fallback script.")
            return create_fallback_script(chapter_title, key_concepts)
            
    except Exception as e:
        logger.error(f"Error getting video script for '{chapter_title}': {e}")
        logger.info(f"Using fallback script template for '{chapter_title}'")
        return create_fallback_script(chapter_title, key_concepts)


def get_scene_class_name(chapter_title: str) -> str:
    """
    Sanitizes a chapter title to create a valid Python class name for a Manim scene.

    Args:
        chapter_title: The title of the chapter.

    Returns:
        A sanitized string suitable for use as a Python class name.
    """
    sanitized_title = ''.join(c for c in chapter_title if c.isalnum() or c == '_')
    sanitized_title = sanitized_title.strip('_')
    if not sanitized_title: 
        sanitized_title = "DefaultChapter"
    # Ensure it starts with a letter (common requirement for Python class names)
    if not sanitized_title[0].isalpha(): 
        sanitized_title = "C_" + sanitized_title
    # Return the CamelCase class name
    return f"{sanitized_title}Scene"


def generate_manim_package_imports(script_content: str) -> str:
    """
    Analyze the script content and generate imports for appropriate Manim packages.
    Ensures all available packages defined in manimconfig.MANIM_PACKAGES are utilized when relevant.
    
    Args:
        script_content: The content of the script to analyze
        
    Returns:
        String containing import statements for Manim and extensions
    """
    
    # Always include the base Manim import
    packages = ["from manim import *"]
    
    # Get all available Manim packages from config
    available_packages = []
    try:
        from . import manimconfig
        if hasattr(manimconfig, 'MANIM_PACKAGES'):
            available_packages = manimconfig.MANIM_PACKAGES
            logger.info(f"Found {len(available_packages)} Manim packages in configuration")
        else:
            logger.warning("No MANIM_PACKAGES found in manimconfig")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Error accessing manimconfig.MANIM_PACKAGES: {str(e)}")
        # Fallback to hardcoded list
        available_packages = [
            "manim-algorithm",
            "manim-editor",
            "manim-revealjs",
            "manim-speech",
            "manim-neural-network",
            "manim-ml",
            "manim-fonts",
            "manim-data-structures",
            "manim-code-blocks"
        ]
    
    # Always include manim-editor and manim-speech for all scripts
    # These are critical for the course generation functionality
    packages.append("from manim_editor import PresentationSectionType")
    packages.append("from manim_voiceover import VoiceoverScene")
    packages.append("from manim_voiceover.services.gtts import GTTSService")
    
    # Check lower-cased content for topic detection
    script_lower = script_content.lower()
    
    # Map of package names to topic keywords/patterns
    topic_patterns = {
        "manim-algorithm": ["algorithm", "sort", "search", "datastructure", "data structure"],
        "manim-revealjs": ["presentation", "slides", "reveal"],
        "manim-voiceover": ["voice", "speak", "narration", "audio"],
        "manim-neural-network": ["neural", "network", "machine learning", "deep learning", "ai"],
        "manim-ml": ["machine learning", "ml", "classifier", "regression", "predict"],
        "manim-fonts": ["font", "text", "typography"],
        "manim-data-structures": ["array", "list", "queue", "stack", "tree", "graph", "hashmap", "hash map", "hash table"],
        "manim-code-blocks": ["code", "program", "function", "algorithm"]
    }
    
    # Process other available packages based on script content
    for package in available_packages:
        # Skip packages we've already added
        if package in ["manim-editor", "manim-voiceover"]:
            continue
            
        # Generate appropriate import based on the package name
        import_line = None
        package_patterns = topic_patterns.get(package, [package.replace("manim-", "")])
        
        # Check if any pattern for this package is in the script
        if any(pattern in script_lower for pattern in package_patterns):
            # Generate import statement based on the package name
            if package == "manim-algorithm":
                import_line = "from manim_algorithms import *"
            elif package == "manim-speech":
                import_line = "from manim_speech import install_speech"
            elif package == "manim-revealjs":
                import_line = "from manim_revealjs import PresentationScene"
            elif package == "manim-neural-network":
                import_line = "from manim_neural_network import NeuralNetworkMobject"
            elif package == "manim-ml":
                import_line = "from manim_ml import *"
            elif package == "manim-fonts":
                import_line = "from manim_fonts import *"
            elif package == "manim-data-structures":
                import_line = "from manim_data_structures import Array, LinkedList, Stack, Queue, BinaryTree, Graph"
            elif package == "manim-code-blocks":
                import_line = "from manim_code_blocks import Code"
            else:
                # Generic import for other packages
                clean_name = package.replace("-", "_")
                import_line = f"from {clean_name} import *"
            
            if import_line and import_line not in packages:
                packages.append(import_line)
    
    # Add error handling for imports in case packages aren't installed
    for i in range(1, len(packages)):
        # Extract the module name from the import statement
        import_parts = packages[i].split()
        if len(import_parts) >= 2 and import_parts[0] == "from":
            module_name = import_parts[1]
            # Replace the direct import with a try-except block
            packages[i] = f"try:\n    {packages[i]}\nexcept ImportError:\n    # {module_name} package not installed\n    pass"
    
    # Add numpy and other common math/science libraries
    packages.append("import numpy as np")
    
    return "\n".join(packages)


def create_fallback_manim_code(chapter_title: str, script: str, key_concepts: List[str] = None) -> str:
    """
    Creates a basic but functional Manim animation code when the API call fails.
    
    Args:
        chapter_title: The title of the chapter.
        script: The script content (to extract visual cues if possible).
        key_concepts: Optional list of key concepts to visualize.
        
    Returns:
        Basic Manim code that will render successfully.
    """
    target_scene_class_name = get_scene_class_name(chapter_title)
    
    # Extract concepts from the script or use provided ones
    concepts = []
    
    # If key_concepts is provided and valid, use it
    if key_concepts and isinstance(key_concepts, list) and len(key_concepts) > 0:
        concepts = key_concepts[:3]  # Use up to 3 concepts
    
    # If we still need concepts, try to extract them from the script
    if len(concepts) < 3 and script:
        import re
        # Look for phrases that might be concepts in the script
        concept_patterns = [
            r'\[CONCEPT[^\]]*\]\s*(.*?)[\n\r]',  # Match [CONCEPT] headers
            r'concept[s]?:?\s+(.*?)[\n\r\.]',    # Match "concept: something"
            r'key point[s]?:?\s+(.*?)[\n\r\.]',  # Match "key points: something"
        ]
        
        for pattern in concept_patterns:
            matches = re.findall(pattern, script, re.IGNORECASE)
            for match in matches:
                # Clean up the match and add if it's substantial
                clean_match = match.strip()
                if clean_match and len(clean_match) > 3 and clean_match not in concepts:
                    concepts.append(clean_match)
                    if len(concepts) >= 3:
                        break
            if len(concepts) >= 3:
                break
    
    # If we still don't have enough concepts, add some generic ones
    while len(concepts) < 3:
        concepts.append(f"Concept {len(concepts)+1}")
    
    # Create the Manim code
    manim_code = f"""from manim import *

class {target_scene_class_name}(Scene):
    def construct(self):
        # Introduction
        title = Text("{chapter_title}", font_size=48).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # First concept
        concept1 = Text("{concepts[0]}", font_size=36).next_to(title, DOWN, buff=0.7)
        shape1 = Circle(radius=0.5, color=WHITE, fill_opacity=0.3).next_to(concept1, DOWN, buff=0.5)
        
        self.play(FadeIn(concept1), Create(shape1))
        self.wait(1.5)
        
        # Second concept
        concept2 = Text("{concepts[1]}", font_size=36)
        concept2.next_to(shape1, DOWN, buff=1.2)
        shape2 = Square(side_length=1.0, color=BLUE).next_to(concept2, DOWN, buff=0.5)
        
        self.play(FadeIn(concept2), Create(shape2))
        self.wait(1.5)
        
        # Connect concepts with an arrow
        arrow = Arrow(shape1.get_bottom(), shape2.get_top(), buff=0.2, color=YELLOW)
        connection_text = Text("leads to", font_size=24).next_to(arrow, RIGHT, buff=0.2)
        
        self.play(GrowArrow(arrow), Write(connection_text))
        self.wait(1)
        
        # Third concept (transform the second shape)
        concept3 = Text("{concepts[2]}", font_size=36).to_edge(RIGHT).shift(UP * 0.5)
        
        self.play(
            Transform(shape2, Circle(radius=0.7, color=GREEN).move_to(shape2.get_center())),
            Transform(concept2, concept3)
        )
        self.wait(1.5)
        
        # Group and fade out middle elements
        middle_elements = VGroup(shape1, arrow, connection_text, shape2)
        self.play(FadeOut(middle_elements))
        self.wait(0.5)
        
        # Summary
        summary_title = Text("Summary", font_size=40).next_to(title, DOWN, buff=0.7)
        self.play(Write(summary_title))
        
        # Create bullet points
        bullet1 = Text("• " + "{concepts[0]}", font_size=28).next_to(summary_title, DOWN, buff=0.5, aligned_edge=LEFT).shift(RIGHT * 0.5)
        bullet2 = Text("• " + "{concepts[1]}", font_size=28).next_to(bullet1, DOWN, buff=0.3, aligned_edge=LEFT)
        bullet3 = Text("• " + "{concepts[2]}", font_size=28).next_to(bullet2, DOWN, buff=0.3, aligned_edge=LEFT)
        
        self.play(Write(bullet1))
        self.wait(0.3)
        self.play(Write(bullet2))
        self.wait(0.3)
        self.play(Write(bullet3))
        self.wait(2)
        
        # Fade everything out at the end
        self.play(FadeOut(VGroup(title, summary_title, bullet1, bullet2, bullet3, concept1, concept2)))
        self.wait(1)
"""
    
    return manim_code


def check_manim_code(code_content: str, chapter_title: str) -> Dict[str, Any]:
    """
    Checks if the Manim code is valid by attempting to parse it.
    
    Args:
        code_content: The Manim code to check.
        chapter_title: The title of the chapter for reference.
        
    Returns:
        Dict with 'is_valid', 'errors', and 'error_type' keys.
    """
    import tempfile
    import ast
    
    result = {
        'is_valid': False,
        'errors': [],
        'error_type': None
    }
    
    # First, check for syntax errors by parsing the code
    try:
        ast.parse(code_content)
        result['is_valid'] = True
    except SyntaxError as e:
        result['is_valid'] = False
        result['errors'].append(f"Syntax error on line {e.lineno}: {e.msg}")
        result['error_type'] = 'syntax'
        return result
    
    # If syntax is good, check for import errors and other issues
    # by attempting to run a syntax check and import verification
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
            temp_file = f.name
            f.write(code_content)
        
        # Run a simple Python check on the file
        result_check = subprocess.run(
            ["python", "-m", "py_compile", temp_file],
            capture_output=True,
            text=True,
            timeout=10  # Set a timeout to avoid hanging
        )
        
        if result_check.returncode != 0:
            result['is_valid'] = False
            result['errors'].append(f"Compilation error: {result_check.stderr}")
            result['error_type'] = 'imports'
            return result
            
        # Code appears valid
        result['is_valid'] = True
        return result
        
    except Exception as e:
        result['is_valid'] = False
        result['errors'].append(f"Error checking code: {str(e)}")
        result['error_type'] = 'unknown'
        return result
    finally:
        # Clean up the temporary file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass


def get_error_correction_prompt(code: str, errors: List[str]) -> str:
    """
    Creates a prompt to fix specific errors in the Manim code.
    
    Args:
        code: The code that contains errors.
        errors: List of error messages.
        
    Returns:
        A prompt string for error correction.
    """
    error_text = "\n".join(errors)
    
    return (
        "The Manim code generated has the following errors:\n\n"
        f"{error_text}\n\n"
        "Here's the code with errors:\n\n"
        f"{code}\n\n"
        "Please fix ONLY these specific errors and return the corrected code. "
        "Maintain the same structure and functionality, but fix syntax errors, "
        "invalid imports, or incorrect class references. "
        "Return ONLY the corrected Python code with no explanations."
    )


def get_manim_code(script: str, chapter_title: str, key_concepts: List[str] = None) -> str:
    """
    Uses the OpenRouter API to generate Manim code based on a script,
    guided by a working example and incorporating appropriate Manim packages.
    Falls back to template code if the API call fails.

    Args:
        script: The video script generated previously (including visual cues).
        chapter_title: The title of the chapter.
        key_concepts: Optional list of key concepts to visualize.

    Returns:
        A string containing Python code intended for Manim.
    """
    # Get the target scene class name using the helper function
    target_scene_class_name = get_scene_class_name(chapter_title)
    
    # Generate appropriate imports based on script content
    suggested_imports = generate_manim_package_imports(script)

    # --- START OF PRESET MANIM EXAMPLE (as string) ---
    # This example guides the AI on structure, allowed elements, and complexity.
    manim_example_code = """
# --- START OF PRESET MANIM EXAMPLE ---
from manim import *

class WorkingExampleScene(Scene):
    def construct(self):
        # 1. Display a title
        title = Text("Chapter Title Example", font_size=48).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # 2. Introduce a basic concept with text and shape
        concept_text = Text("Key Concept 1", font_size=36).next_to(title, DOWN, buff=0.5)
        shape = Circle(radius=0.5, color=WHITE, fill_opacity=0.3).next_to(concept_text, DOWN, buff=0.5)

        self.play(FadeIn(concept_text), Create(shape))
        self.wait(1.5)

        # 3. Show a relationship or transformation
        shape2 = Square(side_length=1.0, color=BLUE).next_to(shape, RIGHT, buff=1.0)
        arrow = Arrow(shape.get_right(), shape2.get_left(), buff=0.1, color=YELLOW)
        explanation = Text("Transforms to...", font_size=24).next_to(arrow, UP, buff=0.2)

        self.play(GrowArrow(arrow), Write(explanation))
        self.play(Transform(shape, shape2)) # Transform circle into square
        self.wait(1)

        # 4. Group and fade out elements
        # Note: 'shape' is now the transformed square after Transform
        elements_to_remove = VGroup(concept_text, shape, arrow, explanation)
        self.play(FadeOut(elements_to_remove))
        # Keep title on screen or fade it too:
        # self.play(FadeOut(elements_to_remove, title))
        self.wait(0.5)

        # 5. Final simple message
        end_message = Text("End of example section.", font_size=32)
        self.play(Write(end_message))
        self.wait(2)
        self.play(FadeOut(end_message, title)) # Fade out everything at the end

# --- END OF PRESET MANIM EXAMPLE ---
"""
    # --- END OF PRESET MANIM EXAMPLE ---

    # Create enhanced examples for various packages if they appear relevant
    neural_network_example = ""
    code_blocks_example = ""
    algorithm_example = ""
    voiceover_example = ""
    data_structures_example = ""
    
    if "neural_network" in suggested_imports:
        neural_network_example = """
# --- NEURAL NETWORK EXAMPLE ---
from manim import *
from manim_neural_network import *

class NeuralNetworkExample(Scene):
    def construct(self):
        # Create a neural network with 3 layers: 2 input, 3 hidden, 1 output neurons
        network = NeuralNetwork([2, 3, 1])
        self.play(Create(network))
        
        # Feed forward animation
        self.play(FeedForward(network))
        
        # Highlight a specific neuron
        self.play(network.layers[1].neurons[0].animate.set_color(RED))
        
        # Show weight values
        self.play(network.get_weights().animate.set_opacity(1))
        
        # Clean up
        self.play(FadeOut(network))
# --- END NEURAL NETWORK EXAMPLE ---
"""

    if "code_blocks" in suggested_imports:
        code_blocks_example = """
# --- CODE BLOCKS EXAMPLE ---
from manim import *
from manim_code_blocks import *

class CodeExample(Scene):
    def construct(self):
        # Create a Python code block
        code = CodeBlock('''
def example_function(x):
    # Calculate the square
    result = x ** 2
    return result
        ''', language="python")
        
        self.play(Create(code))
        
        # Highlight a specific line
        self.play(code.highlight_line(3))
        
        # Add an annotation
        annotation = Text("This calculates x²", font_size=24).next_to(code, RIGHT)
        self.play(Write(annotation))
        
        # Clean up
        self.play(FadeOut(code), FadeOut(annotation))
# --- END CODE BLOCKS EXAMPLE ---
"""

    if "algorithm" in suggested_imports:
        algorithm_example = """
# --- ALGORITHM EXAMPLE ---
from manim import *
from manim_algorithm import *

class SortingExample(Scene):
    def construct(self):
        # Create an array
        arr = Array([5, 2, 8, 1, 9, 3])
        self.play(Create(arr))
        
        # Show bubble sort steps
        self.play(BubbleSort(arr))
        
        # Clean up
        self.play(FadeOut(arr))
# --- END ALGORITHM EXAMPLE ---
"""

    if "voiceover" in suggested_imports:
        voiceover_example = """
# --- VOICEOVER EXAMPLE ---
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class VoiceoverExample(VoiceoverScene):
    def construct(self):
        # Initialize text-to-speech service
        self.set_speech_service(GTTSService())
        
        # Create a simple shape
        circle = Circle(radius=1.0)
        
        # Add voiceover with animation
        with self.voiceover("This is a circle."):
            self.play(Create(circle))
        
        # Another voiceover segment
        with self.voiceover("We can transform it into a square."):
            self.play(Transform(circle, Square(side_length=2.0)))
            
        # Final segment
        with self.voiceover("And that's how shapes can be transformed."):
            self.play(FadeOut(circle))
# --- END VOICEOVER EXAMPLE ---
"""

    if "data_structures" in suggested_imports:
        data_structures_example = """
# --- DATA STRUCTURES EXAMPLE ---
from manim import *
from manim_data_structures import *

class DataStructuresExample(Scene):
    def construct(self):
        # Create a binary tree
        tree = Tree()
        tree.add_elements([5, 3, 7, 2, 4, 6, 8])
        self.play(Create(tree))
        self.wait(1)
        
        # Highlight a path in the tree
        self.play(tree.highlight_path([5, 3, 2]))
        self.wait(1)
        
        # Create a graph
        graph = Graph([1, 2, 3, 4], [(1, 2), (1, 3), (2, 4), (3, 4)])
        self.play(FadeOut(tree))
        self.play(Create(graph))
        
        # Clean up
        self.play(FadeOut(graph))
# --- END DATA STRUCTURES EXAMPLE ---
"""

    system_prompt = (
        "You are an expert Manim developer who specializes in creating precise, elegant mathematical animations. "
        "You write clean, well-structured Python code that leverages the Manim library and its extensions effectively. "
        "Your code is always syntactically correct, follows best practices, and focuses on visual clarity."
    )

    api_prompt = (
        f"Create Python code using the Manim animation library to visualize concepts from this educational script "
        f"for '{chapter_title}'.\n\n"
        f"SCRIPT TO VISUALIZE:\n{script}\n\n"
        f"REQUIREMENTS:\n"
        f"1. Import Statement Requirements - USE THESE EXACT IMPORTS:\n{suggested_imports}\n\n"
        f"2. Name your main Scene class: '{target_scene_class_name}'\n\n"
        f"3. IMPORTANT STYLE GUIDELINES:\n"
        f"   - Create a logical sequence of animations that follows the script's flow\n"
        f"   - Pay special attention to the visual cues in parentheses (Visual: ...)\n"
        f"   - Use appropriate timing with self.wait() between animations\n"
        f"   - Use clean, consistent object naming and organization\n"
        f"   - Add helpful comments explaining complex sections\n"
        f"   - Ensure all objects are properly removed or transformed\n\n"
        f"4. USE THESE MANIM LIBRARIES FROM requirements.txt:\n"
        f"   - manim-speech: For adding narration to animations\n"
        f"   - manim-algorithm: For algorithm visualizations\n"
        f"   - manim-neural-network: For neural network diagrams\n" 
        f"   - manim-code-blocks: For displaying code snippets\n"
        f"   - manim-data-structures: For data structure visualizations\n"
        f"   - manim-fonts: For enhanced typography options\n"
        f"   - manim-ml: For machine learning visualizations\n\n"
        f"5. AVAILABLE ANIMATION ELEMENTS:\n"
        f"   - Basic shapes: Circle, Square, Rectangle, Line, Arrow, Dot\n"
        f"   - Text elements: Text, MathTex, Tex\n"
        f"   - Animations: Create, Write, FadeIn, FadeOut, Transform, GrowArrow\n"
        f"   - Positioning: .to_edge(), .next_to(), .shift(), .scale()\n"
        f"   - Grouping: VGroup for managing multiple objects\n"
        f"   - Colors: WHITE, BLUE, RED, GREEN, YELLOW, etc.\n\n"
        f"6. EXAMPLES FOR REFERENCE:\n{manim_example_code}\n\n"
        f"{neural_network_example}\n{code_blocks_example}\n{algorithm_example}\n{voiceover_example}\n{data_structures_example}\n"
        f"Produce ONLY valid Python code with no explanations or markdown formatting."
    )
    
    # Simplify the prompt if it's too long
    if len(api_prompt) > 10000:  # OpenRouter might have token limits
        api_prompt = (
            f"Create Python code using Manim to animate the key concepts from '{chapter_title}'.\n\n"
            f"Use these imports:\n{suggested_imports}\n\n"
            f"Name your main Scene class: '{target_scene_class_name}'\n\n"
            f"Create a logical sequence showing these concepts: {', '.join(key_concepts if key_concepts else ['Basic Concept'])}\n\n"
            f"Leverage manim extension libraries: manim-voiceover, manim-algorithm, manim-neural-network, "
            f"manim-code-blocks, manim-data-structures based on their relevance to this content.\n\n"
            f"Follow basic Manim patterns with Write(), Create(), Transform(), and FadeOut() animations.\n\n"
            f"Produce ONLY valid Python code with no explanations."
        )
    
    try:
        # Try the API call
        manim_code_content = call_openrouter_api(api_prompt, system_prompt)
        
        # Validate the response
        if manim_code_content and len(manim_code_content) > 200:  # Reasonable minimum length
            # Clean potential markdown code fences and surrounding whitespace
            manim_code_content = manim_code_content.strip()
            if manim_code_content.startswith("```python"):
                manim_code_content = manim_code_content.removeprefix("```python").removesuffix("```").strip()
            elif manim_code_content.startswith("```"):
                manim_code_content = manim_code_content.removeprefix("```").removesuffix("```").strip()

            # Add an extra check to see if the generated code seems plausible
            if f"class {target_scene_class_name}" not in manim_code_content or "def construct(self):" not in manim_code_content:
                logger.warning(f"Generated code for {chapter_title} doesn't contain the expected class or method definition.")
                logger.info(f"Using fallback Manim code template for '{chapter_title}'")
                return create_fallback_manim_code(chapter_title, script, key_concepts)
            
            # Check if the code is valid
            validation_result = check_manim_code(manim_code_content, chapter_title)
            
            if not validation_result['is_valid']:
                logger.warning(f"Generated code for {chapter_title} has errors: {validation_result['errors']}")
                
                # Try to fix the errors using the model
                error_correction_prompt = get_error_correction_prompt(manim_code_content, validation_result['errors'])
                fixed_code = call_openrouter_api(error_correction_prompt, system_prompt)
                
                if fixed_code and len(fixed_code) > 200:
                    # Clean up the fixed code
                    fixed_code = fixed_code.strip()
                    if fixed_code.startswith("```python"):
                        fixed_code = fixed_code.removeprefix("```python").removesuffix("```").strip()
                    elif fixed_code.startswith("```"):
                        fixed_code = fixed_code.removeprefix("```").removesuffix("```").strip()
                    
                    # Validate the fixed code
                    fixed_validation = check_manim_code(fixed_code, chapter_title)
                    if fixed_validation['is_valid']:
                        logger.info(f"Successfully fixed Manim code for '{chapter_title}'")
                        return fixed_code
                    else:
                        logger.warning(f"Failed to fix Manim code errors, using fallback")
                        return create_fallback_manim_code(chapter_title, script, key_concepts)
                else:
                    logger.warning(f"Failed to get error corrections, using fallback")
                    return create_fallback_manim_code(chapter_title, script, key_concepts)
            
            logger.info(f"Successfully generated Manim code for '{chapter_title}' ({len(manim_code_content)} chars)")
            return manim_code_content
        else:
            logger.warning(f"API returned empty or too short Manim code for '{chapter_title}'. Using fallback.")
            return create_fallback_manim_code(chapter_title, script, key_concepts)
            
    except Exception as e:
        logger.error(f"Error getting Manim code for '{chapter_title}': {e}")
        logger.info(f"Using fallback Manim code template for '{chapter_title}'")
        return create_fallback_manim_code(chapter_title, script, key_concepts)


# --- Utility Functions ---

def save_to_file(filename: str, content: str) -> bool:
    """
    Saves content to a file, creating directories if needed.
    
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Successfully saved: {filename}")
        return True
    except IOError as e:
        logger.error(f"Error saving file {filename}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred saving file {filename}: {e}")
        return False


def run_manim_render(manim_script_path: str, scene_class_name: str) -> Dict[str, Any]:
    """
    Attempts to run the Manim rendering command using subprocess.
    Requires Manim to be installed and configured in the system's PATH.
    Utilizes manim-editor to create presentation-ready videos with sections and voiceovers.

    Args:
        manim_script_path: Path to the generated .py Manim script.
        scene_class_name: The name of the Scene class inside the script.
        
    Returns:
        Dict with 'success', 'output', 'error', 'error_message', and 'output_file' keys.
    """
    result = {
        'success': False,
        'output': '',
        'error': '',
        'error_message': '',
        'output_file': ''
    }
    
    if not os.path.exists(manim_script_path):
        logger.error(f"Manim script not found at {manim_script_path}. Skipping rendering.")
        result['error_message'] = f"Script file not found: {manim_script_path}"
        return result
    
    if not scene_class_name:
        logger.error(f"Invalid Scene class name provided for {manim_script_path}. Skipping rendering.")
        result['error_message'] = "Invalid scene class name"
        return result

    # Create a specific media output directory
    output_dir = os.path.join(os.path.dirname(manim_script_path), "media_output")
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Attempting Manim Rendering: {manim_script_path}")
    logger.info(f"Using Scene Class: {scene_class_name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info("Rendering with manim-editor integration for enhanced presentation quality")

    # Detect platform and adjust command if needed
    is_windows = os.name == 'nt'
    
    # First, render for manim-editor to create section data
    if is_windows:
        # For Windows with manim-editor integration
        command_sections = [
            "python", "-m", "manim",
            "--media_dir", output_dir,
            "render", "-ql", "--save_sections",
            manim_script_path,
            scene_class_name
        ]
    else:
        # For Unix-like systems with manim-editor integration
        command_sections = [
            "manim",
            "--media_dir", output_dir,
            "render", "-ql", "--save_sections",
            manim_script_path,
            scene_class_name
        ]

    try:
        logger.info(f"Executing command (sections): {' '.join(command_sections)}")
        
        # Run Manim with sections saving enabled
        timeout_seconds = 300
        result_sections = subprocess.run(
            command_sections,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False,
            timeout=timeout_seconds
        )

        # Store the command output
        result['output'] = result_sections.stdout
        result['error'] = result_sections.stderr
        
        # Log the output
        logger.debug("--- Manim Sections Stdout ---")
        logger.debug(result_sections.stdout if result_sections.stdout else "[No stdout]")
        logger.debug("--- Manim Sections Stderr ---")
        logger.debug(result_sections.stderr if result_sections.stderr else "[No stderr]")

        # Now, if sections rendering was successful, render the final presentation video
        if result_sections.returncode == 0:
            logger.info("Sections saved successfully. Now creating presentation video with manim-editor...")
            
            # Determine the location of the sections JSON file
            scene_base = os.path.basename(manim_script_path).replace('.py', '')
            sections_dir = os.path.join(output_dir, "sections", scene_base)
            
            # Now render the presentation with manim-editor
            if is_windows:
                command_presentation = [
                    "python", "-m", "manim_editor",
                    "render", "--low_quality",
                    manim_script_path, scene_class_name,
                    "--media_dir", output_dir
                ]
            else:
                command_presentation = [
                    "manim-editor",
                    "render", "--low_quality",
                    manim_script_path, scene_class_name,
                    "--media_dir", output_dir
                ]
                
            logger.info(f"Executing manim-editor command: {' '.join(command_presentation)}")
            
            result_presentation = subprocess.run(
                command_presentation,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                check=False,
                timeout=timeout_seconds * 2  # Longer timeout for presentation rendering
            )
            
            # Append presentation output to our results
            result['output'] += "\n" + result_presentation.stdout
            result['error'] += "\n" + result_presentation.stderr
            
            logger.debug("--- Manim Editor Stdout ---")
            logger.debug(result_presentation.stdout if result_presentation.stdout else "[No stdout]")
            logger.debug("--- Manim Editor Stderr ---")
            logger.debug(result_presentation.stderr if result_presentation.stderr else "[No stderr]")
            
            # Consider the overall process successful if either rendering method worked
            if result_presentation.returncode == 0 or result_sections.returncode == 0:
                logger.info(f"Manim rendering completed successfully.")
                result['success'] = True
                
                # Try to find the generated media file (prioritize presentation file)
                try:
                    # First look for manim-editor presentation file
                    presentation_dir = os.path.join(output_dir, "presentations")
                    if os.path.exists(presentation_dir):
                        for root, dirs, files in os.walk(presentation_dir):
                            for file in files:
                                if file.endswith('.mp4'):
                                    full_path = os.path.join(root, file)
                                    logger.info(f"Found presentation video: {full_path}")
                                    result['output_file'] = full_path
                                    break
                    
                    # If presentation not found, look for standard Manim output
                    if not result['output_file']:
                        media_search_path = os.path.join(output_dir, "videos", scene_base)
                        logger.info(f"Searching for rendered video in: {media_search_path}")
                        
                        # Check both MP4 and various quality folders
                        mp4_files = []
                        for root, dirs, files in os.walk(media_search_path):
                            for file in files:
                                if file.endswith('.mp4'):
                                    full_path = os.path.join(root, file)
                                    mp4_files.append(full_path)
                                    logger.info(f"Found rendered video: {full_path}")
                    
                        if mp4_files:
                            result['output_file'] = mp4_files[0]  # Use the first MP4 found
                    
                    # Copy the rendered file to a more accessible location
                    if result['output_file']:
                        output_filename = f"{scene_class_name}.mp4"
                        top_level_output = os.path.join(os.path.dirname(manim_script_path), output_filename)
                        shutil.copy2(result['output_file'], top_level_output)
                        logger.info(f"Copied rendered video to accessible location: {top_level_output}")
                        
                        # Also set this as the output file for easier access
                        result['output_file'] = top_level_output
                    else:
                        logger.warning("No MP4 files found after successful rendering. This is unusual.")
                except Exception as e:
                    logger.error(f"Error finding rendered video: {e}")
                
                return result
            else:
                logger.error(f"Manim rendering failed with return code {result_presentation.returncode}.")
                logger.error("Review the generated code for potential errors.")
                result['success'] = False
                result['error_message'] = f"Rendering failed with code {result_presentation.returncode}"
                return result
        else:
            logger.error(f"Initial sections rendering failed with return code {result_sections.returncode}.")
            logger.error("Attempting standard rendering without presentation features.")
            
            # Attempt a standard render without manim-editor features
            standard_command = []
            if is_windows:
                standard_command = [
                    "python", "-m", "manim",
                    "--media_dir", output_dir,
                    "render", "-ql",
                    manim_script_path,
                    scene_class_name
                ]
            else:
                standard_command = [
                    "manim",
                    "--media_dir", output_dir,
                    "render", "-ql",
                    manim_script_path,
                    scene_class_name
                ]
                
            logger.info(f"Executing standard command: {' '.join(standard_command)}")
            
            result_standard = subprocess.run(
                standard_command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                check=False,
                timeout=timeout_seconds
            )
            
            if result_standard.returncode == 0:
                logger.info(f"Standard Manim rendering completed successfully.")
                result['success'] = True
                
                # Try to find the generated media file
                try:
                    scene_base = os.path.basename(manim_script_path).replace('.py', '')
                    media_search_path = os.path.join(output_dir, "videos", scene_base)
                    logger.info(f"Searching for rendered video in: {media_search_path}")
                    
                    # Check both MP4 and various quality folders
                    mp4_files = []
                    for root, dirs, files in os.walk(media_search_path):
                        for file in files:
                            if file.endswith('.mp4'):
                                full_path = os.path.join(root, file)
                                mp4_files.append(full_path)
                                logger.info(f"Found rendered video: {full_path}")
                    
                    if mp4_files:
                        result['output_file'] = mp4_files[0]  # Use the first MP4 found
                        
                        # Copy the rendered file to a more accessible location
                        output_filename = f"{scene_class_name}.mp4"
                        top_level_output = os.path.join(os.path.dirname(manim_script_path), output_filename)
                        shutil.copy2(result['output_file'], top_level_output)
                        logger.info(f"Copied rendered video to accessible location: {top_level_output}")
                        
                        # Also set this as the output file for easier access
                        result['output_file'] = top_level_output
                    else:
                        logger.warning("No MP4 files found after successful rendering. This is unusual.")
                except Exception as e:
                    logger.error(f"Error finding rendered video: {e}")
                
                return result
            else:
                result['success'] = False
                result['error_message'] = f"All rendering methods failed. Last code: {result_standard.returncode}"
                return result

    except FileNotFoundError:
        logger.error("'manim' command not found. Please ensure Manim Community Edition is installed.")
        logger.error("Try running 'manim --version' in your terminal to verify installation.")
        result['error_message'] = "Manim command not found - check installation"
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Manim rendering timed out after {timeout_seconds} seconds.")
        logger.error("This might indicate an infinite loop in the animation code or a very complex scene.")
        result['error_message'] = f"Rendering timed out after {timeout_seconds} seconds"
        return result
    except Exception as e:
        logger.error(f"An unexpected error occurred during Manim execution: {e}")
        logger.error("Check Manim installation and script content.")
        result['error_message'] = f"Unexpected error: {str(e)}"
        return result


def fix_manim_rendering_errors(manim_script_path: str, scene_class_name: str, render_result: Dict[str, Any]) -> bool:
    """
    Attempts to fix Manim rendering errors by analyzing the error output and 
    correcting the code.
    
    Args:
        manim_script_path: Path to the Manim script.
        scene_class_name: The name of the scene class.
        render_result: The result from the run_manim_render function.
        
    Returns:
        True if fixed successfully, False otherwise.
    """
    if not render_result or render_result.get('success', False):
        return True  # Nothing to fix
        
    error_output = render_result.get('error', '') + render_result.get('output', '')
    if not error_output:
        logger.error("No error output to analyze for fixing rendering issues")
        return False
        
    # Read the current script content
    try:
        with open(manim_script_path, 'r', encoding='utf-8') as f:
            current_code = f.read()
    except Exception as e:
        logger.error(f"Error reading Manim script to fix: {e}")
        return False
        
    # Create a prompt to fix the rendering errors
    error_fix_prompt = (
        f"The following Manim code failed to render with these errors:\n\n"
        f"{error_output[:3000]}\n\n"  # Limit error size to 3000 chars
        f"Here's the current code:\n\n{current_code}\n\n"
        f"Please fix the issues that are causing the rendering to fail. "
        f"The scene class name should remain '{scene_class_name}'. "
        f"Return ONLY the fixed Python code with no explanations."
    )
    
    # Get fixed code from the API
    system_prompt = "You are an expert at debugging and fixing Manim animation code."
    try:
        fixed_code = call_openrouter_api(error_fix_prompt, system_prompt)
        
        if fixed_code and len(fixed_code) > 200:
            # Clean up the fixed code
            fixed_code = fixed_code.strip()
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code.removeprefix("```python").removesuffix("```").strip()
            elif fixed_code.startswith("```"):
                fixed_code = fixed_code.removeprefix("```").removesuffix("```").strip()
                
            # Write the fixed code back to the file
            with open(manim_script_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
                
            logger.info(f"Updated Manim script with fixes. Attempting to render again.")
            
            # Try rendering again
            new_result = run_manim_render(manim_script_path, scene_class_name)
            if new_result.get('success', False):
                logger.info("Successfully fixed Manim rendering errors!")
                return True
            else:
                logger.warning("Failed to fix Manim rendering errors despite code updates.")
                return False
        else:
            logger.error("Failed to get fixed code for rendering errors")
            return False
    except Exception as e:
        logger.error(f"Error attempting to fix Manim rendering: {e}")
        return False


def get_module_video_url(module):
    """
    Convert a module's manim_video_path to a Flask static URL.
    """
    path = module.manim_video_path
    if not path:
        return None
    # Normalize separators
    normalized = path.replace('\\', '/')
    # Look for the 'static/' segment
    idx = normalized.find('static/')
    if idx != -1:
        rel_path = normalized[idx + len('static/'):]
        return url_for('static', filename=rel_path)
    # Fallback: return raw path
    return path


# --- Functions migrated from manim_utils.py ---

# Store Manim generation progress globally
_manim_generation_progress = {
    "status": "idle",
    "total_videos": 0,
    "completed_videos": 0,
    "current_video": None,
    "details": []
}

def reset_manim_progress(total_videos=0):
    """Reset the Manim generation progress tracker"""
    global _manim_generation_progress
    _manim_generation_progress = {
        "status": "ready",
        "total_videos": total_videos,
        "completed_videos": 0,
        "current_video": None,
        "details": []
    }

def update_manim_progress(status, message, video_title=None):
    """Update the Manim generation progress"""
    global _manim_generation_progress
    
    _manim_generation_progress["status"] = status
    
    if status == "processing" and video_title:
        _manim_generation_progress["current_video"] = video_title
    elif status == "completed" and video_title:
        _manim_generation_progress["completed_videos"] += 1
        _manim_generation_progress["current_video"] = None
    
    # Add the message to the details list (max 20 messages)
    _manim_generation_progress["details"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message
    })
    
    # Keep only the latest 20 messages
    if len(_manim_generation_progress["details"]) > 20:
        _manim_generation_progress["details"] = _manim_generation_progress["details"][-20:]

def get_manim_generation_progress():
    """Get the current Manim generation progress"""
    global _manim_generation_progress
    return _manim_generation_progress

def generate_and_save_manim_video(topic, content, learning_style="visual", output_path=None):
    """
    Generate a Manim animation video based on topic and content.
    Now uses enhanced course video generation with manim-editor and manim-speech.
    
    Args:
        topic (str): The topic of the video
        content (str): Content description
        learning_style (str): visual, auditory, or hands-on
        output_path (str): Path to save the video (optional)
        
    Returns:
        str: Path to the generated video or None if failed
    """
    # Use the new enhanced course video generation
    return create_course_video(topic, content, learning_style, output_path)

def create_course_video(topic: str, content: str, learning_style: str, output_path: str = None) -> str:
    """
    Creates a comprehensive course video using manim-editor and manim-speech integration.
    
    This is the main entry point for creating educational videos with full presentation
    capabilities using all available Manim packages.
    
    Args:
        topic: The topic of the course video
        content: Detailed content description/script
        learning_style: "visual", "auditory", or "hands-on"
        output_path: Path to save the video (optional)
        
    Returns:
        Path to the generated video or None if failed
    """
    try:
        logger.info(f"Creating course video for '{topic}' with {learning_style} learning style")
        
        # Use all available packages from manimconfig
        available_packages = []
        try:
            from . import manimconfig
            if hasattr(manimconfig, 'MANIM_PACKAGES'):
                available_packages = manimconfig.MANIM_PACKAGES
                logger.info(f"Utilizing {len(available_packages)} Manim packages: {', '.join(available_packages)}")
            else:
                logger.warning("No MANIM_PACKAGES found in manimconfig")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Error accessing manimconfig.MANIM_PACKAGES: {str(e)}")
        
        # Generate the Manim script with full presentation sections and voiceovers
        logger.info("Generating presentation-ready Manim script with voiceovers")
        script = generate_manim_script(topic, learning_style, "medium")
        
        # Generate a unique ID for this rendering
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a safe filename based on the topic
        safe_topic = ''.join(c if c.isalnum() else '_' for c in topic)
        script_filename = f"manim_course_{safe_topic}_{unique_id}.py"
        
        # Set up directories
        videos_dir = os.path.join("Backend", "website", "static", "courses", "videos")
        scripts_dir = os.path.join("Backend", "website", "static", "courses", "scripts")
        os.makedirs(videos_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Define output paths
        script_path = os.path.join(scripts_dir, script_filename)
        
        if output_path is None:
            output_path = os.path.join(videos_dir, f"{safe_topic}_{unique_id}.mp4")
        
        # Initialize progress tracking
        update_manim_progress("processing", f"Creating course video for '{topic}'", topic)
        
        # Save the script to file
        if save_to_file(script_path, script):
            logger.info(f"Saved Manim script to {script_path}")
            
            # Get scene class name from the topic
            scene_class_name = f"{topic.replace(' ', '')}Scene"
            
            # Render with manim-editor integration
            logger.info(f"Rendering presentation video with manim-editor and voiceovers")
            update_manim_progress("rendering", f"Rendering presentation video for '{topic}'", topic)
            render_result = run_manim_render(script_path, scene_class_name)
            
            if render_result['success']:
                logger.info(f"Successfully rendered course video for '{topic}'")
                update_manim_progress("completed", f"Successfully created course video for '{topic}'", topic)
                
                # Make sure output_file exists in the render result
                if 'output_file' in render_result and os.path.exists(render_result['output_file']):
                    # If output paths differ, copy the file
                    if output_path != render_result['output_file']:
                        import shutil
                        shutil.copy2(render_result['output_file'], output_path)
                        logger.info(f"Copied presentation video to {output_path}")
                    return output_path
                else:
                    logger.warning(f"Output file not found in render result for '{topic}'")
                    return render_result.get('output_file', output_path)
            else:
                logger.error(f"Failed to render course video: {render_result.get('error_message', 'Unknown error')}")
                update_manim_progress("error", f"Failed to create course video: {render_result.get('error_message', 'Unknown error')}", topic)
                return None
        else:
            logger.error(f"Failed to save Manim script for '{topic}'")
            update_manim_progress("error", f"Failed to save script for '{topic}'", topic)
            return None
    
    except Exception as e:
        logger.error(f"Error creating course video for '{topic}': {str(e)}")
        update_manim_progress("error", f"Error: {str(e)}", topic)
        return None


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
    
    # Create a more comprehensive Manim script that uses various packages
    # Enhanced with manim-editor and manim-voiceover integration
    script = f"""
from manim import *
from manim_editor import PresentationSectionType
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
import numpy as np

# For code demonstrations if needed
try:
    from manim_code_blocks import Code
except ImportError:
    pass

# For neural network visualization if needed
try:
    from manim_neural_network import NeuralNetworkMobject
except ImportError:
    pass

# For data structure visualization if needed
try:
    from manim_data_structures import Array, LinkedList, Stack, Queue, BinaryTree
except ImportError:
    pass

class {topic.replace(" ", "")}Scene(VoiceoverScene):
    def construct(self):
        # Initialize the text-to-speech service
        self.set_speech_service(GTTSService())
        
        # Course title and topic introduction with voice narration
        topic = "{topic}"
        
        # SECTION 1: Introduction
        self.next_section("Introduction", PresentationSectionType.NORMAL)
        with self.voiceover("Welcome to this educational video on " + topic + "."):
            title = Text(topic, font_size=48)
            self.play(Write(title))
            self.wait(1)
        
        # Subtitle with author information
        with self.voiceover("In this video, we'll explore the key concepts and applications of this important topic."):
            subtitle = Text("An Educational Presentation", font_size=24)
            self.play(title.animate.to_edge(UP), Write(subtitle))
            self.wait(1)
            self.play(FadeOut(subtitle))
        
        # SECTION 2: Overview
        self.next_section("Overview", PresentationSectionType.NORMAL)
        with self.voiceover("Let's start with an overview of what we'll cover today."):
            overview = Text("Overview", font_size=36)
            self.play(ReplacementTransform(title, overview))
            self.wait(1)
            
            # Key topics bullet points
            topics = BulletedList(
                "Core concepts",
                "Key applications",
                "Real-world examples",
                "Practice scenarios",
                font_size=24
            )
            self.play(Write(topics))
            self.wait(2)
            
            # Highlight each topic as we introduce it
            for i in range(len(topics)):
                self.play(topics.animate_item(i, highlight_color=YELLOW), run_time=0.5)
                self.wait(0.5)
            
            self.wait(1)
            self.play(FadeOut(topics), FadeOut(overview))
        
        # SECTION 3: Main Content
        self.next_section("Main Content", PresentationSectionType.NORMAL)
        with self.voiceover("Now, let's dive into the main content of " + topic + "."):
            main_title = Text("Main Content", font_size=36)
            self.play(Write(main_title))
            self.wait(1)
            self.play(FadeOut(main_title))
            
            # Concept 1
            with self.voiceover("First, let's explore the fundamental concepts."):
                concept1 = Text("Key Concept 1", font_size=32)
                self.play(Write(concept1))
                self.wait(1)
                
                # Simple visualization for concept 1
                concept1_viz = Circle(radius=1.5, color=BLUE)
                self.play(ReplacementTransform(concept1, concept1_viz))
                self.wait(1)
                self.play(concept1_viz.animate.set_color(GREEN))
                self.wait(1)
                self.play(FadeOut(concept1_viz))
            
            # Concept 2
            with self.voiceover("Next, let's look at another important aspect."):
                concept2 = Text("Key Concept 2", font_size=32)
                self.play(Write(concept2))
                self.wait(1)
                
                # Simple visualization for concept 2
                concept2_viz = Square(side_length=2, color=RED)
                self.play(ReplacementTransform(concept2, concept2_viz))
                self.wait(1)
                self.play(Rotate(concept2_viz, PI/2))
                self.wait(1)
                self.play(FadeOut(concept2_viz))
        
        # SECTION 4: Application/Example
        self.next_section("Application", PresentationSectionType.NORMAL)
        with self.voiceover("Let's see how these concepts apply in real-world scenarios."):
            application = Text("Practical Application", font_size=36)
            self.play(Write(application))
            self.wait(1)
            self.play(application.animate.to_edge(UP))
            
            # Try to use specialized visualizations based on the topic
            if "programming" in topic.lower() or "coding" in topic.lower() or "algorithm" in topic.lower():
                try:
                    code_str = '''
def example_function(x):
    result = x * 2
    return result

# Call the function
example_function(5)
'''
                    code = Code(
                        code=code_str,
                        tab_width=4,
                        background="window",
                        language="Python",
                        font="Monospace"
                    )
                    self.play(Write(code))
                    self.wait(2)
                    self.play(FadeOut(code))
                except:
                    # Fallback
                    code_viz = Text("Code Example", font_size=24)
                    self.play(Write(code_viz))
                    self.wait(2)
                    self.play(FadeOut(code_viz))
            
            elif "neural network" in topic.lower() or "machine learning" in topic.lower() or "ai" in topic.lower():
                try:
                    nn = NeuralNetworkMobject([3, 4, 2])
                    self.play(Write(nn))
                    self.wait(2)
                    self.play(FadeOut(nn))
                except:
                    # Fallback
                    nn_viz = Text("Neural Network Visualization", font_size=24)
                    self.play(Write(nn_viz))
                    self.wait(2)
                    self.play(FadeOut(nn_viz))
            
            else:
                # Generic visualization
                # Define bounds for LaTeX integration formula
                lower_bound = "a"  # Integration lower bound 
                upper_bound = "b"  # Integration upper bound
                # Construct the LaTeX formula string with explicit values to avoid undefined variable errors
                formula_text = r"f(x) = \int_{" + lower_bound + r"}^{" + upper_bound + r"} g(x) dx"
                formula = MathTex(formula_text)
                self.play(Write(formula))
                self.wait(2)
                self.play(FadeOut(formula))
        
        # SECTION 5: Summary
        self.next_section("Summary", PresentationSectionType.NORMAL)
        with self.voiceover("Let's summarize what we've learned about " + topic + "."):
            conclusion = Text("Summary of key points", font_size=28)
            self.play(Write(conclusion))
            self.wait(2)
            
            # Final title with manim-editor section for easy ending
            self.next_section("Ending", PresentationSectionType.NORMAL)
            with self.voiceover("Thanks for watching this video on " + topic + "."):
                final_title = Text("Thanks for watching!", font_size=36)
                self.play(ReplacementTransform(conclusion, final_title))
                self.wait(2)
    """ 
    
    return script


# --- Main Workflow ---
def main():
    logger.info("--- Automated Course Content Generator with Gemini ---")
    logger.info("This script uses the OpenRouter API with Gemini to generate course outlines, scripts,")
    logger.info("and Manim animation code, leveraging specialized Manim packages.")
    logger.info("Requires OpenRouter API configuration in config.py and local Manim installation.\n")

    # 1. Get user input
    topic = input("Enter the course topic (e.g., Introduction to Quantum Computing): ")
    if not topic:
        logger.error("Topic cannot be empty.")
        return

    # Create output directories safely
    # Replace spaces and invalid chars for directory name
    safe_topic_name = ''.join(c for c in topic if c.isalnum() or c in [' ', '_', '-']).strip()
    output_dir_base = safe_topic_name.lower().replace(" ", "_")
    if not output_dir_base: output_dir_base = "untitled_course" # Fallback
    output_dir = output_dir_base + "_course_content"

    scripts_dir = os.path.join(output_dir, "video_scripts")
    manim_code_dir = os.path.join(output_dir, "manim_code")

    try:
        os.makedirs(scripts_dir, exist_ok=True)
        os.makedirs(manim_code_dir, exist_ok=True)
        logger.info(f"Output will be saved in: {os.path.abspath(output_dir)}")
    except OSError as e:
        logger.error(f"Error creating output directories: {e}")
        return

    # 2. Get course overview
    logger.info("Generating course overview...")
    course_data = get_course_overview(topic)

    if not course_data or not course_data.get("chapters"):
        logger.error("Failed to generate a valid course overview. Exiting.")
        return

    course_title = course_data.get('title', 'Untitled Course')
    logger.info(f"Generated Course Overview for '{course_title}':")
    for i, chapter in enumerate(course_data.get("chapters", []), 1):
        logger.info(f"  {i}. {chapter.get('title', 'Unnamed Chapter')} (ID: {chapter.get('id', 'no_id')})")

    overview_filename = os.path.join(output_dir, "course_overview.json")
    save_to_file(overview_filename, json.dumps(course_data, indent=4))

    # 3. Process each chapter
    chapters = course_data.get("chapters", [])
    total_chapters = len(chapters)
    
    # Use tqdm for progress tracking
    for i, chapter in enumerate(tqdm(chapters, desc="Processing Chapters", unit="chapter")):
        chapter_title = chapter.get("title")
        chapter_id = chapter.get("id") # Should be filesystem-safe based on prompt
        key_concepts = chapter.get("key_concepts", [])  # New field from enhanced prompt

        logger.info(f"Processing Chapter {i+1}/{total_chapters}: '{chapter_title}' (ID: {chapter_id})")

        if not chapter_title or not chapter_id:
            logger.warning(f"Skipping chapter {i+1} due to missing title or id.")
            continue

        # 3a. Get video script
        logger.info("Generating video script...")
        script_content = get_video_script(chapter_title, course_title, key_concepts)
        if not script_content:
            logger.error(f"Failed to generate script for '{chapter_title}'. Skipping Manim steps for this chapter.")
            # Save an error indicator file
            script_filename = os.path.join(scripts_dir, f"{chapter_id}_script_FAILED.txt")
            save_to_file(script_filename, "# Script generation failed.")
            continue # Skip to next chapter if script generation fails

        script_filename = os.path.join(scripts_dir, f"{chapter_id}_script.txt")
        save_to_file(script_filename, script_content)

        # 3b. Get Manim code
        logger.info("Generating Manim code with specialized package support...")
        manim_code_content = get_manim_code(script_content, chapter_title, key_concepts)
        if not manim_code_content:
            logger.error(f"Failed to generate Manim code for '{chapter_title}'. Skipping rendering.")
            # Save an error indicator file
            manim_code_filename = os.path.join(manim_code_dir, f"{chapter_id}_manim_code_FAILED.py")
            save_to_file(manim_code_filename, "# Manim code generation failed.")
            continue # Skip rendering if code generation fails

        # Determine Manim script filename using the chapter ID
        manim_code_filename = os.path.join(manim_code_dir, f"{chapter_id}_manim.py")

        # Get expected scene class name
        expected_scene_class_name = get_scene_class_name(chapter_title)

        if save_to_file(manim_code_filename, manim_code_content):
            # 3c. Attempt Manim Rendering 
            render_result = run_manim_render(manim_code_filename, expected_scene_class_name)

            if not render_result.get('success', False):
                logger.error(f"Manim rendering failed with error: {render_result.get('error_message', 'Unknown error')}")
                # Try to fix rendering errors
                if fix_manim_rendering_errors(manim_code_filename, expected_scene_class_name, render_result):
                    logger.info("Manim rendering errors fixed. Attempting to render again.")
                    render_result = run_manim_render(manim_code_filename, expected_scene_class_name)

            if render_result.get('success', False):
                logger.info("Manim rendering completed successfully!")
            else:
                logger.error(f"Manim rendering failed with error: {render_result.get('error_message', 'Unknown error')}")

    logger.info("--- Workflow Complete ---")
    logger.info(f"Outputs generated in directory: {os.path.abspath(output_dir)}")
    logger.info("Check subdirectories: 'video_scripts', 'manim_code'.")
    logger.info("Check Manim's 'media' directory for any successfully rendered videos (.mp4 files).")


if __name__ == "__main__":
    main()