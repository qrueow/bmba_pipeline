"""
CLI для пайплайна BMBA mock-тестов.

Примеры:
    python -m bmba_pipeline.cli digitize PROMOCK-1.pdf --variant PROMOCK-1
    python -m bmba_pipeline.cli stats
    python -m bmba_pipeline.cli generate --variant generated-1
"""

import argparse
import json
import sys
from pathlib import Path

from . import config, db
from .digitize import digitize_pdf
from .generate import generate_mock_test


def cmd_digitize(args: argparse.Namespace) -> None:
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Файл не найден: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Оцифровываю {pdf_path} через {config.DIGITIZE_MODEL}...")
    problems = digitize_pdf(pdf_path)

    variant_name = args.variant or pdf_path.stem
    count = db.insert_problems(problems, variant_name=variant_name, source="digitized")
    print(f"Сохранено {count} задач в базу под именем варианта '{variant_name}'.")

    if args.export:
        out_path = config.OUTPUT_DIR / f"{variant_name}.json"
        db.export_json(problems, out_path)
        print(f"Также экспортировано в {out_path}")


def cmd_digitize_batch(args: argparse.Namespace) -> None:
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Папка не найдена: {folder}", file=sys.stderr)
        sys.exit(1)

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"В папке {folder} нет файлов *.pdf")
        return

    print(f"Найдено {len(pdf_files)} файлов. Начинаю оцифровку через {config.DIGITIZE_MODEL}...\n")

    already_done = set(db.fetch_variant_names()) if args.skip_existing else set()

    ok, failed, skipped = [], [], []
    for pdf_path in pdf_files:
        variant_name = pdf_path.stem

        if variant_name in already_done:
            print(f"[ПРОПУЩЕН] {pdf_path.name} — вариант '{variant_name}' уже есть в базе")
            skipped.append(pdf_path.name)
            continue

        print(f"[...] {pdf_path.name}")
        try:
            problems = digitize_pdf(pdf_path)
            count = db.insert_problems(problems, variant_name=variant_name, source="digitized")
            if args.export:
                db.export_json(problems, config.OUTPUT_DIR / f"{variant_name}.json")
            print(f"[OK]  {pdf_path.name} — сохранено {count} задач как '{variant_name}'")
            ok.append(pdf_path.name)
        except Exception as e:  # noqa: BLE001 — батч должен продолжаться при ошибке на одном файле
            print(f"[ОШИБКА] {pdf_path.name}: {e}", file=sys.stderr)
            failed.append((pdf_path.name, str(e)))

    print("\n--- Итог ---")
    print(f"Успешно: {len(ok)}")
    print(f"Пропущено (уже в базе): {len(skipped)}")
    print(f"С ошибками: {len(failed)}")
    if failed:
        print("\nФайлы с ошибками (можно перезапустить только их):")
        for name, err in failed:
            print(f"  - {name}: {err}")


def cmd_stats(args: argparse.Namespace) -> None:
    problems = db.fetch_all_digitized()
    if not problems:
        print("База пуста.")
        return
    from collections import Counter

    by_topic = Counter(p["topic"] for p in problems)
    by_difficulty = Counter(p["difficulty"] for p in problems)
    variants = db.fetch_variant_names()

    print(f"Всего задач-доноров: {len(problems)}")
    print(f"Вариантов в базе: {', '.join(variants)}")
    print("По темам:")
    for topic, count in by_topic.most_common():
        print(f"  {topic}: {count}")
    print("По сложности:")
    for diff in sorted(by_difficulty):
        print(f"  {diff}: {by_difficulty[diff]}")


def cmd_generate(args: argparse.Namespace) -> None:
    print(f"Генерирую новый мок-тест через {config.GENERATE_MODEL}...")
    result = generate_mock_test(variant_name=args.variant)

    out_path = config.OUTPUT_DIR / f"{args.variant}.json"
    db.export_json(result["problems"], out_path)

    print(f"Готово. Сохранено {len(result['problems'])} задач в {out_path}")
    print("Сводка (test_summary):")
    print(json.dumps(result["test_summary"], ensure_ascii=False, indent=2))


def main() -> None:
    db.init_db()

    parser = argparse.ArgumentParser(description="BMBA mock-test pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_digitize = sub.add_parser("digitize", help="Оцифровать PDF-скан варианта")
    p_digitize.add_argument("pdf_path", help="Путь к PDF-файлу")
    p_digitize.add_argument("--variant", help="Имя варианта (по умолчанию — имя файла)")
    p_digitize.add_argument(
        "--export", action="store_true", help="Также сохранить JSON в output/"
    )
    p_digitize.set_defaults(func=cmd_digitize)

    p_batch = sub.add_parser(
        "digitize-batch", help="Оцифровать все PDF из папки одной командой"
    )
    p_batch.add_argument("folder", help="Путь к папке с PDF-файлами моков")
    p_batch.add_argument(
        "--export", action="store_true", help="Также сохранить JSON каждого варианта в output/"
    )
    p_batch.add_argument(
        "--skip-existing",
        action="store_true",
        help="Пропускать файлы, чьё имя уже есть как variant_name в базе",
    )
    p_batch.set_defaults(func=cmd_digitize_batch)

    p_stats = sub.add_parser("stats", help="Показать статистику базы")
    p_stats.set_defaults(func=cmd_stats)

    p_generate = sub.add_parser("generate", help="Сгенерировать новый мок-тест")
    p_generate.add_argument(
        "--variant", default="generated-1", help="Имя нового варианта"
    )
    p_generate.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
