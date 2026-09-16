"""
Режим 2 — генерация полного нового мок-теста на основе накопленной базы
задач-доноров через Gemini (двухэтапный промпт с защитой от подмены чисел).
"""

import json
from collections import Counter

from google import genai

from . import config, db
from .prompts import MODE2_PROMPT_TEMPLATE
from .validate import extract_json, validate_generated_test


def _analyze_structure(problems: list[dict]) -> tuple[int, dict, dict]:
    total = len(problems)
    by_topic = Counter(p["topic"] for p in problems)
    by_difficulty = Counter(str(p["difficulty"]) for p in problems)
    return total, dict(by_topic), dict(by_difficulty)


def generate_mock_test(variant_name: str = "generated-1") -> dict:
    """Возвращает dict с ключами 'problems' и 'test_summary'."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "Не задан GEMINI_API_KEY. Выполните: export GEMINI_API_KEY=..."
        )

    examples = db.fetch_all_digitized()
    if not examples:
        raise RuntimeError(
            "База пуста — сначала оцифруйте хотя бы один вариант (digitize)."
        )

    total, by_topic, by_difficulty = _analyze_structure(examples)

    prompt = MODE2_PROMPT_TEMPLATE.format(
        total=total,
        by_topic=json.dumps(by_topic, ensure_ascii=False),
        by_difficulty=json.dumps(by_difficulty, ensure_ascii=False),
        examples_json=json.dumps(examples, ensure_ascii=False),
    )

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=config.GENERATE_MODEL,
        contents=prompt,
    )

    data = extract_json(response.text)

    errors = validate_generated_test(data, expected_total=total)
    if errors:
        raise ValueError(
            "Сгенерированный тест не прошёл валидацию:\n" + "\n".join(errors)
        )

    db.insert_problems(
        data["problems"], variant_name=variant_name, source="generated"
    )

    return data
