"""
Конфигурация пайплайна BMBA mock-тестов.

API-ключ Gemini берётся из переменной окружения GEMINI_API_KEY.
Никогда не храните ключ прямо в коде.

    export GEMINI_API_KEY="ваш_ключ"
"""

import os
from pathlib import Path

# --- API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Модели можно поменять при необходимости (проверяйте актуальный список
# моделей в документации Gemini API — названия версий периодически меняются).
DIGITIZE_MODEL = os.environ.get("BMBA_DIGITIZE_MODEL", "gemini-2.5-pro")
GENERATE_MODEL = os.environ.get("BMBA_GENERATE_MODEL", "gemini-2.5-pro")

# --- Пути ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("BMBA_DB_PATH", BASE_DIR / "data" / "problems.db"))
OUTPUT_DIR = Path(os.environ.get("BMBA_OUTPUT_DIR", BASE_DIR / "output"))

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Допустимые значения (валидация) ---
VALID_TOPICS = {
    "алгебра",
    "геометрия",
    "тригонометрия",
    "анализ функций",
    "комбинаторика",
    "теория вероятностей",
    "стереометрия",
}
DIFFICULTY_RANGE = range(1, 6)  # 1..5
