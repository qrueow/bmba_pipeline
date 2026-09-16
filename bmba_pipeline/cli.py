"""Command-line interface for BMBA pipeline."""
import sys
from pathlib import Path
from datetime import datetime
import argparse
from . import config
from .db import ProblemsDB
from .digitize import digitize_pdf, digitize_batch, export_variant_to_json
from .generate import generate_new_mock_test, export_test_to_json, print_test_summary


def main():
    parser = argparse.ArgumentParser(description="BMBA Mock Test Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Digitize command
    digitize_parser = subparsers.add_parser("digitize", help="Digitize a single PDF")
    digitize_parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    digitize_parser.add_argument("--variant", type=str, required=True, help="Variant name")
    digitize_parser.add_argument("--export", action="store_true", help="Export to JSON")
    
    # Digitize-batch command
    batch_parser = subparsers.add_parser("digitize-batch", help="Digitize all PDFs in directory")
    batch_parser.add_argument("directory", type=Path, help="Directory with PDFs")
    batch_parser.add_argument("--export", action="store_true", help="Export to JSON files")
    batch_parser.add_argument("--skip-existing", action="store_true", help="Skip already processed variants")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate new mock test")
    generate_parser.add_argument("--variant", type=str, help="Variant name (default: current date)")
    generate_parser.add_argument("--export", action="store_true", help="Export to JSON")
    generate_parser.add_argument("--count", type=int, help="Number of problems to generate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    db = ProblemsDB()
    
    try:
        if args.command == "digitize":
            if not args.pdf_path.exists():
                print(f"Error: {args.pdf_path} not found")
                return 1
            
            print(f"Digitizing {args.pdf_path}...")
            problems = digitize_pdf(args.pdf_path, args.variant, db=db)
            
            if problems:
                print(f"✓ Extracted {len(problems)} problems")
                for p in problems:
                    print(f"  - #{p['problem_number']}: {p['content'][:60]}...")
                
                if args.export:
                    output_file = config.OUTPUT_DIR / f"{args.variant}.json"
                    export_variant_to_json(args.variant, output_file, db=db)
            else:
                print("✗ No problems extracted")
                return 1
        
        elif args.command == "digitize-batch":
            if not args.directory.is_dir():
                print(f"Error: {args.directory} is not a directory")
                return 1
            
            results = digitize_batch(args.directory, skip_existing=args.skip_existing, db=db)
            
            print(f"\n✓ Processed {len(results)} variants")
            for variant_name, problems in results.items():
                print(f"  {variant_name}: {len(problems)} problems")
                
                if args.export:
                    output_file = config.OUTPUT_DIR / f"{variant_name}.json"
                    export_variant_to_json(variant_name, output_file, db=db)
        
        elif args.command == "stats":
            stats = db.get_stats()
            print("\n=== Database Statistics ===")
            print(f"Total problems: {stats['total_problems']}")
            print(f"Total variants: {stats['total_variants']}")
            
            if stats['difficulty_distribution']:
                print("\nBy difficulty:")
                for difficulty, count in sorted(stats['difficulty_distribution'].items()):
                    print(f"  {difficulty}: {count}")
            
            if stats['theme_distribution']:
                print("\nBy theme:")
                for theme, count in sorted(stats['theme_distribution'].items()):
                    print(f"  {theme}: {count}")
        
        elif args.command == "generate":
            variant_name = args.variant or f"mock-{datetime.now().strftime('%Y-%m-%d')}"
            
            print(f"Generating new test: {variant_name}...")
            
            distribution = None
            if args.count:
                distribution = {"count": args.count}
            
            test_data = generate_new_mock_test(variant_name, db=db, distribution=distribution)
            
            print_test_summary(test_data)
            
            if args.export:
                output_file = config.OUTPUT_DIR / f"{variant_name}.json"
                export_test_to_json(test_data, output_file)
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
