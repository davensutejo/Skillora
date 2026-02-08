"""
Configuration file for OpenRouter API
"""

# OpenRouter API Configuration
OPENROUTER_API_KEY = "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"  # Your OpenRouter API key
OPENROUTER_API_BASE_URL = "https://openrouter.ai/api/v1"

# Default model settings
DEFAULT_MODEL = "google/gemini-2.5-flash-preview" #qwen/qwq-32b:free  #google/gemma-3-27b-it:free
DEFAULT_MAX_TOKENS = 4000  # Increased token limit for more detailed responses
DEFAULT_TEMPERATURE = 0.1  # Lower temperature for more precise, consistent code generation

# Request settings
REQUEST_TIMEOUT = 60  # Increased timeout for complex generations
MAX_RETRIES = 5  # More retries for better reliability

# Optional settings
ENABLE_LOGGING = True  # Enable/disable logging
LOG_LEVEL = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Proxy settings (if needed)
USE_PROXY = False
PROXY_URL = ""  # Proxy URL if needed

# Rate limiting settings
RATE_LIMIT_REQUESTS = 100  # Maximum requests per time window
RATE_LIMIT_WINDOW = 60  # Time window in seconds

# Manim-specific settings
MANIM_PACKAGES = [
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
