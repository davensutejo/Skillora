#!/usr/bin/env python3
"""
Course Generator - Main Script using Browser Automation


This script uses AI agents controlling a web browser to find relevant YouTube videos
for different chapters of a specified course topic. It also generates transcripts
and analyzes relevance.
"""


import asyncio
import os
import re
import json
import sys # Import sys for platform check
import traceback # For printing detailed tracebacks


# --- Fix for Playwright/Asyncio/Subprocess issue on Windows ---
# The explicit event loop policy setting is removed as it may cause issues on some systems.
# The default policy should be sufficient for most modern Windows environments.
# --- End Fix ---


from dotenv import load_dotenv
# Ensure browser_use.py exists and defines these classes
try:
    from browser_use import Agent, Browser, BrowserConfig
except ImportError:
    print("Error: Could not import from 'browser_use'. Make sure browser_use.py exists and defines Agent, Browser, BrowserConfig.")
    sys.exit(1)


from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai # For overview and transcript generation


# --- Configuration ---
load_dotenv()


# Get API Keys from .env or provide directly
api_keys = [os.getenv(f"GOOGLE_API_KEY_{i+1}") for i in range(10)] # Try to load up to 10 keys
api_keys = [key for key in api_keys if key] # Filter out None values


if not api_keys:
    raise ValueError("No Google API Keys found. Set GOOGLE_API_KEY_1, etc. in your .env file or provide them directly.")


# Limit concurrency based on available keys or a desired max
MAX_CONCURRENT_AGENTS = 10
NUM_CONCURRENT_AGENTS = min(len(api_keys), MAX_CONCURRENT_AGENTS)
print(f"[Config] Using {NUM_CONCURRENT_AGENTS} API keys for concurrent agents (Max requested: {MAX_CONCURRENT_AGENTS}).")


# Model names (Adjust if needed)
AGENT_MODEL_NAME = "gemini-1.5-flash-latest" # Ensure this model supports tool use / function calling if browser_use relies on it heavily
OVERVIEW_MODEL_NAME = "gemini-1.5-flash-latest" # Or "gemini-pro"
TRANSCRIPT_MODEL_NAME = "gemini-1.5-flash-latest" # Model for generating transcripts
RELEVANCE_MODEL_NAME = "gemini-1.5-flash-latest" # Model for analyzing relevance


# --- End Configuration ---


PREFERRED_CHANNELS_BY_TOPIC = {
    # Channels generally good for many CS/Tech topics
    "default": [
        "freeCodeCamp.org", "CrashCourse", "Khan Academy", "MIT OpenCourseWare",
        "CS50", "Google Developers", "Microsoft Developer", "Fireship", "3Blue1Brown",
        "Codecademy", "Udacity","The Organic Chemistry Tutor",
    ],
    # Topic-specific additions (examples)
    "Data Science": ["StatQuest with Josh Starmer", "Ken Jee", "Data School"],
    "Python": ["Corey Schafer", "Sentdex", "Real Python"],
    "Web Development": ["Traversy Media", "The Net Ninja", "Academind", "Web Dev Simplified", "Kevin Powell"],
    "Machine Learning": ["Andrew Ng", "Two Minute Papers"],
    "Cybersecurity": ["Professor Messer", "NetworkChuck", "John Hammond"],
    "Game Development": ["Brackeys", "Sebastian Lague", "Unity", "Game Maker's Toolkit"],
    "Calculus": ["3blue1brown"],
    # Add more mappings as needed
}


def get_preferred_channels(topic: str) -> list[str]:
    """Gets a combined list of default and topic-specific preferred channels."""
    topic_lower = topic.lower()
    # Start with a copy of the default list
    preferred = PREFERRED_CHANNELS_BY_TOPIC.get("default", []).copy()
    # Add topic-specific channels
    for key, channels in PREFERRED_CHANNELS_BY_TOPIC.items():
        if key != "default" and key.lower() in topic_lower:
            preferred.extend(channels)
    # Return a unique list
    return list(set(preferred))


def parse_chapters_simple(overview_text: str) -> list[str]:
    """
    Simpler parser for chapter titles from the overview.
    Looks for lines starting with common patterns like 'Chapter X:', 'Module Y:', '- ', '* ', '1. '.
    """
    chapters = []
    # Regex to find lines likely indicating a chapter/module/section title
    pattern = re.compile(r"^\s*(?:(?:chapter|module|unit|section|part)\s+\w*[:.\-–]?|\d+\.?|\*|\-)\s+(.*)", re.IGNORECASE | re.MULTILINE)


    matches = pattern.findall(overview_text)
    print(f"  [Parser] Found {len(matches)} potential chapters via regex.")


    for title in matches:
        title = title.strip()
        # Basic filter
        if len(title) > 5 and not title.lower().startswith(("e.g.", "i.e.", "includes:", "such as")):
            # Further clean common prefixes the regex might miss if they have no punctuation
            title = re.sub(r"^(Chapter|Module|Unit|Section|Part)\s*\d*\s*", "", title, flags=re.IGNORECASE).strip()
            chapters.append(title)


    # Fallback: If regex finds nothing, split by newline and take non-empty lines
    if not chapters and overview_text:
         print("  [Parser] Regex found no chapters, falling back to splitting lines.")
         lines = overview_text.strip().split('\n')
         for line in lines:
             line = line.strip()
             # Basic heuristics for a fallback
             if len(line) > 10 and (':' in line or (line and line[0].isupper()) or re.match(r"^\d+\.", line)):
                 # Try to remove potential prefixes like "Chapter 1: " if they exist
                 line = re.sub(r"^\s*(?:(?:chapter|module|unit|section|part)\s+\w*[:.\-–]?|\d+\.?|\*|\-)\s*", "", line, flags=re.IGNORECASE).strip()
                 if len(line) > 5: # Check length again after stripping prefix
                    chapters.append(line)


    # Deduplicate while preserving order
    seen = set()
    unique_chapters = []
    for chapter in chapters:
        if chapter not in seen:
            unique_chapters.append(chapter)
            seen.add(chapter)


    print(f"  [Parser] Identified {len(unique_chapters)} unique chapters.")
    return unique_chapters


async def analyze_transcript_relevance(
    model: genai.GenerativeModel,
    transcript: str,
    chapter_title: str,
    course_topic: str,
    semaphore: asyncio.Semaphore
) -> str:
    """
    Analyzes if the transcript content is relevant to the chapter title and course topic.
    Returns "Highly Relevant", "Moderately Relevant", "Not Relevant", or an error message.
    """
    async with semaphore:
        print(f"    [Relevance] Analyzing transcript for chapter: '{chapter_title}'")
        max_transcript_len = 8000 # Limit transcript length for analysis prompt
        if len(transcript) > max_transcript_len:
            transcript_snippet = transcript[:max_transcript_len] + "... (truncated)"
        else:
            transcript_snippet = transcript


        prompt = f"""
Analyze the following YouTube video transcript snippet to determine its relevance to the course chapter "{chapter_title}" within the broader topic of "{course_topic}".


Chapter Title: {chapter_title}
Course Topic: {course_topic}


Transcript Snippet:
---
{transcript_snippet}
---


Based ONLY on the transcript snippet provided, assess the relevance. Consider if the core concepts of the chapter title are discussed explicitly or implicitly.


Output ONLY one of the following classifications:
- Highly Relevant
- Moderately Relevant
- Not Relevant
"""
        try:
            # Use less restrictive safety settings for analysis as well
            safety_settings = [ {"category": c, "threshold": "BLOCK_NONE"} for c in [
                    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]]
            response = await model.generate_content_async(prompt, safety_settings=safety_settings)


            if response.parts:
                analysis = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
                # Validate response format
                valid_responses = ["Highly Relevant", "Moderately Relevant", "Not Relevant"]
                if analysis in valid_responses:
                    print(f"    [Relevance] Analysis complete for '{chapter_title}': {analysis}")
                    return analysis
                else:
                    print(f"    [Relevance] Analysis for '{chapter_title}' returned unexpected format: {analysis}")
                    return "[Analysis Failed: Invalid Format]"
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                 reason = response.prompt_feedback.block_reason.name
                 print(f"    [Relevance] Analysis failed for '{chapter_title}': Blocked by model ({reason})")
                 return f"[Analysis Failed: Blocked ({reason})]"
            else:
                 print(f"    [Relevance] Analysis failed for '{chapter_title}': Unknown reason")
                 return "[Analysis Failed: Unknown]"
        except Exception as e:
            print(f"    [Relevance] Analysis failed for '{chapter_title}': {e}")
            return f"[Analysis Failed: Error ({e})]"




async def get_transcript(model: genai.GenerativeModel, video_url: str, semaphore: asyncio.Semaphore) -> str:
    """
    Requests a transcript for a given YouTube video URL using the provided Gemini model.
    Returns the transcript text or an error message string.
    """
    async with semaphore:
        print(f"    [Transcript] Requesting transcript for: {video_url}")
        # Use the Tool directly if available and preferred
        video_file = genai.upload_file(path=video_url) # This likely won't work directly with URLs, intended for local files
        # The prompt method is generally more reliable for URLs with standard models
        prompt = f"Please provide a detailed text transcript of the video content at this URL: {video_url}. Focus only on the spoken words."


        try:
            # Configure safety settings to be less restrictive for transcription
            safety_settings = [ {"category": c, "threshold": "BLOCK_NONE"} for c in [
                    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]]
            response = await model.generate_content_async(prompt, safety_settings=safety_settings)


            if response.parts:
                transcript = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                print(f"    [Transcript] Received transcript for: {video_url} (Length: {len(transcript)})")
                return transcript.strip() if transcript else "[Transcript empty or model refused]"
            elif response.prompt_feedback and response.prompt_feedback.block_reason:
                 reason = response.prompt_feedback.block_reason.name
                 print(f"    [Transcript] Failed for {video_url}: Blocked by model ({reason})")
                 return f"[Transcript failed: Blocked by model ({reason})]"
            else:
                 # Check candidate for finish reason if no parts/feedback
                 finish_reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                 print(f"    [Transcript] Failed for {video_url}: Reason: {finish_reason} (No parts/block feedback)")
                 return f"[Transcript failed: {finish_reason}]"


        except Exception as e:
            error_str = str(e)
            # Handle specific errors more gracefully
            if "API key not valid" in error_str:
                print(f"    [Transcript] Failed for {video_url}: Invalid API Key")
                return "[Transcript failed: Invalid API Key]"
            elif "429" in error_str or "ResourceExhausted" in error_str:
                print(f"    [Transcript] Failed for {video_url}: Rate Limit/Quota Exceeded")
                return "[Transcript failed: Rate Limit/Quota Exceeded]"
            elif "Vertex AI API has not been used" in error_str:
                 print(f"    [Transcript] Failed for {video_url}: Vertex AI API not enabled or initialized")
                 return "[Transcript failed: Vertex AI API not enabled]"
            elif "permission" in error_str.lower() or "access denied" in error_str.lower():
                 print(f"    [Transcript] Failed for {video_url}: Permission Denied (Check API key permissions/billing)")
                 return "[Transcript failed: Permission Denied]"
            elif "File format is not supported" in error_str or "does not contain media" in error_str:
                print(f"    [Transcript] Failed for {video_url}: Model cannot process this URL/format directly.")
                return "[Transcript failed: Cannot process URL]"
            else:
                print(f"    [Transcript] Failed for {video_url}: {e}")
                # Optionally log the full traceback for unexpected errors
                # logger.error(f"Unexpected transcript error for {video_url}", exc_info=True)
                return f"[Transcript failed: Unexpected Error ({type(e).__name__})]"




async def run_single_agent(browser: Browser, llm_instance: ChatGoogleGenerativeAI, task_prompt: str, semaphore: asyncio.Semaphore, chapter_title: str):
    """Acquires semaphore, creates and runs a single agent task using the shared browser, returns result or exception."""
    async with semaphore:
        print(f"  [Agent Runner] Starting task for chapter: '{chapter_title}'...")
        agent = None # Initialize agent to None
        try:
            # Create the agent instance INSIDE the task context, passing the shared browser
            print(f"    [Agent Runner] Instantiating Agent for '{chapter_title}'...")
            agent = Agent(
                browser=browser, # Pass the shared browser instance
                llm=llm_instance,
                task=task_prompt,
            )
            print(f"    [Agent Runner] Agent instantiated. Running task...")
            # The core agent execution
            # The result is typically a history object or similar structure from the agent library
            result = await agent.run()
            print(f"  [Agent Runner] Finished task for chapter: '{chapter_title}'")
            return result
        except Exception as e:
             print(f"  [Agent Runner] !!! Exception during agent run for chapter '{chapter_title}': {type(e).__name__} - {e}")
             # Log the traceback for agent execution errors
             # logger.error(f"Exception in agent run for '{chapter_title}'", exc_info=True)
             # Return the exception itself to be handled later
             return e
        finally:
            # Optional: Clean up agent-specific resources if needed, though browser is shared
            if agent:
                # Add any specific cleanup if the Agent class requires it
                pass
            print(f"  [Agent Runner] Semaphore released for chapter: '{chapter_title}'")




async def main():
    topic = input("Enter course topic: ")


    # --- Step 1: Initialize Shared Browser ---
    print("\n[Setup] Initializing Shared Browser (Headless)...")
    browser = None # Initialize to None
    try:
        browser_config = BrowserConfig(
            headless=False, # Changed to True for typical server/script use
            disable_security=False # Keep security enabled unless specifically needed
        )
        browser = Browser(config=browser_config)
        print("[Setup] Shared Browser initialized successfully.")
    except Exception as e:
        print(f"\n[Setup] Error initializing Shared Browser: {e}")
        print("Ensure Chrome or Chromium is installed and accessible in PATH, or configure executable path.")
        print("Try running with headless=False initially for debugging.")
        return # Exit if browser fails


    # --- Step 2: Initialize LLMs ---
    print(f"[Setup] Initializing LLM for overview ({OVERVIEW_MODEL_NAME})...")
    model_gen = None
    model_transcript = None
    model_relevance = None
    agent_llms = []
    try:
        # LLM for generating the overview (using the first API key)
        genai.configure(api_key=api_keys[0])
        model_gen = genai.GenerativeModel(OVERVIEW_MODEL_NAME)
        print(f"[Setup] Initializing LLM for transcripts ({TRANSCRIPT_MODEL_NAME})...")
        # Reconfigure if needed, or use the same config if key/model match
        # genai.configure(api_key=api_keys[0]) # Assuming same key is okay
        model_transcript = genai.GenerativeModel(TRANSCRIPT_MODEL_NAME)
        print(f"[Setup] Initializing LLM for relevance analysis ({RELEVANCE_MODEL_NAME})...")
        model_relevance = genai.GenerativeModel(RELEVANCE_MODEL_NAME)


        print(f"[Setup] Initializing {NUM_CONCURRENT_AGENTS} LLM instances for agents ({AGENT_MODEL_NAME})...")
        for i in range(NUM_CONCURRENT_AGENTS):
            key_index = i % len(api_keys) # Cycle through available keys safely
            llm = ChatGoogleGenerativeAI(
                model=AGENT_MODEL_NAME,
                google_api_key=api_keys[key_index],
                temperature=0.4, # Slightly lower temp might help focus the agent
                convert_system_message_to_human=True,
                # Add request options if needed, e.g., timeout
                # request_options={"timeout": 300}
            )
            agent_llms.append(llm)
        print(f"[Setup] LLMs initialized.")
    except Exception as e:
        print(f"\n[Setup] Error initializing Google Generative AI models: {e}")
        print(f"Check API keys, model names ('{OVERVIEW_MODEL_NAME}', '{AGENT_MODEL_NAME}', '{TRANSCRIPT_MODEL_NAME}', '{RELEVANCE_MODEL_NAME}'), network access, and quotas.")
        if browser: await browser.close() # Clean up browser if LLM init fails
        return


    # --- Step 3: Generate Course Overview ---
    print(f"\n[Generator] Generating course overview for '{topic}'...")
    course_overview = ""
    try:
        prompt = (
            f"Create a concise course overview about '{topic}'. "
            "List the main chapters or modules (around 5-10). "
            "Use a clear list format, like 'Chapter 1: Title', 'Module A: Title', '- Topic Name', or '1. Introduction'. "
            "Put each chapter/module title on its own new line."
            "Focus on distinct learning units suitable for video lessons."
            "Do not add introductory or concluding sentences, just the list."
        )
        response = await model_gen.generate_content_async(prompt) # Use async version
        if response.parts:
             course_overview = "".join(part.text for part in response.parts if hasattr(part, 'text')).strip()
        else:
            raise Exception("Overview generation returned no content.")
        print("\n--- Generated Course Overview ---")
        print(course_overview)
        print("---------------------------------\n")
    except Exception as e:
        print(f"\n[Generator] Error generating course overview: {e}")
        if browser: await browser.close()
        return


    # --- Step 4: Parse Chapters ---
    print("[Parser] Parsing chapters from the overview...")
    chapters = parse_chapters_simple(course_overview)
    if not chapters:
        print("\n[Parser] Could not identify chapters from the overview. Exiting.")
        if browser: await browser.close()
        return
    print(f"\n[Agent Setup] Found {len(chapters)} chapters. Preparing agents...")


    # --- Step 5: Prepare and Run Agent Tasks Concurrently ---
    semaphore = asyncio.Semaphore(NUM_CONCURRENT_AGENTS)
    tasks = []


    preferred_channels_list = get_preferred_channels(topic)
    preferred_channels_str = ", ".join(f"'{name}'" for name in preferred_channels_list)
    print(f"  [Agent Setup] Prioritizing channels (if relevant): {preferred_channels_str}")


    for i, chapter_title in enumerate(chapters):
        llm_instance = agent_llms[i % NUM_CONCURRENT_AGENTS] # Cycle through LLMs/API keys


        # Define the specific task for the agent - MODIFIED FOR VERIFIED PREFERENCE
        task_prompt = (
            "INSTRUCTIONS:\n"
            f"You are an expert researcher tasked with finding educational video content about '{topic}'.\n"
            f"Your specific goal for this task is to find the SINGLE BEST, most relevant, high-quality YouTube video for the course chapter titled: '{chapter_title}'.\n\n"


            "CRITICAL OUTPUT REQUIREMENT:\n"
            "Your final response MUST be ONLY the single, direct YouTube video URL (e.g., 'https://www.youtube.com/watch?v=videoID' or 'https://youtu.be/videoID').\n"
            "ABSOLUTELY DO NOT RETURN: Channel links (/c/, /@, /user/), playlist links, search result links, YouTube Shorts (/shorts/), or any other text, explanation, commentary, greetings, or formatting. JUST the URL.\n\n"


            "SEARCH STRATEGY:\n"
            f"1. Navigate to YouTube.com.\n"
            f"2. Search using precise terms. Start with: `\"{chapter_title}\" {topic} course tutorial`\n"
            f"3. **Scroll down the search results page ONCE or TWICE** to load more videos beyond the initial view. Use the scroll_down action.\n"
            f"4. If the initial search yields poor results, try variations like: `{chapter_title} explained` or keywords extracted from the chapter title combined with `{topic}`.\n\n"
            "\nEVALUATION CRITERIA (Strictly evaluate search results and video pages based on these):\n"
            f"*   **Relevance (Highest Priority):** Does the video title *directly* address the chapter '{chapter_title}'? Are the main keywords present early in the title? Does the description (check the video page) confirm it covers the specific chapter content within the context of '{topic}'?\n"
            f"*   **Channel Trust/Verification (High Priority):**\n"
            f"    *   **Preferred Channels:** Is the video from one of these highly regarded channels: {preferred_channels_str}? Check the channel name on the search results or video page.\n"
            f"    *   **YouTube Verification:** Does the channel name have the official verification checkmark symbol (`✓`) next to it on the search results or video page? \n"
            f"    *   **Give Strong Preference:** Strongly prefer relevant videos from Preferred or Verified channels over others, even if the others have slightly higher view counts.\n"


            "EVALUATION CRITERIA (Strictly evaluate search results and video pages based on these):\n"
            f"*   **Relevance (Highest Priority):** Does the video title AND description (check video page) *directly* address the specific chapter '{chapter_title}'? Is it clearly within the context of the broader topic '{topic}'?\n"
            "*   **Quality Indicators:** Look for signs of a well-produced, informative video (clear audio/visuals if possible, professional presentation). Avoid low-effort content, pure marketing, or overly long intros.\n"
            "***   **Channel Reputation (Preference):** Prefer videos from channels that appear official, established, or reputable in the '{topic}' domain. Look for indicators like a verification checkmark (✔️) if visible, high subscriber counts, or clear affiliation with known organizations. However, a highly relevant video from a smaller, focused channel can still be chosen if it's the best content match.\n" # <-- MODIFIED
            "*   **Engagement Signals (Tie-breaker):** Consider view count and like ratio (if visible) primarily to differentiate between multiple, *equally relevant* videos. Relevance is more important than raw popularity.\n"
            "*   **Recency (Consideration):** For rapidly evolving topics, prefer newer videos if relevance and quality are comparable.\n"
            "*   **Avoid Duplicates:** Do not select a video extremely similar to one likely found for other chapters in this course.\n\n"


            "ACTION SEQUENCE:\n"
            "1. Perform the YouTube search.\n"
            "2. **Scroll down** the search results page once or twice.\n"
            "3. Analyze the **visible** top ~15-20 search results based on the criteria above (paying close attention to titles and channel names).\n"
            "4. Click into the MOST promising video result.\n"
            "5. On the video page, CAREFULLY verify its title, description, and (if possible) the start of the content match the chapter '{chapter_title}'. Check the channel appearance for reputability.\n"
            "6. If it's the best match according to ALL criteria (especially relevance), extract its direct video URL (e.g., from the browser address bar or 'Share' button).\n"
            "7. If the first video isn't suitable, GO BACK to search results and evaluate the next best candidate rigorously.\n"
            "8. Pick the one from a verified channel"
            "9. Repeat step 4-6 until the single best video is found.\n"
            "10. Output ONLY the final selected video URL."


        )
        print(f"  [Agent Setup] Creating agent for chapter {i+1}/{len(chapters)}: '{chapter_title}'")


        try:
            # Create an asyncio task, passing the shared browser and other parameters
            tasks.append(asyncio.create_task(run_single_agent(browser, llm_instance, task_prompt, semaphore, chapter_title)))
        except Exception as e:
             print(f"  [Agent Setup] Error creating agent task for chapter '{chapter_title}': {e}")
             # Add a placeholder for failed task creation
             async def failed_task_placeholder(error): return error
             tasks.append(asyncio.create_task(failed_task_placeholder(RuntimeError(f"Agent task creation failed: {e}"))))




    print(f"\n[Agent Runner] Starting {len(tasks)} agent tasks with concurrency limit {NUM_CONCURRENT_AGENTS}...")
    # Run all tasks concurrently and wait for them to complete
    results = await asyncio.gather(*tasks) # Exceptions within tasks are returned in the results list
    print(f"\n[Agent Runner] All agent tasks finished.")


    # --- Step 6: Process Results, Get Transcripts, Analyze Relevance ---
    successful_tasks = 0
    failed_tasks = 0
    all_agent_results_status = {}
    parsed_links_by_chapter = {}


    # --- Step 6a: Collect Agent Results & Parse/Validate Links ---
    print("\n[Processor] Collecting and processing agent results...")
    for i, result_or_exc in enumerate(results):
        chapter_title = chapters[i]
        extracted_link = None
        status_message = "[Processing Error]" # Default status


        if isinstance(result_or_exc, Exception):
            failed_tasks += 1
            status_message = result_or_exc # Store the exception object
            print(f"  - Chapter '{chapter_title}': Failed (Agent Execution Error: {result_or_exc})")
        elif hasattr(result_or_exc, 'final_result'): # Check if it looks like the expected history object
            successful_tasks += 1
            try:
                final_output_text = result_or_exc.final_result() # Expecting the URL string
                if final_output_text and isinstance(final_output_text, str):
                    potential_link = final_output_text.strip()
                    status_message = potential_link # Store raw output


                    # Validate the link format
                    if (potential_link.startswith("https://www.youtube.com/watch?v=") or \
                        potential_link.startswith("https://youtu.be/")) and \
                       "/shorts/" not in potential_link and \
                       len(potential_link) > 20: # Basic sanity check length
                        extracted_link = potential_link
                        print(f"  - Chapter '{chapter_title}': Success (Link Found: {extracted_link})")
                    else:
                        print(f"  - Chapter '{chapter_title}': Completed (Output not a valid YouTube link: '{potential_link}')")
                        status_message = f"[Invalid Output: {potential_link}]" # Update status
                else:
                     print(f"  - Chapter '{chapter_title}': Completed (Agent returned empty or non-string result)")
                     status_message = "[Agent Result Empty/Invalid]"
            except Exception as e:
                 print(f"  - Chapter '{chapter_title}': Completed (Error processing agent result: {e})")
                 status_message = f"[Error processing result: {e}]"
        else:
            # Unexpected result type from gather
            failed_tasks += 1
            status_message = f"[Unexpected Result Type: {type(result_or_exc).__name__}]"
            print(f"  - Chapter '{chapter_title}': Failed ({status_message})")


        all_agent_results_status[chapter_title] = status_message
        parsed_links_by_chapter[chapter_title] = [extracted_link] if extracted_link else []




    # --- Step 6b: Generate Transcripts Concurrently ---
    print("\n[Transcript] Preparing transcript generation...")
    all_links_to_transcript = list(set(link for links in parsed_links_by_chapter.values() for link in links if link))
    transcripts_by_link = {}
    transcript_tasks = []
    # Limit concurrency for transcript generation as well
    transcript_semaphore = asyncio.Semaphore(NUM_CONCURRENT_AGENTS)


    if all_links_to_transcript:
        print(f"[Transcript] Found {len(all_links_to_transcript)} unique valid links to transcribe.")
        for link in all_links_to_transcript:
            transcript_tasks.append(
                asyncio.create_task(get_transcript(model_transcript, link, transcript_semaphore))
            )


        print(f"[Transcript] Starting {len(transcript_tasks)} transcript tasks...")
        transcript_results = await asyncio.gather(*transcript_tasks)
        print("[Transcript] All transcript tasks finished.")
        transcripts_by_link = dict(zip(all_links_to_transcript, transcript_results))
    else:
        print("[Transcript] No valid links found by agents to transcribe.")




    # --- Step 6c: Analyze Transcript Relevance Concurrently ---
    print("\n[Relevance] Preparing transcript relevance analysis...")
    relevance_tasks = []
    relevance_results_by_link = {}
    # Reuse semaphore or create a new one if needed
    relevance_semaphore = asyncio.Semaphore(NUM_CONCURRENT_AGENTS)
    link_to_chapter_map = {link: ch for ch, links in parsed_links_by_chapter.items() for link in links if link}


    if transcripts_by_link:
        print(f"[Relevance] Creating analysis tasks for available transcripts...")
        tasks_created = 0
        for link, transcript_text in transcripts_by_link.items():
            chapter_for_link = link_to_chapter_map.get(link)
            # Check if transcript is valid and chapter mapping exists
            if chapter_for_link and transcript_text and not transcript_text.startswith("[Transcript failed") and not transcript_text.startswith("[Transcript empty"):
                 relevance_tasks.append(
                     asyncio.create_task(analyze_transcript_relevance(
                         model_relevance, # Use the dedicated relevance model
                         transcript_text,
                         chapter_for_link,
                         topic,
                         relevance_semaphore
                     ))
                 )
                 tasks_created += 1
            else:
                 # Store placeholder for links with failed transcripts or mapping issues
                 relevance_results_by_link[link] = "[Analysis Skipped: Invalid Transcript]"


        if relevance_tasks:
            print(f"[Relevance] Starting {len(relevance_tasks)} analysis tasks...")
            analysis_results_list = await asyncio.gather(*relevance_tasks)
            print("[Relevance] All analysis tasks finished.")


            # Map results back to the links that were actually analyzed
            analyzed_links = [link for link, transcript in transcripts_by_link.items() if link_to_chapter_map.get(link) and transcript and not transcript.startswith("[Transcript failed") and not transcript.startswith("[Transcript empty")]
            relevance_results_by_link.update(dict(zip(analyzed_links, analysis_results_list)))
        else:
            print("[Relevance] No valid transcripts were available to analyze.")
    else:
        print("[Relevance] No transcripts were generated, skipping analysis.")




    # --- Step 6d: Integrated Results Reporting ---
    print("\n" + "=" * 40)
    print("--- Final Course Content Report ---")
    print("=" * 40)
    total_links_found = 0
    successful_transcripts = 0
    failed_transcripts = 0
    highly_relevant_count = 0
    moderately_relevant_count = 0


    for i, chapter_title in enumerate(chapters): # Iterate through original chapters list
        print(f"\n[{i+1}/{len(chapters)}] Chapter: {chapter_title}")
        agent_status = all_agent_results_status.get(chapter_title)
        found_links = parsed_links_by_chapter.get(chapter_title, [])
        link = found_links[0] if found_links else None


        if isinstance(agent_status, Exception):
            print(f"  Status: Agent Failed")
            error_str = str(agent_status)
            if "429" in error_str or "ResourceExhausted" in error_str: print(f"  Error: Rate Limit / Quota Exceeded")
            elif "API key not valid" in error_str: print(f"  Error: Invalid API Key")
            else: print(f"  Error: Agent Execution Failed ({type(agent_status).__name__})")
            print(f"  Link Found: ---")
        elif link:
            print(f"  Status: Agent Completed")
            print(f"  Link Found: {link}")
            total_links_found += 1
            # Transcript Info
            transcript_result = transcripts_by_link.get(link, "[Transcript Not Generated]")
            if transcript_result and not transcript_result.startswith("[Transcript failed") and not transcript_result.startswith("[Transcript empty"):
                print(f"  Transcript: Generated (Length: {len(transcript_result)})")
                successful_transcripts += 1
            else:
                print(f"  Transcript: {transcript_result}") # Show error or empty message
                failed_transcripts += 1
            # Relevance Info
            relevance_result = relevance_results_by_link.get(link, "[Analysis Not Run]")
            print(f"  Relevance: {relevance_result}")
            if relevance_result == "Highly Relevant": highly_relevant_count += 1
            elif relevance_result == "Moderately Relevant": moderately_relevant_count += 1
        else:
            # Agent completed but didn't find/return a valid link
            print(f"  Status: Agent Completed")
            print(f"  Link Found: --- (Agent output: {str(agent_status)[:100]}...)") # Show snippet of invalid output
            print(f"  Transcript: [Not Applicable]")
            print(f"  Relevance: [Not Applicable]")


    print("\n" + "=" * 40)
    print("--- Overall Summary ---")
    print(f"Chapters Processed: {len(chapters)}")
    print(f"Agents Completed Successfully (may not have found link): {successful_tasks}")
    print(f"Agents Failed Execution: {failed_tasks}")
    print("-" * 20)
    print(f"Total Valid YouTube Links Found: {total_links_found}")
    print(f"Transcripts Generated Successfully: {successful_transcripts}")
    print(f"Transcripts Failed or Empty: {failed_transcripts}")
    print("-" * 20)
    print(f"Videos Assessed as 'Highly Relevant': {highly_relevant_count}")
    print(f"Videos Assessed as 'Moderately Relevant': {moderately_relevant_count}")
    print("=" * 40 + "\n")


    # --- Step 7: Clean up Shared Browser ---
    if browser:
        print("\n[Cleanup] Closing shared browser...")
        await asyncio.sleep(0.5) # Increased sleep slightly
        try:
            await browser.close()
            print("[Cleanup] Shared Browser closed.")
        except Exception as e:
            print(f"[Cleanup] Error closing browser: {e}")
            # Log traceback for browser closing errors if needed
            # logger.error("Error closing browser", exc_info=True)




if __name__ == "__main__":
    try:
        # Setup basic logging if needed (optional)
        # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    except Exception as e:
         print(f"\nFATAL ERROR in main execution loop: {e}")
         traceback.print_exc()
    finally:
        # Attempt to clean up any lingering asyncio tasks/resources if possible
        # This is complex and might not catch everything, especially related to subprocesses
        # from asyncio.all_tasks might be useful here in a more complex scenario
        print("[Main] Script finished.")

