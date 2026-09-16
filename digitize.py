"""
Режим 1 — оцифровка PDF-скана варианта BMBA в JSON через Gemini.
"""

import json
from pathlib import Path

from google import genai

from . import config
from .prompts import MODE1_PROMPT
from .validate import extract_json, validate_digitized_problems


def digitize_pdf(pdf_path: Path) -> list[dict]:
    """Загружает PDF в Gemini, извлекает задачи, валидирует и возвращает
    список словарей в формате Режима 1."""
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "Не задан GEMINI_API_KEY. Выполните: export GEMINI_API_KEY=..."
        )

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    uploaded_file = client.files.upload(file=str(pdf_path))

    response = client.models.generate_content(
        model=config.DIGITIZE_MODEL,
        contents=[uploaded_file, MODE1_PROMPT],
    )

    raw_text = response.text
    data = extract_json(raw_text)

    if not isinstance(data, list):
        raise ValueError(
            "Ожидался JSON-массив задач, получен другой тип: "
            f"{type(data).__name__}. Проверьте сырой ответ модели вручную."
        )

    errors = validate_digitized_problems(data)
    if errors:
        raise ValueError(
            "Оцифрованные задачи не прошли валидацию:\n" + "\n".join(errors)
        )

    return data
