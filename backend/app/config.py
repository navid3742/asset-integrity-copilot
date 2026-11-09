"""Centralized environment configuration. Secrets never reach the browser."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATA_DIR = Path(os.getenv('DATA_DIR', str(ROOT / 'backend' / 'data')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = Path(os.getenv('DATABASE_PATH', str(DATA_DIR / 'asset_integrity.sqlite3')))
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
DEMO_PASSWORD = os.getenv('DEMO_PASSWORD', '').strip()
# Live AI requires a password to avoid public visitors exhausting paid API credits.
LIVE_ENABLED = bool(API_KEY and DEMO_PASSWORD)
ENABLE_EMBEDDINGS = os.getenv('ENABLE_EMBEDDINGS', 'true').lower() == 'true'
MAX_TOOL_ROUNDS = min(max(int(os.getenv('MAX_TOOL_ROUNDS', '4')), 1), 6)
MAX_API_REQUESTS_PER_HOUR = int(os.getenv('MAX_API_REQUESTS_PER_HOUR', '35'))
MAX_ESTIMATED_SPEND_USD = float(os.getenv('MAX_ESTIMATED_SPEND_USD', '3'))
INPUT_USD_PER_MILLION = float(os.getenv('INPUT_USD_PER_MILLION', '0.40'))
OUTPUT_USD_PER_MILLION = float(os.getenv('OUTPUT_USD_PER_MILLION', '1.60'))
STATIC_DIR = ROOT / 'frontend' / 'dist'

# SDK tracing is opt-in. Keep prompts/tool inputs out of exported traces.
ENABLE_SDK_TRACING = os.getenv('ENABLE_SDK_TRACING', 'false').lower() == 'true'
