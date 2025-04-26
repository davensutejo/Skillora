"""
Configuration settings for the Skillora application
"""

# OpenRouter API configuration
OPENROUTER_API_KEY = "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"

# Available models (uncomment the one you want to use)
# Free models with fewer restrictions
OPENROUTER_MODEL = "google/gemini-2.5-flash-preview"  # Free model that should work without credits
# OPENROUTER_MODEL = ""

# OPENROUTER_MODEL = "google/gemini-pro"                 # Standard Gemini Pro

# Premium models (require credits)
# OPENROUTER_MODEL = "google/gemini-2.5-pro-exp-03-25:free"  # Paid version of Gemini 2.5 Pro
# OPENROUTER_MODEL = "anthropic/claude-3-opus-20240229"      # Claude 3 Opus
# OPENROUTER_MODEL = "anthropic/claude-3-sonnet-20240229"    # Claude 3 Sonnet

# API endpoints
GEMINI_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model parameters
TEMPERATURE = 0.7
MAX_TOKENS = 1000

# Chat settings
MAX_CHAT_HISTORY = 10  # Number of messages to keep in context window 
GEMINI_SYSTEM_PROMPT="""You are Skillora AI, an educational assistant developed for the Skillora learning platform.

- Always introduce yourself as 'Skillora AI' when relevant
- Never identify yourself as a Google model, Claude, GPT or any other AI
- Never say phrases like 'I am a large language model' or 'I was trained by Google/OpenAI/Anthropic'
- Remember you are specifically 'Skillora AI', an educational assistant focused on helping users with learning

Your primary purpose is to help users with educational questions and support their learning journey.

Anda adalah Skillora AI, asisten belajar yang membantu pengguna dengan pertanyaan pendidikan."""