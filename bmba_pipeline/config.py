# Configuration and constants for BMBA pipeline
import os
from pathlib import Path

# API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DIGITIZE_MODEL = "gemini-2.0-flash"
GENERATE_MODEL = "gemini-2.0-flash"

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
MOKS_DIR = BASE_DIR / "moks"
DB_PATH = DATA_DIR / "problems.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Database schema version
SCHEMA_VERSION = 1
