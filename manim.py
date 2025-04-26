# parser.py
import asyncio
import os
import json
import re
import sys
import platform
import random
import html
import subprocess # For running Manim
# Removed: from gtts import gTTS (Now handled by manim-voiceover)
import numpy # Often used by Manim code
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Page, Error as PlaywrightError


# --- API Configuration ---
OPENROUTER_API_KEY = "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" # Replace with your actual key or load securely
OPENROUTER_API_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini" # Example model, adjust as needed

# --- Manim Requirement ---
print("[Requirement] Ensure Manim is installed and configured: pip install manim")
# <<< MODIFIED >>> Added manim-voiceover requirement
print("[Requirement] Ensure Manim Voiceover is installed: pip install manim-voiceover")
print("[Requirement] Ensure gTTS is installed (as a dependency for Manim Voiceover's GTTS service): pip install gtts")
print("[Requirement] Ensure ffmpeg and a LaTeX distribution are installed for Manim.")


# --- Configuration ---
AI_STUDIO_URL = "https://aistudio.google.com/" # Make sure this is still the target, or use the intended Gemini Pro URL
OUTPUT_DIR_BASE = "generated_course" # Base directory name
MAX_MANIM_RETRIES = 2 # Number of times to retry Manim generation/rendering if it fails

# <<< YOUR CHROME EXECUTABLE PATH >>>
# Example for Windows, adjust as needed
CHROME_EXECUTABLE_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe' # Ensure this path is correct

# <<< YOUR CHROME USER DATA DIRECTORY >>>
# Example for Windows, adjust as needed. Find yours via chrome://version
USER_DATA_DIR = r'C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data' # Adjust YourUsername!

# <<< --- REALISTIC USER AGENTS --- >>>
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]
REALISTIC_USER_AGENT = random.choice(REALISTIC_USER_AGENTS)
print(f"[Info] Using randomized User Agent: {REALISTIC_USER_AGENT}")

# --- Auto-detect USER_DATA_DIR ---
if not USER_DATA_DIR or "YourUsername" in USER_DATA_DIR: # Add check for placeholder
    print("[Warning] USER_DATA_DIR seems unset or uses placeholder. Attempting auto-detect...")
    USER_DATA_DIR = "" # Reset to trigger auto-detect logic if placeholder was used
    system = platform.system(); print(f"[Info] Auto-detecting User Data Directory for {system}...")
    try:
        if system == "Windows":
            user_data_root = os.getenv('LOCALAPPDATA', '')
            potential_dir = os.path.join(user_data_root, 'Google', 'Chrome', 'User Data') if user_data_root else ""
            if os.path.isdir(potential_dir): USER_DATA_DIR = potential_dir
        elif system == "Darwin": # macOS
            potential_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
            if os.path.isdir(potential_dir): USER_DATA_DIR = potential_dir
        elif system == "Linux":
            potential_paths = [
                os.path.expanduser('~/.config/google-chrome'),
                os.path.expanduser('~/.config/chromium')
            ]
            for path in potential_paths:
                if os.path.isdir(path):
                    USER_DATA_DIR = path
                    print(f"[Info] Found potential directory: {path}")
                    break
    except Exception as detect_err:
        print(f"[Warning] Error during auto-detection: {detect_err}")

    if not USER_DATA_DIR: print("[Warning] Could not determine default Chrome User Data Directory. Set USER_DATA_DIR manually.")
    elif "YourUsername" in USER_DATA_DIR: # Check again if auto-detect somehow failed or returned placeholder path
        print("[Error] Auto-detected path might still be incorrect. Please set USER_DATA_DIR manually.")
        sys.exit(1)


# Final Check after potential auto-detect
if not USER_DATA_DIR or not os.path.isdir(USER_DATA_DIR):
     print(f"[Error] Chrome User Data Directory invalid or not found: {USER_DATA_DIR}");
     print("Please set the USER_DATA_DIR variable in the script correctly.")
     sys.exit(1)
else: print(f"[Info] Using USER_DATA_DIR: {USER_DATA_DIR}")


# --- JavaScript to inject ---
# (Keep js_to_hide_automation as it was)
js_to_hide_automation = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [ { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '' } ], });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => ( parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters) );
    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
    Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
    try {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { return 'Intel Inc.'; } // UNMASKED_VENDOR_WEBGL
            if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; } // UNMASKED_RENDERER_WEBGL
            return getParameter(parameter);
        };
    } catch (e) { console.error('WebGL spoofing failed:', e); }
"""

# --- Helper Function ---
def sanitize_filename(name):
    if not isinstance(name, str): name = str(name)
    # Allow underscores in the base ID part
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name).lower()
    # Keep only letters, numbers, underscore, dot, hyphen
    name = re.sub(r'[^a-z0-9_.-]', '', name)
    # Ensure it doesn't start with a hyphen or dot if it might be the only char
    if name.startswith(('-', '.')): name = '_' + name[1:]
    # Prevent excessively long names
    return name[:100] if len(name) > 100 else name


# --- Reusable AI Studio Interaction Function ---
# (Keep interact_with_ai_studio as it was - the parsing is done in main)
async def interact_with_ai_studio(
    page: Page,
    prompt_text: str,
    task_description: str,
    temperature: float,
    top_p: float,
    top_k: int,
    max_tokens: int
) -> str | None:
    """Finds input, clears, types prompt, adds delay, clicks run, polls for response content, extracts."""
    print(f"    [AI Interaction] Starting: {task_description}")
    max_retries = 2
    for attempt in range(max_retries):
        print(f"      Attempt {attempt + 1}/{max_retries}...")
        try:
            if not page or page.is_closed():
                 print("      [Error] Page is closed at start of interaction attempt.")
                 return None

            # Small random delay before interaction
            await page.wait_for_timeout(random.randint(100, 400))

            # 1. Locate Input Area & Clear/Fill
            input_selector = 'ms-autosize-textarea textarea'
            input_locator = page.locator(input_selector).first
            await input_locator.wait_for(state="visible", timeout=30000)
            await input_locator.scroll_into_view_if_needed(timeout=5000)
            await page.wait_for_timeout(random.randint(50, 200)) # Wait after scroll

            # Attempt to clear and fill
            await input_locator.fill("") # Clear existing content
            await page.wait_for_timeout(random.randint(50, 150)) # Wait after clear
            print(f"      Filling prompt ({len(prompt_text)} chars)...")
            await input_locator.fill(prompt_text)
            await input_locator.dispatch_event('input') # Trigger input event after filling
            print(f"      Prompt entered.")
            await input_locator.focus() # Ensure focus
            await page.wait_for_timeout(random.randint(200, 500)) # Wait after filling

            # 2. Modify Settings (CURRENTLY DISABLED - Keep as is unless needed)
            # print("      Skipping settings modification.")
            # Add code here to interact with sliders/dropdowns if needed in the future

            # 3. Locate Submit Button
            submit_selector = 'run-button button[type="submit"]'
            submit_locator = page.locator(submit_selector).first
            await submit_locator.scroll_into_view_if_needed(timeout=5000)
            await page.wait_for_timeout(random.randint(50, 200)) # Wait after scroll
            await submit_locator.wait_for(state="visible", timeout=15000)
            print("      Submit element visible.")
            # Optionally check if enabled, though clicking might handle it
            # is_enabled = await submit_locator.is_enabled(timeout=5000)
            # print(f"      Submit button enabled: {is_enabled}")

            # 4. Human-like Delay BEFORE Clicking Submit
            pre_click_delay = random.randint(800, 1800) # Milliseconds
            print(f"      Pausing for {pre_click_delay}ms before clicking submit...")
            await page.wait_for_timeout(pre_click_delay)

            # 5. Click Submit Button (Using JavaScript click for robustness)
            print(f"      Simulating random mouse movement before click...")
            try:
                # Simulate some plausible mouse movements before the click action
                viewport_size = page.viewport_size
                if viewport_size:
                    for _ in range(random.randint(1, 3)): # 1 to 3 small movements
                        # Target coordinates somewhere plausible on the lower part of the screen
                        move_target_x = random.uniform(viewport_size['width'] * 0.3, viewport_size['width'] * 0.7)
                        move_target_y = random.uniform(viewport_size['height'] * 0.6, viewport_size['height'] * 0.9)
                        await page.mouse.move(move_target_x, move_target_y, steps=random.randint(5, 20))
                        await page.wait_for_timeout(random.randint(50, 200))
                else:
                    print("       [Warning] Viewport size not available for mouse simulation.")
            except Exception as mouse_err:
                print(f"       [Warning] Error during mouse simulation: {mouse_err}")

            print(f"      Executing JavaScript to click submit element...")
            await page.evaluate(f"""
                const btn = document.querySelector('{submit_selector}');
                if (btn) {{
                    console.log('Clicking submit button via JS');
                    btn.click();
                }} else {{
                    console.error('Submit button not found for JS click');
                }}
            """)
            print(f"      JavaScript click executed.")
            # await page.wait_for_timeout(random.randint(100, 300)) # Short pause after click

            # --- Check for Immediate 'Internal Error' Message ---
            print(f"      Checking for immediate 'internal error' message (briefly)...")
            error_selector = "div.model-error" # Selector for the error div
            try:
                 # Wait a short, variable time for the error message to potentially appear
                 await page.wait_for_timeout(random.randint(500, 1200))
                 error_locator = page.locator(error_selector).first
                 if await error_locator.count() > 0 and await error_locator.is_visible(timeout=500): # Check visibility briefly
                     error_text = await error_locator.inner_text(timeout=500)
                     if "internal error has occurred" in error_text.lower():
                         print("      [DETECTION] 'Internal error' message found immediately after submit.")
                         raise ValueError("Detected 'internal error' message.") # Treat as failure
                     else:
                         # Log other errors but might not be fatal yet
                         print(f"      [Info] Found other model error message immediately: {error_text[:100]}...")
            except PlaywrightTimeoutError:
                 print("      No immediate error message detected.")
            except PlaywrightError as pe:
                 # Ignore "Target closed" as it's handled later, log others
                 if "Target closed" not in str(pe):
                     print(f"      PlaywrightError checking for immediate error: {pe}.")
                 # Continue, as this check is brief and might fail legitimately

            # --- Wait for Generation Completion ---
            print(f"      Polling Run/Stop button state for completion...")
            generation_complete = False
            submit_button_label_selector = 'run-button button[type="submit"] span.label' # Find the text span within the button
            max_completion_wait_attempts = 180 # Max attempts (e.g., 180 * 2.5s = 450s = 7.5 mins)
            completion_polling_interval = 2.5 # Seconds between checks

            for completion_attempt in range(max_completion_wait_attempts):
                try:
                    if not page or page.is_closed():
                        raise ConnectionError("Page closed during generation polling")

                    label_locator = page.locator(submit_button_label_selector).first
                    if await label_locator.count() > 0:
                        button_text = await label_locator.inner_text(timeout=1000) # Short timeout for text fetch
                        # Check if button text is back to "Run" (case-insensitive, trimmed)
                        if button_text.strip().lower() == "run":
                            print(f"        Button text is 'Run'. Generation complete. (Attempt {completion_attempt + 1})")
                            generation_complete = True
                            break # Exit polling loop
                        # else: print(f"        Button text: '{button_text}'. Still generating...") # Optional debug logging
                    else:
                         print(f"        Submit button label not found (Attempt {completion_attempt + 1}).")
                         # Could indicate a page state issue, but we continue polling for now

                    # Wait before next poll
                    await asyncio.sleep(completion_polling_interval)

                except ConnectionError as ce:
                    # If page closed, propagate the error immediately
                    raise ce
                except Exception as e:
                    # Log other errors during polling but continue if possible
                    if page and not page.is_closed() and "Target closed" not in str(e):
                        print(f"        [Polling Info] Error during button check: {e}")
                    elif not page or page.is_closed():
                        # If page closed during the error handling, raise ConnectionError
                        raise ConnectionError("Page closed during polling exception handling")
                    # Wait before retrying the poll check after an error
                    await asyncio.sleep(completion_polling_interval)

            if not generation_complete:
                print("      [Error] Timed out waiting for generation completion (Run button didn't reappear).");
                # Capture screenshot if page is still available
                if page and not page.is_closed():
                    try:
                        await page.screenshot(path=f"error_screenshot_{sanitize_filename(task_description)}_completion_timeout.png")
                        print("        Screenshot saved for timeout.")
                    except Exception as screen_err: print(f"        Failed to save screenshot: {screen_err}")
                raise ValueError("Timed out waiting for AI generation.") # Treat as failure

            # --- Wait AFTER Completion ---
            post_completion_delay = random.randint(4000, 6000) # Wait 4-6 seconds for content to fully render/settle
            print(f"        Generation complete detected. Pausing {post_completion_delay/1000:.1f}s before extraction...")
            await page.wait_for_timeout(post_completion_delay)

            # --- Extraction Logic ---
            print(f"      Extracting final response content...")
            response_text = None
            max_extraction_attempts = 5 # Try extraction a few times if it fails initially
            extraction_polling_interval = 1.5 # Seconds between extraction attempts

            # Selectors for potential content elements within the last model response
            model_turn_selector = "div.chat-turn-container.model" # The container for the AI's response
            # Common elements where text appears (adjust based on AI Studio structure if it changes)
            content_selectors = [
                "ms-code-block code",           # Code blocks
                "ms-text-chunk > ms-cmark-node > p", # Paragraphs
                "ms-text-chunk > ms-cmark-node > span",# Spans (sometimes used)
                "ms-text-chunk > ms-cmark-node > ol > li", # Ordered list items
                "ms-text-chunk > ms-cmark-node > ul > li", # Unordered list items
                "ms-text-chunk > ms-cmark-node"       # Catch-all for direct markdown nodes if others fail
            ]
            combined_content_selector = ", ".join(content_selectors) # Combine into one selector string

            for extract_attempt in range(max_extraction_attempts):
                print(f"        Extraction attempt {extract_attempt + 1}/{max_extraction_attempts}...")
                try:
                    if not page or page.is_closed():
                        raise ConnectionError("Page closed during extraction attempt")

                    # Locate the last response turn from the model
                    last_model_turn = page.locator(model_turn_selector).last
                    if await last_model_turn.count() == 0:
                        print(f"        Last model turn container not found.");
                        await asyncio.sleep(extraction_polling_interval); continue # Try again after delay

                    # Find all potential content elements within that last turn
                    all_content_elements = last_model_turn.locator(combined_content_selector)
                    count = await all_content_elements.count()

                    if count > 0:
                        print(f"        Found {count} potential content elements in the last model turn.")
                        extracted_parts = []
                        for i in range(count):
                            element = all_content_elements.nth(i)
                            try:
                                # Check if element is visible before extracting text
                                if await element.is_visible(timeout=500): # Brief check
                                    part_text = await element.inner_text(timeout=1000) # Extract text
                                    if part_text: # Check if text is not empty
                                        cleaned_part = html.unescape(part_text).strip() # Clean HTML entities and whitespace
                                        if cleaned_part: # Ensure it's not just whitespace after cleaning
                                            extracted_parts.append(cleaned_part)
                                # else: print(f"          Element {i} not visible.") # Optional debug
                            except Exception as el_ex:
                                # Handle potential errors during element processing (e.g., element detached)
                                if page.is_closed(): raise ConnectionError("Page closed during element processing")
                                elif "Target closed" not in str(el_ex):
                                    print(f"          [Warn] Error processing content element {i}: {el_ex}")
                                # Continue to the next element

                        if extracted_parts:
                            # Join the extracted parts, clean up multiple newlines
                            response_text = "\n".join(extracted_parts).strip()
                            response_text = re.sub(r'\n{3,}', '\n\n', response_text) # Consolidate excessive newlines
                            print("        [Success] Extracted and combined text from elements."); break # Exit extraction loop on success
                        else:
                            print("        [Warn] Found elements, but no visible text extracted from them.");
                            response_text = None # Ensure it's None if no text found
                    else:
                        print(f"        No content elements matching selectors found in the last model turn.")

                except ConnectionError as ce:
                    # Propagate connection errors immediately
                    raise ce
                except Exception as extract_ex:
                    # Log other extraction errors
                    if page.is_closed(): raise ConnectionError("Page closed during extraction exception handling")
                    elif "Target closed" not in str(extract_ex):
                        print(f"        [Warn] Error during extraction process: {extract_ex}")

                # If extraction failed or yielded no text, wait before retrying
                if response_text is None:
                    print(f"        Extraction attempt {extract_attempt + 1} failed or yielded no text. Waiting...")
                    await asyncio.sleep(extraction_polling_interval)

            # After all extraction attempts
            if response_text is None or not response_text.strip():
                 print("      [Error] Failed to extract valid response text after multiple attempts.");
                 if page and not page.is_closed():
                    try:
                         await page.screenshot(path=f"error_screenshot_{sanitize_filename(task_description)}_extraction_failed.png")
                         print("        Screenshot saved for extraction failure.")
                    except Exception as screen_err: print(f"        Failed to save screenshot: {screen_err}")
                 raise ValueError("Failed to extract response content.") # Treat as failure

            print(f"    [AI Interaction] Success: {task_description}")
            return response_text # Return the extracted text

        # --- Error Handling within the retry loop ---
        except ConnectionError as ce:
            print(f"      [Error] Interaction failed (Connection Closed): {ce}")
            return None # Cannot retry if connection is lost
        except ValueError as ve:
            # Handle specific ValueErrors like "internal error" or timeouts
            if "Detected 'internal error'" in str(ve):
                print(f"      [Error] Detected internal error message (Attempt {attempt + 1}). Aborting interaction.")
                return None # Don't retry on explicit internal error
            else:
                print(f"      [Error] ValueError (Attempt {attempt + 1}): {ve}")
                if attempt + 1 == max_retries:
                    print(f"        Max retries reached for ValueError.")
                    return None # Failed after retries
                else:
                    print("        Retrying interaction after delay...");
                    await asyncio.sleep(random.randint(7, 15)) # Wait longer before retrying
        except PlaywrightTimeoutError as e:
            print(f"      [Error] Playwright Timeout (Attempt {attempt + 1}): {e}")
            if attempt + 1 == max_retries:
                print(f"        Max retries reached for Timeout.")
                if page and not page.is_closed():
                    try:
                        await page.screenshot(path=f"error_screenshot_{sanitize_filename(task_description)}_timeout.png")
                        print("        Screenshot saved for timeout.")
                    except Exception as screen_err: print(f"        Failed screenshot on timeout: {screen_err}")
                return None # Failed after retries
            else:
                print("        Retrying interaction after delay...");
                await asyncio.sleep(random.randint(7, 15)) # Wait longer before retrying
        except Exception as e:
            # Handle unexpected errors
            err_msg = str(e)
            is_target_closed = "Target closed" in err_msg or (page and page.is_closed())

            if not is_target_closed:
                 # Log unexpected errors if the page is still seemingly open
                 print(f"      [Error] Unexpected error (Attempt {attempt + 1}): {e}")
                 import traceback; traceback.print_exc() # Print stack trace for debugging
                 # Try to take a screenshot
                 if page and not page.is_closed():
                    try:
                         await page.screenshot(path=f"error_screenshot_{sanitize_filename(task_description)}_unexpected.png")
                         print("        Screenshot saved for unexpected error.")
                    except Exception as screen_err: print(f"        Failed screenshot on unexpected error: {screen_err}")
            elif is_target_closed:
                 # If the error is due to the target being closed, treat it like a ConnectionError
                 print(f"      [Error] Interaction failed (Target Closed during operation) (Attempt {attempt + 1}): {e}")
                 return None # Cannot retry

            # Decide whether to retry for unexpected errors (if target not closed)
            if not is_target_closed and attempt + 1 < max_retries:
                print("        Retrying interaction after unexpected error...");
                await asyncio.sleep(random.randint(10, 20)) # Wait even longer
            elif not is_target_closed:
                print("        Max retries reached after unexpected error.")
                return None # Failed after retries


    # If loop finishes without returning successfully
    print(f"    [AI Interaction] Failed after {max_retries} attempts: {task_description}")
    return None


# --- Main Async Function ---
async def main():
    # --- Get Course Topic ---
    COURSE_TOPIC = input("Enter the course topic (e.g., 'Fundamentals of Quantum Computing'): ")
    if not COURSE_TOPIC: print("[Error] Course topic cannot be empty."); return
    print(f"[Info] Using course topic: {COURSE_TOPIC}")

    # --- Setup Output Directory ---
    OUTPUT_DIR = os.path.join(OUTPUT_DIR_BASE, sanitize_filename(COURSE_TOPIC))
    OVERVIEW_FILE = os.path.join(OUTPUT_DIR, "course_overview_generated.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[Info] Output directory: {OUTPUT_DIR}")

    # --- Initial Setup ---
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! IMPORTANT: CLOSE ALL CHROME BROWSER WINDOWS *BEFORE*    !!!")
    print("!!! running this script to avoid profile lock errors.       !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    user_input = input("Press Enter to continue if Chrome is closed, or Ctrl+C to abort...")
    if not CHROME_EXECUTABLE_PATH or not os.path.exists(CHROME_EXECUTABLE_PATH): print(f"[Error] Chrome executable path invalid: {CHROME_EXECUTABLE_PATH}"); return
    if not USER_DATA_DIR or not os.path.isdir(USER_DATA_DIR): print(f"[Error] Chrome User data dir invalid: {USER_DATA_DIR}"); return
    print("[Setup] Initializing Playwright...")
    p = None; browser_context = None; page = None

    try:
        async with async_playwright() as p_context:
            p = p_context

            # --- launch_and_setup_browser (nested function) ---
            async def launch_and_setup_browser():
                nonlocal browser_context, page, p # Allow modification of outer scope variables
                if browser_context:
                    print("[Launch] Closing previous browser context if exists...")
                    try: await browser_context.close()
                    except Exception as close_err: print(f"  [Warn] Error closing previous context: {close_err}")
                    browser_context, page = None, None
                    await asyncio.sleep(random.uniform(1.5, 3.0)) # Wait after closing

                print(f"[Launch] Attempting to start Chrome with User Data: {USER_DATA_DIR}")
                try:
                    current_user_agent = random.choice(REALISTIC_USER_AGENTS) # Choose a new UA each time
                    print(f"[Info] Using User Agent for this launch: {current_user_agent}")
                    browser_context = await p.chromium.launch_persistent_context(
                        user_data_dir=USER_DATA_DIR,
                        headless=False, # Must be False to interact with AI Studio UI
                        executable_path=CHROME_EXECUTABLE_PATH,
                        accept_downloads=False, # Generally not needed for this task
                        user_agent=current_user_agent,
                        # Recommended args for stability and avoiding detection
                        args=[
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--start-maximized', # Start maximized for better element visibility
                            '--disable-blink-features=AutomationControlled', # Key anti-detection flag
                            '--disable-infobars', # Hide "Chrome is being controlled..."
                            '--disable-features=IsolateOrigins,site-per-process,TargetedMSAFixedPoint', # Potential stability/detection improvements
                            # '--force-device-scale-factor=1', # Can sometimes help with rendering consistency
                        ],
                        # Ignore default args that might reveal automation
                        ignore_default_args=["--enable-automation"],
                        # Set a realistic viewport size
                        viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)}
                    )
                    print("[Launch] Browser context launched.")
                    await asyncio.sleep(random.uniform(1.0, 2.0)) # Wait for browser to settle

                    # Get the primary page or create one
                    pages = browser_context.pages
                    page = pages[0] if pages else await browser_context.new_page()
                    if not page: raise RuntimeError("Failed to get a page from the browser context.")
                    print("[Launch] Got browser page.")
                    await page.bring_to_front() # Ensure it's the active window

                    # Inject anti-detection scripts on initialization
                    await page.add_init_script(js_to_hide_automation)
                    print("[Inject] Anti-detection JS injected via add_init_script.")

                    # Navigate to the target URL
                    print(f"[Navigate] Going to {AI_STUDIO_URL}...")
                    await page.goto(AI_STUDIO_URL, timeout=90000, wait_until="domcontentloaded") # Increased timeout, wait for DOM
                    print("[Navigate] Navigation initiated. Waiting for page load and elements...")
                    await page.wait_for_timeout(random.randint(2000, 3500)) # Wait after initial load

                    # Wait for a key element of the AI Studio UI to be ready
                    print("[Wait] Waiting for main interface element (textarea)...")
                    await page.wait_for_selector('ms-autosize-textarea textarea', state="visible", timeout=45000) # Wait for input area
                    print("  [Success] Main interface detected.")

                    # Add event listeners for debugging (optional)
                    page.on("close", lambda: print("[Event Listener] Page closed event detected."))
                    browser_context.on("close", lambda: print("[Event Listener] Browser context closed event detected."))

                    return True # Indicate successful launch and setup

                except PlaywrightError as launch_err:
                    err_str = str(launch_err).lower()
                    # Check specifically for the profile lock error
                    if "user data directory is already in use" in err_str or "lock" in err_str:
                        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                        print("[CRITICAL ERROR] Chrome User Data Directory is LOCKED!")
                        print("This usually means another Chrome instance using the same profile is open.")
                        print(f"Profile path: {USER_DATA_DIR}")
                        print("Please CLOSE ALL Chrome windows and try running the script again.")
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                        # Re-raise the specific error to stop the script cleanly
                        raise launch_err
                    else:
                        # Log other Playwright launch errors
                        print(f"[CRITICAL Launch Error] Playwright error during launch: {launch_err}")

                    # Attempt cleanup if context was partially created
                    if browser_context: await browser_context.close()
                    browser_context, page = None, None
                    return False # Indicate launch failure
                except Exception as general_launch_err:
                     # Catch any other unexpected errors during launch
                     print(f"[CRITICAL Launch Error] Unexpected error during launch: {general_launch_err}")
                     if browser_context: await browser_context.close()
                     browser_context, page = None, None
                     return False # Indicate launch failure

            # --- New function to send error details to API (defined within main scope) ---
            async def send_error_to_api(manim_code: str, error_output: str, api_key: str, base_url: str, model: str) -> str:
               """Sends Manim code and error output to an API for analysis."""
               prompt = f"""
               The following Manim Python code failed to render. Please analyze the code and the provided error output and suggest potential fixes.

               Manim Code:
               ```python
               {manim_code}
               ```

               Manim Error Output:
               ```text
               {error_output}
               ```

               Provide specific suggestions for modifying the Manim code to resolve the error. Focus on common Manim issues like incorrect object usage, animation conflicts, missing imports, or syntax errors based on the traceback.
               """

               headers = {
                   "Authorization": f"Bearer {api_key}",
                   "Content-Type": "application/json",
                   "HTTP-Referer": "https://github.com/Rvexi/AISHIT-MANUM", # Replace with your actual repo URL
                   "X-Title": "AISHIT-MANUM Manim Error Analyzer", # Replace with your app name
               }

               payload = {
                   "model": model,
                   "messages": [
                       {"role": "user", "content": prompt}
                   ]
               }

               try:
                   async with httpx.AsyncClient() as client:
                       response = await client.post(
                           f"{base_url}/chat/completions",
                           json=payload,
                           headers=headers,
                           timeout=60.0 # Set a reasonable timeout
                       )
                       response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                       response_data = response.json()
                       # Extract the content from the API response
                       if response_data and response_data.get("choices"):
                           return response_data["choices"][0].get("message", {}).get("content", "No specific suggestions provided by API.")
                       else:
                           return "API response did not contain expected format."

               except httpx.RequestError as e:
                   return f"API Request Error: {e}"
               except httpx.HTTPStatusError as e:
                   return f"API HTTP Error: {e.response.status_code} - {e.response.text}"
               except Exception as e:
                   return f"An unexpected error occurred during API call: {e}"


            # ================================================
            # --- Task 1: Generate Course Overview ---
            # ================================================
            print("\n[Task 1] Generating Course Overview...")
            # Updated prompt for clarity and robustness
            overview_prompt_for_ai_studio = f"""
            Act as an expert curriculum designer. Create a course outline for a comprehensive course titled "{COURSE_TOPIC}".

            **Requirements:**
            1.  **Structure:** The output MUST be a single, valid JSON object.
            2.  **Content:**
                *   Include a top-level key `"course_title"` with the value "{COURSE_TOPIC}".
                *   Include a top-level key `"chapters"` which is a list containing 10 to 15 chapter objects.
                *   Each chapter object MUST have two keys:
                    *   `"title"`: (string) The full, descriptive chapter title (e.g., "Chapter 1: Introduction to Core Concepts").
                    *   `"id"`: (string) A concise, unique identifier suitable for filenames, using lowercase snake_case (e.g., "ch01_intro_concepts"). Ensure IDs are unique.
            3.  **Formatting:**
                *   Generate ONLY the JSON object.
                *   Do NOT include any introductory text, explanations, comments, or markdown backticks (```json ... ```) around the JSON.
                *   Ensure the JSON is perfectly valid (correct commas, braces, brackets, quotes).

            **Example JSON Structure:**
            ```json
            {{
              "course_title": "Example Topic",
              "chapters": [
                {{
                  "title": "Chapter 1: First Topic",
                  "id": "ch01_first_topic"
                }},
                {{
                  "title": "Chapter 2: Second Topic Details",
                  "id": "ch02_second_topic_details"
                }}
                // ... more chapters ...
              ]
            }}
            ```

            Generate the JSON object for the course "{COURSE_TOPIC}" now.
            """
            # AI Studio parameters (adjust if needed)
            temp=0.7; top_p=0.95; top_k=40; max_tokens=2048
            overview_raw_text = None; overview_data = None; max_task1_retries = 3

            for task1_attempt in range(max_task1_retries):
                print(f"\n[Task 1] Attempt {task1_attempt + 1}/{max_task1_retries}...")
                # Ensure browser is running before starting the attempt
                if not browser_context or not page or page.is_closed():
                    print(f"  Attempting to launch browser for Task 1...")
                    if not await launch_and_setup_browser():
                        print(f"  Browser launch failed. Waiting before next retry...")
                        await asyncio.sleep(10) # Wait before retrying launch
                        continue # Go to next attempt
                    else:
                        print("  Browser launched successfully.")

                try:
                    # Double-check page status
                    if page.is_closed():
                        raise ConnectionError("Page closed unexpectedly before Task 1 interaction attempt.")

                    # Check if we are on the right page, navigate if needed
                    current_url = page.url
                    if not current_url or not current_url.startswith(AI_STUDIO_URL):
                        print(f"  Not on AI Studio URL (current: {current_url}). Re-navigating...")
                        try:
                            await page.goto(AI_STUDIO_URL, timeout=90000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(random.randint(1500, 3000)) # Wait after navigation
                            # Re-verify key element after navigation
                            await page.wait_for_selector('ms-autosize-textarea textarea', state="visible", timeout=30000)
                            print("  Re-navigation successful.")
                        except Exception as nav_err:
                            print(f"  Error during re-navigation: {nav_err}")
                            raise ConnectionError("Failed to re-navigate to AI Studio.") # Treat as connection issue

                    # Perform the AI interaction
                    overview_raw_text = await interact_with_ai_studio(
                        page, overview_prompt_for_ai_studio, "Course Overview Generation",
                        temp, top_p, top_k, max_tokens
                    )

                    # --- START: MODIFIED JSON Parsing Logic (Indentation Corrected) ---
                    if overview_raw_text is not None:
                        print("  AI interaction successful. Attempting to parse JSON...")
                        overview_data = None
                        remaining_text = overview_raw_text

                        try:
                            # 1. Look for ```json ... ``` code block first
                            json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', remaining_text, re.IGNORECASE)
                            if json_match:
                                print("    Found JSON within ```json code block.")
                                json_text_to_parse = json_match.group(1).strip()
                                try:
                                    overview_data = json.loads(json_text_to_parse)
                                    # Basic validation of structure
                                    if isinstance(overview_data, dict) and \
                                       "course_title" in overview_data and \
                                       "chapters" in overview_data and \
                                       isinstance(overview_data["chapters"], list):
                                        print("  [Success] Parsed valid JSON structure from code block.")
                                        break # SUCCESS - Exit Task 1 retry loop
                                    else:
                                        print("  [Warning] Parsed JSON from code block, but structure is invalid. Trying other methods.")
                                        overview_data = None # Reset and try fallback
                                except json.JSONDecodeError:
                                    print("  [Warning] Failed to parse JSON from ```json block. Trying other methods.")
                                    overview_data = None # Reset and try fallback

                            # 2. If no code block or parsing failed, iterate through potential JSON objects
                            if overview_data is None:
                                print("    Attempting to find and parse JSON object(s) in raw text.")
                                search_start_index = 0
                                while search_start_index < len(remaining_text):
                                    first_brace_index = remaining_text.find('{', search_start_index)
                                    if first_brace_index == -1:
                                        print("    No more '{' found in the remaining text.")
                                        break # No more potential JSON objects

                                    potential_json_start = remaining_text[first_brace_index:]
                                    last_brace_index_in_potential = potential_json_start.rfind('}')

                                    if last_brace_index_in_potential != -1:
                                        json_text_to_parse = potential_json_start[:last_brace_index_in_potential + 1].strip()
                                        print(f"    Found potential JSON from index {first_brace_index} to {first_brace_index + last_brace_index_in_potential}. Attempting to parse...")
                                        try:
                                            temp_data = json.loads(json_text_to_parse)
                                            # Basic validation of structure
                                            if isinstance(temp_data, dict) and \
                                               "course_title" in temp_data and \
                                               "chapters" in temp_data and \
                                               isinstance(temp_data["chapters"], list):
                                                print("  [Success] Parsed valid JSON structure from raw text.")
                                                overview_data = temp_data # Found valid data
                                                break # SUCCESS - Exit search loop
                                            else:
                                                print("    Parsed potential JSON, but structure is invalid. Continuing search.")
                                                search_start_index = first_brace_index + 1 # Continue search after this '{'
                                        except json.JSONDecodeError:
                                            print("    Failed to parse potential JSON. Continuing search.")
                                            search_start_index = first_brace_index + 1 # Continue search after this '{'
                                        except Exception as inner_parse_ex:
                                            print(f"    [Warning] Unexpected error during inner parsing attempt: {inner_parse_ex}. Continuing search.")
                                            search_start_index = first_brace_index + 1 # Continue search after this '{'
                                    else:
                                        print("    Found '{' but no matching '}' in the rest of the text. Stopping search.")
                                        break # No matching '}' found

                            # 3. After all attempts, check if valid data was found
                            if overview_data:
                                print("  [Success] Successfully extracted and parsed JSON data.")
                                break # SUCCESS - Exit Task 1 retry loop
                            else:
                                # If no valid JSON was found after all attempts
                                raise json.JSONDecodeError("Failed to extract a valid JSON object from the response.", overview_raw_text or "", 0)


                        except json.JSONDecodeError as parse_e:
                            print(f"  [Error] JSON parsing failed after all extraction attempts: {parse_e}")
                            print(f"  Raw text received (first 500 chars):\n'''\n{overview_raw_text[:500]}...\n'''") # Log raw text for debugging
                            # Save the raw response for debugging if parsing fails
                            raw_file = os.path.join(OUTPUT_DIR, f"course_overview_RAW_UNPARSED_attempt_{task1_attempt+1}.txt")
                            try:
                                with open(raw_file, 'w', encoding='utf-8') as f: f.write(overview_raw_text)
                                print(f"  Raw unparseable text saved: {raw_file}")
                            except Exception as save_err: print(f"  Failed to save raw text: {save_err}")
                            overview_data = None # Ensure data is None if parsing failed
                        except Exception as general_parse_e:
                            print(f"  [Error] Unexpected error during parsing/validation: {general_parse_e}")
                            import traceback; traceback.print_exc() # Add traceback
                            overview_data = None

                        # If parsing/validation failed after successful interaction, it might indicate AI non-compliance.
                        # Closing the browser might help reset state for the next attempt.
                        if overview_data is None:
                            print("  Parsing/Validation failed. Closing browser context before retry...")
                            if browser_context:
                                try: await browser_context.close(); print("  Context closed.")
                                except Exception as close_err: print(f"  Error closing context: {close_err}")
                            browser_context, page = None, None
                            await asyncio.sleep(random.randint(5, 10)) # Wait before next attempt (which will re-launch)
                            # Loop continues to next attempt

                    # --- END: MODIFIED JSON Parsing Logic ---
                    else: # interact_with_ai_studio returned None (likely detection or critical error)
                        print("  AI interaction failed (returned None). Browser context might be compromised.")
                        # Assume browser is dead, close it if possible, and wait before retry
                        if browser_context:
                            print("  Closing browser context...")
                            try: await browser_context.close(); print("  Context closed.")
                            except Exception as close_err: print(f"  Error closing context: {close_err}")
                        browser_context, page = None, None
                        await asyncio.sleep(10)

                except ConnectionError as ce:
                    # Handle cases where the page/connection died during the attempt
                    print(f"  [Error] Task 1 ConnectionError (Attempt {task1_attempt + 1}): {ce}")
                    if browser_context: await browser_context.close(); browser_context, page = None, None
                    await asyncio.sleep(5) # Wait before next attempt (which will re-launch)
                except Exception as task1_ex:
                    # Catch other unexpected errors during the task attempt
                    print(f"  [Error] Task 1 Unexpected error (Attempt {task1_attempt + 1}): {task1_ex}")
                    if page and not page.is_closed():
                        try: await page.screenshot(path=f"error_screenshot_task1_attempt_{task1_attempt+1}.png")
                        except Exception: pass
                    # Close context before retrying after unexpected error
                    if browser_context: await browser_context.close(); browser_context, page = None, None
                    await asyncio.sleep(random.randint(10, 15)) # Longer wait after unexpected error


            # --- After Task 1 Retry Loop ---
            if overview_data:
                print("\n[Task 1] Successfully generated and parsed course overview.")
                try:
                    with open(OVERVIEW_FILE, 'w', encoding='utf-8') as f: json.dump(overview_data, f, indent=4)
                    print(f"  Saved course overview to: {OVERVIEW_FILE}")
                except Exception as save_e:
                    print(f"  [Error] Failed to save overview JSON: {save_e}")
                    # Proceed anyway if data is in memory, but log the error
            else:
                print("\n[Error] Failed to generate course overview after multiple attempts. Cannot proceed.")
                # Use raise RuntimeError to stop the script cleanly if overview failed
                raise RuntimeError("Failed to generate course overview.")


            # ================================================
            # --- Task 2 & 3: Generate Chapter Scripts & Manim Code ---
            # ================================================
            # Check if overview succeeded AND browser is still valid before proceeding
            if overview_data and browser_context and page and not page.is_closed():
                chapters = overview_data.get("chapters", [])
                if chapters:
                    print(f"\n[Task 2 & 3] Processing {len(chapters)} chapters...")
                    num_chapters = len(chapters)
                    for i, chapter in enumerate(chapters):
                        # --- Chapter Setup ---
                        chapter_title = chapter.get("title", f"Untitled Chapter {i+1}").strip()
                        # Generate chapter_id_base from title if 'id' is missing or invalid
                        raw_id = chapter.get("id", "").strip()
                        if not raw_id:
                            chapter_id_base = sanitize_filename(chapter_title)
                            print(f"    [Info] Generated chapter ID base from title: '{chapter_id_base}'")
                        else:
                            chapter_id_base = sanitize_filename(raw_id) # Sanitize provided ID

                        # Ensure chapter_id_base is suitable for class names (more robust)
                        # 1. Remove leading non-alpha characters (allow underscore)
                        class_name_base = re.sub(r'^[^a-zA-Z_]+', '', chapter_id_base)
                        # 2. Replace invalid characters with underscore
                        class_name_base = re.sub(r'[^a-zA-Z0-9_]', '_', class_name_base)
                        # 3. Capitalize parts for CamelCase (split by underscore, capitalize, join)
                        class_name_base = "".join(part.capitalize() for part in class_name_base.split('_') if part)
                        # 4. Ensure it starts with a letter (prefix if needed)
                        if not class_name_base or not class_name_base[0].isalpha():
                            class_name_base = f"Chapter{i+1}{class_name_base}"
                        # 5. Fallback if everything else fails
                        if not class_name_base: class_name_base = f"Chapter{i+1}Default"

                        # Use sanitized/formatted base for class name
                        expected_scene_name = f"{class_name_base}Scene"
                        # Use original (but sanitized) base for file names, prefixed with index
                        chapter_id_for_files = f"{i+1:02d}_{chapter_id_base.lower()}"

                        print(f"\n--- Chapter {i+1}/{num_chapters}: {chapter_title} ---")
                        print(f"    File ID Prefix: {chapter_id_for_files}")
                        print(f"    Expected Manim Scene: {expected_scene_name}")


                        # --- Task 2: Generate Script ---
                        print(f"  [Task 2] Generating Text Script for '{chapter_title}'...")
                        script_raw_text = None; script_gen_success = False; script_filepath = None
                        max_script_retries = 2
                        for script_attempt in range(max_script_retries):
                            print(f"    Script Attempt {script_attempt + 1}/{max_script_retries}...")
                            try:
                                # Check browser state at the start of each attempt
                                if not browser_context or not page or page.is_closed():
                                    print(f"    [Error] Browser context/page invalid before script attempt. Stopping chapter processing.")
                                    chapters = [] # Signal to stop processing further chapters
                                    break # Exit script retry loop

                                # Re-check URL, navigate if necessary (less likely needed here but safe)
                                current_url = page.url
                                if not current_url or not current_url.startswith(AI_STUDIO_URL):
                                    print(f"    [Warn] Not on AI Studio URL. Re-navigating...");
                                    try:
                                        await page.goto(AI_STUDIO_URL, timeout=90000, wait_until="domcontentloaded")
                                        await page.wait_for_timeout(random.randint(1500, 2500))
                                        await page.wait_for_selector('ms-autosize-textarea textarea', state="visible", timeout=30000)
                                    except Exception as nav_err:
                                        print(f"    [Error] Failed re-navigation: {nav_err}")
                                        raise ConnectionError("Failed re-navigation during script generation.")

                                # Estimate target word count (adjust WPM as needed)
                                words_per_minute = 140 # Average speaking pace
                                target_duration_minutes = 10 # Aim for ~10 min video per chapter
                                target_word_count = words_per_minute * target_duration_minutes
                                word_count_range_upper = target_word_count + 300 # Allow some flexibility

                                script_prompt_for_ai_studio = f"""
                                Act as an expert educational scriptwriter creating content for a video course.
                                Your task is to write a detailed, engaging narration script for a video segment covering the topic: "{chapter_title}".

                                **Context:**
                                - Overall Course Topic: "{COURSE_TOPIC}"
                                - Target Audience: Assumed intelligent adults, motivated learners, but potentially new to this specific sub-topic.
                                - Desired Video Segment Length: Approximately {target_duration_minutes} minutes when spoken at a conversational pace ({words_per_minute} WPM).

                                **Script Requirements:**
                                1.  **Content:**
                                    *   Provide a clear introduction explaining the importance of "{chapter_title}" within the broader context of "{COURSE_TOPIC}".
                                    *   Explain key concepts thoroughly but accessibly. Use analogies or simple examples relevant to the main course topic where helpful.
                                    *   Maintain a logical flow from one idea to the next with smooth transitions.
                                    *   Include a brief summary or conclusion reinforcing the main takeaways.
                                2.  **Style:**
                                    *   Write in a conversational, engaging, and authoritative tone suitable for narration.
                                    *   Use clear, concise language. Avoid excessive jargon unless explained.
                                    *   Structure the script using paragraphs for readability.
                                3.  **Length:** Aim for approximately {target_word_count} to {word_count_range_upper} words.
                                4.  **Visual Hints (Optional but helpful):** You MAY include simple visual cues in brackets, like `[VISUAL: Show a simple diagram of X]` or `[VISUAL: Highlight keyword Y]`. These are hints for the animator; do NOT describe complex animations.
                                5.  **Output Format:** Output ONLY the raw narration script text. Do NOT include:
                                    *   Titles like "Script:" or "Chapter X Script".
                                    *   Scene headings, character names (e.g., "NARRATOR:").
                                    *   Word counts or duration estimates.
                                    *   Any introductory/concluding remarks outside the script itself (e.g., "Here is the script:").

                                Generate the narration script for "{chapter_title}" now.
                                """
                                # AI Studio parameters for script generation
                                temp_script=0.7; top_p_script=0.95; top_k_script=40; max_tokens_script=4090 # Use max tokens

                                # Interact with AI Studio
                                script_raw_text = await interact_with_ai_studio(
                                    page, script_prompt_for_ai_studio, f"Script: {chapter_id_for_files}",
                                    temp_script, top_p_script, top_k_script, max_tokens_script
                                )

                                # Process the result
                                if script_raw_text:
                                    cleaned_script = script_raw_text.strip()
                                    # Basic check for non-empty script
                                    if len(cleaned_script) > 100: # Arbitrary minimum length check
                                        script_filepath = os.path.join(OUTPUT_DIR, f"{chapter_id_for_files}_script.txt") # Save as .txt
                                        try:
                                            with open(script_filepath, 'w', encoding='utf-8') as f: f.write(cleaned_script)
                                            print(f"    [Success] Script saved: {script_filepath}")
                                            script_gen_success = True
                                            script_raw_text = cleaned_script # Use the cleaned version going forward
                                            break # Exit script retry loop on success
                                        except Exception as save_err:
                                            print(f"    [Error] Failed to save script file: {save_err}")
                                            # Continue to next retry if possible, but mark as failed for now
                                            script_gen_success = False
                                            script_raw_text = None
                                    else:
                                         print(f"    [Warn] Generated script seems too short ({len(cleaned_script)} chars). Saving raw response.")
                                         short_script_filepath = os.path.join(OUTPUT_DIR, f"{chapter_id_for_files}_script_RAW_SHORT_A{script_attempt+1}.txt")
                                         try:
                                              with open(short_script_filepath, 'w', encoding='utf-8') as f: f.write(script_raw_text) # Save original raw
                                              print(f"    Short/Raw script saved: {short_script_filepath}")
                                         except Exception: pass
                                         # Consider this a failure for retry purposes
                                         script_gen_success = False
                                         script_raw_text = None
                                else:
                                     # interact_with_ai_studio returned None
                                     print(f"    [Error] Script interaction failed (Returned None - likely detection) (Attempt {script_attempt + 1}).")
                                     # Assume browser is dead if interaction fails critically
                                     if browser_context: await browser_context.close(); browser_context, page = None, None
                                     print("    [Critical] Closing browser due to failed interaction. Stopping all tasks.")
                                     chapters = [] # Stop processing
                                     break # Exit script retry loop

                            except ConnectionError as ce:
                               print(f"    [Error] Page closed during script generation attempt {script_attempt+1}: {ce}")
                               if browser_context: await browser_context.close(); browser_context, page = None, None
                               chapters = []; break # Stop processing
                            except Exception as script_ex:
                                print(f"    [Error] Unexpected script generation error (Attempt {script_attempt + 1}): {script_ex}")
                                if page and not page.is_closed():
                                    try: await page.screenshot(path=f"error_screenshot_script_{chapter_id_for_files}_A{script_attempt+1}.png")
                                    except Exception: pass
                                # Decide whether to retry or give up
                                if script_attempt + 1 == max_script_retries:
                                    print(f"    [Error] Max retries reached for script generation. Skipping chapter.")
                                else:
                                    print("      Waiting before retrying script generation...")
                                    await asyncio.sleep(random.randint(5, 10))

                        if not chapters: break # Exit outer chapter loop immediately if browser died

                        # <<< --- TASK 2b (Separate gTTS Audio Generation) REMOVED --- >>>

                        # --- Task 3: Generate Manim Code (Using manim-voiceover) ---
                        if script_gen_success and script_raw_text:
                            print(f"  [Task 3] Generating Manim Code with Voiceover for '{chapter_title}'...")
                            manim_code_generated_and_rendered = False # Flag for this chapter's overall success
                            manim_filepath = None # Define here to be accessible after loop

                            for manim_attempt in range(MAX_MANIM_RETRIES):
                                print(f"    Manim Code Attempt {manim_attempt + 1}/{MAX_MANIM_RETRIES}...")
                                manim_raw_text = None; manim_code_saved = False
                                temp_manim=0.7; top_p_manim=0.95; top_k_manim=40; max_tokens_manim=4090 # Use max tokens

                                # Check browser state before starting Manim interaction attempt
                                if not browser_context or not page or page.is_closed():
                                    print(f"    [Error] Browser died before Manim attempt {manim_attempt+1}. Stopping chapter processing.")
                                    chapters = [] # Signal to stop outer loop
                                    break # Exit Manim retry loop for this chapter

                                # <<< MODIFIED MANIM PROMPT >>>
                                manim_prompt_for_ai_studio = f"""
                                Act as an expert Manim animator, skilled in creating educational animations with synchronized voiceovers using the `manim-voiceover` library.

                                **Task:** Generate a complete, runnable Python script using Manim and `manim-voiceover` to visually animate the key concepts from the provided script text. The animation should be synchronized with narration using Google Text-to-Speech (gTTS).

                                **Context:**
                                - Course Topic: {COURSE_TOPIC}
                                - Chapter Title: {chapter_title}
                                - Expected Scene Name: {expected_scene_name}

                                **Provided Narration Script Text:**
                                ```text
                                {script_raw_text[:3800]}
                                ```
                                (Note: Script may be truncated if very long. Focus on animating the provided portion.)

                                **CRITICAL Instructions:**
                                1.  **Framework:** Use Manim (`manim`) and the `manim-voiceover` extension.
                                2.  **Runnable Code:** Generate ONE complete Python script (`.py`). The script MUST run without errors using the command `manim <filename.py> {expected_scene_name}`.
                                3.  **Imports:** Start the script *exactly* with:
                                    ```python
                                    from manim import *
                                    from manim_voiceover import VoiceoverScene
                                    from manim_voiceover.services.gtts import GTTSService
                                    # Optional: import numpy as np (if needed)
                                    ```
                                4.  **Scene Class:** Define the Manim scene class *exactly* as:
                                    `class {expected_scene_name}(VoiceoverScene):`
                                    (It MUST inherit from `VoiceoverScene`).
                                5.  **Voiceover Setup:** Inside the `construct(self)` method, the *very first line* MUST be:
                                    `self.set_speech_service(GTTSService())`
                                    Optionally add `lang='en'` if needed: `self.set_speech_service(GTTSService(lang='en'))`.
                                6.  **Synchronization:**
                                    *   Break the provided script text into logical, sentence-like segments for narration.
                                    *   For EACH narration segment, use the `with self.voiceover(text="...") as vo:` context manager.
                                    *   Place the Manim animations (`self.play(...)`, `self.wait(...)` etc.) that correspond to that narration segment *inside* its `with self.voiceover(...) as vo:` block.
                                    *   Example:
                                      ```python
                                      with self.voiceover(text="First, let's introduce the concept.") as vo:
                                          concept_text = Text("Concept X").scale(1.5)
                                          self.play(Write(concept_text))
                                          # self.wait(vo.get_remaining_duration()) # Optional: Wait if animation finishes before speech
                                      ```
                                7.  **Animation Style:**
                                    *   Create clear, clean visuals (like 3Blue1Brown style).
                                    *   Use smooth transitions (`Write`, `FadeIn`, `Transform`, `Create`, `FadeOut`, `ReplacementTransform`).
                                    *   Visualize the main ideas and any `[VISUAL: ...]` hints from the script.
                                    *   Use standard Manim objects: `Text`, `MathTex`, `Tex`, `Line`, `Arrow`, `Circle`, `Square`, `Rectangle`, `Dot`, `NumberPlane`, `Axes`, `VGroup`. Manage object placement carefully to avoid overlaps unless intended (e.g., using `.shift()`, `.to_edge()`, `.next_to()`). Remove objects when done (`FadeOut`).
                                8.  **Restrictions:**
                                    *   ***ABSOLUTELY NO `SVGMobject` or `ImageMobject`.*** Do not attempt to load external image or SVG files. Use Manim's built-in capabilities only.
                                    *   Do not manually try to load or play audio files; `manim-voiceover` handles this.
                                9.  **Completeness:** Include the standard Manim execution block at the end:
                                    ```python
                                    if __name__ == "__main__":
                                        scene = {expected_scene_name}()
                                        scene.render()
                                    ```
                                10. **Output Format:** Generate ONLY the raw Python code. Do NOT include explanations, comments outside the code, or markdown formatting like ```python ... ```. Start with `from manim import *` and end with the `scene.render()` line within the `if __name__ == "__main__":` block.

                                Generate the complete Manim Python code for `{expected_scene_name}` now.
                                """

                                try:
                                    # Interact with AI Studio to get the Manim code
                                    manim_raw_text = await interact_with_ai_studio(
                                        page, manim_prompt_for_ai_studio, f"Manim Code: {chapter_id_for_files} (A{manim_attempt+1})",
                                        temp_manim, top_p_manim, top_k_manim, max_tokens_manim
                                    )

                                    if manim_raw_text:
                                        extracted_code = None
                                        # Try extracting code block first
                                        match = re.search(r'```python\s*([\s\S]+?)\s*```', manim_raw_text, re.IGNORECASE)
                                        if match:
                                            extracted_code = match.group(1).strip()
                                            print("    Extracted code from ```python block.")
                                        else:
                                            # If no block, assume the whole response might be code (less ideal)
                                            print("    No ```python block found, attempting to use entire response as code.")
                                            # Basic check if it looks like Python
                                            if "from manim import" in manim_raw_text and "class " in manim_raw_text:
                                                extracted_code = manim_raw_text.strip()
                                            else:
                                                print("    [Warning] Response doesn't look like Python code. Saving raw.")
                                                extracted_code = None # Mark as failed

                                        # --- START: MODIFIED - Remove duplicate content marker ---
                                        if extracted_code:
                                            ignore_marker = "IGNORE_WHEN_COPYING_START"
                                            marker_index = extracted_code.find(ignore_marker)
                                            if marker_index != -1:
                                                print(f"    Detected '{ignore_marker}' marker. Truncating code.")
                                                extracted_code = extracted_code[:marker_index].strip()
                                        # --- END: MODIFIED - Remove duplicate content marker ---

                                        if extracted_code:
                                            # <<< MODIFIED VALIDATION >>> Check for VoiceoverScene
                                            class_pattern = rf'class\s+{re.escape(expected_scene_name)}\s*\(\s*VoiceoverScene\s*\)\s*:'
                                            if ("from manim import *" in extracted_code or "import manim" in extracted_code) and \
                                               "from manim_voiceover import VoiceoverScene" in extracted_code and \
                                               "from manim_voiceover.services.gtts import GTTSService" in extracted_code and \
                                               re.search(class_pattern, extracted_code) and \
                                               "construct(self)" in extracted_code and \
                                               "self.set_speech_service(GTTSService" in extracted_code and \
                                               'if __name__ == "__main__":' in extracted_code:

                                                # Save the valid code
                                                manim_filename = f"{chapter_id_for_files}_manim.py" # Save as .py
                                                manim_filepath = os.path.join(OUTPUT_DIR, manim_filename) # Assign filepath here
                                                try:
                                                    with open(manim_filepath, 'w', encoding='utf-8') as f: f.write(extracted_code)
                                                    print(f"    [Success] Manim code saved: {manim_filepath}")
                                                    manim_code_saved = True # Mark as ready for rendering attempt
                                                except Exception as save_err:
                                                     print(f"    [Error] Failed to save Manim code file: {save_err}")
                                                     manim_code_saved = False
                                            else:
                                                print(f"    [Warning] Extracted code failed validation checks (Imports, Class Name '{expected_scene_name}(VoiceoverScene)', construct, set_speech_service, main block). Saving raw python.")
                                                manim_filename_raw = f"{chapter_id_for_files}_manim_RAW_INVALID_A{manim_attempt+1}.py"
                                                raw_path = os.path.join(OUTPUT_DIR, manim_filename_raw)
                                                try:
                                                    with open(raw_path, 'w', encoding='utf-8') as f: f.write(extracted_code)
                                                    print(f"    Raw Python saved: {raw_path}")
                                                except Exception: pass
                                                manim_code_saved = False # Mark as failed for retry
                                        # else: handled above (no code extracted)

                                    else:
                                        # interact_with_ai_studio returned None
                                        print("    [Error] Failed to generate Manim code response from AI (Returned None).")
                                        manim_code_saved = False # Mark as failed for retry
                                        # Assume browser is dead
                                        if browser_context: await browser_context.close(); browser_context, page = None, None
                                        print("    [Critical] Closing browser due to failed interaction. Stopping all tasks.")
                                        chapters = []
                                        break # Exit Manim retry loop

                                except ConnectionError as ce:
                                    print(f"    [Error] Page closed during Manim generation: {ce}")
                                    if browser_context: await browser_context.close(); browser_context, page = None, None
                                    chapters = []; break # Stop all tasks
                                except Exception as manim_ex:
                                     print(f"    [Error] Unexpected error during Manim generation/saving: {manim_ex}")
                                     if page and not page.is_closed():
                                         try: await page.screenshot(path=f"error_screenshot_manim_{chapter_id_for_files}_A{manim_attempt+1}.png")
                                         except Exception: pass
                                     manim_code_saved = False # Mark as failed for retry

                                # --- Task 3b: Render Manim Code (Using VoiceoverScene) ---
                                # Indentation Corrected
                                if manim_code_saved and manim_filepath:
                                    print(f"    [Task 3b] Attempting to render Manim animation with voiceover...")
                                    manim_abs_filepath = os.path.abspath(manim_filepath)
                                    media_dir = os.path.join(OUTPUT_DIR, "media") # Define media output subdir

                                    # <<< MODIFIED RENDER COMMAND >>> Removed --audio flag
                                    manim_command = [
                                        "python", "-m", "manim", # Use python -m manim for consistency
                                        manim_abs_filepath,
                                        expected_scene_name,
                                        "-pql", # Preview quality, low. Use -p for production.
                                        "--media_dir", media_dir, # Explicitly set media output directory
                                        # Optional: Add --verbosity DEBUG for more detailed logs if needed
                                        # "--verbosity", "DEBUG",
                                        # Optional: Force module use if needed, but usually automatic
                                        # "--module", manim_filename,
                                    ]
                                    print(f"      Executing Manim: {' '.join(manim_command)}")
                                    print(f"      (Output video/audio will be in: {media_dir})")

                                    try:
                                        # Ensure media directory exists (Manim usually creates it, but doesn't hurt)
                                        os.makedirs(media_dir, exist_ok=True)

                                        # Run Manim command
                                        # Use check=False initially to capture output even on failure
                                        process = subprocess.run(
                                            manim_command,
                                            capture_output=True,
                                            text=True,
                                            check=False, # Don't raise exception on non-zero exit code yet
                                            encoding='utf-8',
                                            errors='replace' # Handle potential encoding issues in output
                                        )

                                        # Print Manim's output (stdout and stderr)
                                        print("      --- Manim Output ---")
                                        # Limit output length to avoid flooding console
                                        stdout_limit = 2000
                                        stderr_limit = 3000
                                        if process.stdout: print(process.stdout[:stdout_limit] + ("..." if len(process.stdout)>stdout_limit else ""))
                                        else: print("      (No stdout)")
                                        if process.stderr: print("      --- Manim Stderr ---", file=sys.stderr); print(process.stderr[:stderr_limit] + ("..." if len(process.stderr)>stderr_limit else ""), file=sys.stderr); print("      --- End Stderr ---", file=sys.stderr)
                                        else: print("      (No stderr)", file=sys.stderr)
                                        print("      --------------------")

                                        # Check return code AFTER printing output
                                        if process.returncode == 0:
                                            print(f"    [Success] Manim rendering completed successfully for {expected_scene_name}!")
                                            manim_code_generated_and_rendered = True # Set flag for overall success
                                            break # Exit Manim retry loop on success
                                        else:
                                            print(f"    [Error] Manim rendering failed (Return Code: {process.returncode}). See output above.")
                                            # Manim failed, but the code was saved. Now send error to API
                                            print("    [Info] Sending error details to API for analysis...")
                                            try:
                                                # Need the content of the Manim file to send to the API
                                                with open(manim_filepath, 'r', encoding='utf-8') as f:
                                                    manim_code_content = f.read()

                                                api_response = await send_error_to_api(
                                                    manim_code_content,
                                                    process.stdout + "\n" + process.stderr, # Send both stdout and stderr
                                                    OPENROUTER_API_KEY,
                                                    OPENROUTER_API_BASE_URL,
                                                    DEFAULT_MODEL
                                                )
                                                print("    [API Response] Analysis received:")
                                                print(api_response)
                                                # Optionally, could try to parse the API response and apply fixes here (more advanced)
                                            except FileNotFoundError:
                                                print(f"    [Error] Manim file not found for API analysis: {manim_filepath}")
                                            except Exception as api_ex:
                                                print(f"    [Error] Failed to send error to API or process response: {api_ex}")

                                            # Manim failed, but the code was saved. Loop will continue to retry generation.
                                            # Optionally: could try to parse error and feedback to AI in next prompt (advanced)

                                    except FileNotFoundError:
                                        print("    [CRITICAL Error] `python` or `manim` command not found.")
                                        print("    Is Python and Manim installed correctly and in your system's PATH?")
                                        manim_code_saved = False; chapters = []; break # Cannot retry if command not found, stop everything
                                    except Exception as render_ex:
                                        print(f"    [Error] Unexpected Python error during Manim subprocess execution: {render_ex}")
                                        manim_code_saved = False # Treat as failure for retry

                                # --- End of Rendering Attempt Logic ---

                                # Decide whether to retry if this attempt failed (Indentation Corrected)
                                if not manim_code_generated_and_rendered and manim_attempt < MAX_MANIM_RETRIES - 1:
                                     print(f"      Manim attempt {manim_attempt+1} failed (either code generation/validation or rendering). Retrying...")
                                     await asyncio.sleep(random.randint(5, 10)) # Wait before next generation attempt
                                elif not manim_code_generated_and_rendered:
                                     print(f"      Manim failed on final attempt ({manim_attempt+1}).")

                            # --- End of Manim Retry Loop ---
                            if not chapters: break # Exit chapter loop if browser died during Manim attempts

                            # Report Manim success/failure for the chapter (Indentation Corrected)
                            if not manim_code_generated_and_rendered:
                                print(f"  [Error] Failed to generate and render Manim code for chapter {chapter_title} (ID: {chapter_id_for_files}) after {MAX_MANIM_RETRIES} attempts.")
                            else:
                                print(f"  [Success] Successfully generated and rendered Manim video for chapter {chapter_title}.")

                        # --- Script Generation Failed Case (Indentation Corrected) ---
                        elif not script_gen_success:
                            print(f"  [Task 3] Skipping Manim for chapter {i+1}: Script generation failed.")
                        else: # Should not happen if script_gen_success is True, but as a fallback
                            print(f"  [Task 3] Skipping Manim for chapter {i+1}: Script text is missing.")

                        # --- Chapter End & Delay Logic (Indentation Corrected) ---
                        if not chapters: # Check if stop signal was received
                            print("    [Info] Stop signal received (chapters list cleared). Stopping chapter processing.")
                            break # Exit the main chapter loop

                        # Only delay if there are more chapters AND browser is alive
                        if browser_context and page and not page.is_closed() and (i < num_chapters - 1):
                            delay = random.randint(10, 25) # Slightly longer delay between chapters
                            print(f"\n    --- Waiting {delay}s before starting Chapter {i+2} ---")
                            await asyncio.sleep(delay)
                        elif i == num_chapters - 1:
                            print(f"\n    --- Finished processing the last chapter ({chapter_title}) ---")
                        else:
                            # If browser died or it's the last chapter, don't delay
                            print("[Info] Browser closed or last chapter reached. Not delaying.")

                # --- No Chapters Case (Indentation Corrected) ---
                else: # overview_data.get("chapters", []) was empty
                    print("[Info] No chapters found in the overview data to process.")
            # --- Overview Failed Case (Indentation Corrected) ---
            elif not overview_data:
                print("[Info] Course overview generation failed earlier. Skipping chapter processing.") # Should have been caught by RuntimeError
            # --- Browser Invalid Case (Indentation Corrected) ---
            else: # Browser context was invalid at the start of chapter loop
                print("[Info] Browser context was invalid. Skipping chapter processing.")

    # --- Outer Exception Handling ---
    except RuntimeError as rt_err:
        # Catch specific errors raised internally (like overview failure)
        print(f"\n[Script Stopped] Runtime Error: {rt_err}")
    except PlaywrightError as e:
         err_str = str(e).lower();
         # Handle profile lock error gracefully
         if "user data directory is already in use" in err_str or "lock" in err_str:
             print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
             print("[CRITICAL ERROR] Chrome User Data Directory is LOCKED!")
             print(f"Profile path: {USER_DATA_DIR}")
             print("CLOSE ALL Chrome windows using this profile and run again.")
             print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
         else: # Log other Playwright errors
             print(f"[CRITICAL Playwright Error] {e}");
             import traceback; traceback.print_exc()
             # Try screenshot if page object exists and might be valid
             if 'page' in locals() and page is not None and not page.is_closed():
                 try: await page.screenshot(path="error_screenshot_playwright_unexpected.png")
                 except Exception: pass
    except Exception as e:
         # Catch any other unexpected errors in the main flow
         print(f"[CRITICAL Error] An unexpected error occurred in main: {e}");
         import traceback; traceback.print_exc()
         if 'page' in locals() and page is not None and not page.is_closed():
             try: await page.screenshot(path="error_screenshot_main_unexpected.png")
             except Exception: pass

    finally:
        # --- Cleanup ---
        print("\n[Cleanup] Script finished or encountered critical error.")
        if 'browser_context' in locals() and browser_context is not None:
             connection_active = False
             try:
                 # Ping the browser connection briefly to see if it's still responsive
                 await asyncio.wait_for(browser_context.pages(), timeout=1.5)
                 connection_active = True
                 print("[Cleanup] Browser connection seems active.")
             except Exception:
                 connection_active = False
                 print("[Cleanup Info] Browser connection seems closed or unresponsive.")

             if connection_active:
                 print("Attempting to close browser context gracefully...")
                 user_input = input("Press Enter to close the browser window, or type 'keep' to leave it open: ")
                 if user_input.lower().strip() != 'keep':
                     try:
                         await browser_context.close()
                         print("[Cleanup] Browser context closed by script.")
                     except Exception as close_e:
                         print(f"[Cleanup Info] Error closing browser context: {close_e}")
                 else:
                     print("[Cleanup] Browser window left open as requested.")
             else: # Connection wasn't active
                  print("[Cleanup] Attempting final cleanup of potentially defunct browser context...")
                  try: await browser_context.close() # Try closing anyway
                  except Exception: pass # Ignore errors here
                  print("[Cleanup] Final context close attempted.")
        else:
             print("[Cleanup] Browser context was not established or already cleaned up.")
        print("[Cleanup] End of script.")

if __name__ == '__main__':
     try:
         # Ensure numpy is available if Manim code might use it
         try: import numpy; print(f"[Info] Numpy version {numpy.__version__} found.")
         except ImportError: print("[Warning] Numpy not found. Manim code requiring numpy might fail.")

         asyncio.run(main())

     except KeyboardInterrupt:
         print("\n[Execution Interrupted] Script stopped by user (Ctrl+C).")
     except Exception as outer_err:
         # Catch errors that might occur outside the main async loop
         print(f"\n[CRITICAL] An unhandled error occurred at the top level: {outer_err}")
         import traceback; traceback.print_exc()
         input("Press Enter to exit after error...") # Keep window open