"""
Configuration settings for the Skillora application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API configuration
# Read from environment variable (set in .env or system environment)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Available models (uncomment the one you want to use)
# Free models with fewer restrictions
# OPENROUTER_MODEL = "mistralai/mistral-7b-instruct-v0.2"  # Free model that should work without credits
# OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct"  # Free Llama 3 model
# OPENROUTER_MODEL = "google/gemini-2.5-pro-exp-03-25:free"  # Using Gemini through OpenRouter (free)
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.5-flash-preview')
# Premium models (require credits)
# OPENROUTER_MODEL = "anthropic/claude-3-opus-20240229"      # Claude 3 Opus
# OPENROUTER_MODEL = "anthropic/claude-3-sonnet-20240229"    # Claude 3 Sonnet

# API endpoints
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model parameters
TEMPERATURE = 0.7
MAX_TOKENS = 1000

# Chat settings
MAX_CHAT_HISTORY = 10  # Number of messages to keep in context window 
SYSTEM_PROMPT = "You are Skillora AI, a learning assistant that helps users with educational questions."
