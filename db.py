"""
SQLite-хранилище оцифрованных и сгенерированных задач.

Таблица problems хранит и задачи-доноры (source='digitized'), и
сгенерированные задачи (source='generated'), чтобы можно было анализировать
статистику отдельно и вместе.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_name TEXT NOT NULL,
    problem_number INTEGER NOT NULL,
    topic TEXT NOT NULL,
    subtopic TEXT,
    difficulty INTEGER NOT NULL,
    condition_latex TEXT NOT NULL,
    has_figure INTEGER NOT NULL DEFAULT 0,
    figure_description TEXT,
    solution_latex TEXT,
    answer TEXT,
    source TEXT NOT NULL CHECK(source IN ('digitized', 'generated')),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_problems_topic ON problems(topic);
CREATE INDEX IF NOT EXISTS idx_problems_variant ON problems(variant_name);
"""


@contextmanager
def get_conn(db_path: Path = config.DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path = config.DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def insert_problems(
    problems: Iterable[dict],
    variant_name: str,
    source: str,
    db_path: Path = config.DB_PATH,
) -> int:
    """Сохраняет список задач (в формате Режима 1/2) в базу. Возвращает
    количество вставленных строк."""
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            variant_name,
            p["problem_number"],
            p["topic"],
            p.get("subtopic"),
            p["difficulty"],
            p["condition_latex"],
            int(bool(p.get("has_figure", False))),
            p.get("figure_description"),
            p.get("solution_latex"),
            p.get("answer"),
            source,
            now,
        )
        for p in problems
    ]
    with get_conn(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO problems (
                variant_name, problem_number, topic, subtopic, difficulty,
                condition_latex, has_figure, figure_description,
                solution_latex, answer, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return len(rows)


def fetch_all_digitized(db_path: Path = config.DB_PATH) -> list[dict]:
    """Возвращает все оцифрованные (не сгенерированные) задачи — это база
    примеров для Режима 2."""
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT * FROM problems WHERE source = 'digitized' "
            "ORDER BY variant_name, problem_number"
        )
        return [_row_to_problem_dict(r) for r in cur.fetchall()]


def fetch_variant_names(db_path: Path = config.DB_PATH) -> list[str]:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT DISTINCT variant_name FROM problems WHERE source = 'digitized'"
        )
        return [r["variant_name"] for r in cur.fetchall()]


def _row_to_problem_dict(row: sqlite3.Row) -> dict:
    return {
        "problem_number": row["problem_number"],
        "topic": row["topic"],
        "subtopic": row["subtopic"],
        "difficulty": row["difficulty"],
        "condition_latex": row["condition_latex"],
        "has_figure": bool(row["has_figure"]),
        "figure_description": row["figure_description"],
        "solution_latex": row["solution_latex"],
        "answer": row["answer"],
    }


def export_json(problems: list[dict], path: Path) -> None:
    path.write_text(
        json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8"
    )
