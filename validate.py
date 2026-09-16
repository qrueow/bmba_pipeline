"""
Валидация ответов модели: устойчивый парсинг JSON + проверка схемы.
"""

import json
import re

from . import config

_REQUIRED_FIELDS = {
    "problem_number",
    "topic",
    "subtopic",
    "difficulty",
    "condition_latex",
    "has_figure",
    "figure_description",
    "solution_latex",
    "answer",
}

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(raw_text: str):
    """Модели иногда оборачивают JSON в ```json ... ``` несмотря на
    инструкцию — на всякий случай подчищаем перед парсингом."""
    cleaned = _JSON_FENCE_RE.sub("", raw_text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Не удалось распарсить JSON от модели: {e}\n"
            f"Первые 500 символов ответа:\n{cleaned[:500]}"
        ) from e


def validate_digitized_problems(problems: list[dict]) -> list[str]:
    """Возвращает список текстовых ошибок (пустой список = всё ок)."""
    errors = []
    for i, p in enumerate(problems):
        missing = _REQUIRED_FIELDS - p.keys()
        if missing:
            errors.append(f"Задача #{i}: отсутствуют поля {missing}")
            continue
        if not isinstance(p["difficulty"], int) or p["difficulty"] not in config.DIFFICULTY_RANGE:
            errors.append(
                f"Задача {p.get('problem_number')}: некорректная сложность "
                f"{p['difficulty']!r} (ожидается 1-5)"
            )
        if not p["condition_latex"] or not str(p["condition_latex"]).strip():
            errors.append(f"Задача {p.get('problem_number')}: пустое условие")
        if p["has_figure"] and not p.get("figure_description"):
            errors.append(
                f"Задача {p.get('problem_number')}: has_figure=true, но "
                f"figure_description пуст"
            )
    return errors


def validate_generated_test(data: dict, expected_total: int) -> list[str]:
    errors = []
    if "problems" not in data or "test_summary" not in data:
        return ["Ответ не содержит ключей 'problems' и/или 'test_summary'"]

    problems = data["problems"]
    if not isinstance(problems, list):
        return ["'problems' не является массивом"]

    errors.extend(validate_digitized_problems(problems))

    numbers = [p.get("problem_number") for p in problems]
    if sorted(numbers) != list(range(1, len(problems) + 1)):
        errors.append(
            f"problem_number не образуют непрерывную последовательность "
            f"1..{len(problems)}: {sorted(numbers)}"
        )

    if len(problems) != expected_total:
        errors.append(
            f"Ожидалось {expected_total} задач, получено {len(problems)} "
            f"(допустимо, если это осознанное решение — проверьте вручную)"
        )

    return errors
