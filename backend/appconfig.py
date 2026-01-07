"""
Application configuration for MedScan
Central place for paths, flags, and safety settings
"""

from pathlib import Path

APP_NAME = "MedScan"
APP_VERSION = "0.1.0"

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Prompt file location
PROMPT_PATH = BASE_DIR / ".github" / "prompts" / "ai_prompt.md"

# Safety settings
ALLOW_DIAGNOSIS = False
ALLOW_TREATMENT_ADVICE = False
SUMMARY_READING_LEVEL = "middle_school"

# OCR settings (placeholder for later)
OCR_LANGUAGE = "eng"
OCR_CONFIDENCE_THRESHOLD = 0.80

DEBUG_MODE = True
