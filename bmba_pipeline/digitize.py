"""Mode 1: PDF digitization - convert PDF scans to structured JSON via Gemini."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import base64
from . import config, prompts
from .validate import parse_problems_list, validate_problem_consistency
from .db import ProblemsDB


def encode_image_to_base64(image_path: Path) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def digitize_pdf(pdf_path: Path, variant_name: str, db: Optional[ProblemsDB] = None) -> List[Dict[str, Any]]:
    """
    Digitize a PDF file using Gemini vision API.
    
    Args:
        pdf_path: Path to PDF file
        variant_name: Name for this variant in the database
        db: ProblemsDB instance (optional, for saving to database)
    
    Returns:
        List of parsed problems
    """
    try:
        import google.generativeai as genai
    except ImportError:
        print("google-genai not installed. Install with: pip install google-genai")
        return []
    
    if not config.GEMINI_API_KEY:
        print("GEMINI_API_KEY not set")
        return []
    
    genai.configure(api_key=config.GEMINI_API_KEY)
    
    # For this example, we'll assume the PDF can be read as bytes
    # In production, you might use PyPDF2 or pdfplumber to extract pages
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        # Create Gemini request with the PDF
        model = genai.GenerativeModel(config.DIGITIZE_MODEL)
        
        # Note: Gemini API handles PDF directly or we convert to images
        response = model.generate_content([
            prompts.DIGITIZE_PROMPT,
            pdf_data  # Gemini can handle PDF bytes directly in some cases
        ])
        
        # Parse response
        problems = parse_problems_list(response.text)
        problems = validate_problem_consistency(problems)
        
        # Save to database if provided
        if db and problems:
            for problem in problems:
                db.insert_problem(
                    variant_name=variant_name,
                    problem_number=problem.get("problem_number"),
                    content=problem.get("content"),
                    difficulty=problem.get("difficulty"),
                    theme=problem.get("theme"),
                    source_file=pdf_path.name
                )
        
        return problems
    
    except Exception as e:
        print(f"Error digitizing {pdf_path}: {e}")
        return []


def digitize_batch(moks_dir: Path, skip_existing: bool = False, 
                   db: Optional[ProblemsDB] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Digitize all PDF files in a directory.
    
    Args:
        moks_dir: Directory containing PDF files
        skip_existing: Skip variants already in database
        db: ProblemsDB instance
    
    Returns:
        Dictionary mapping variant names to their problems
    """
    db = db or ProblemsDB()
    results = {}
    failed = []
    
    pdf_files = sorted(moks_dir.glob("*.pdf"))
    
    for pdf_path in pdf_files:
        variant_name = pdf_path.stem  # filename without .pdf
        
        # Skip if already processed
        if skip_existing:
            existing = db.get_problems_by_variant(variant_name)
            if existing:
                print(f"Skipping {variant_name} (already in database)")
                results[variant_name] = existing
                continue
        
        print(f"Processing {pdf_path.name}...")
        
        try:
            problems = digitize_pdf(pdf_path, variant_name, db=db)
            if problems:
                results[variant_name] = problems
                print(f"  → {len(problems)} problems extracted")
            else:
                failed.append(pdf_path.name)
                print(f"  → Failed to extract problems")
        except Exception as e:
            failed.append(pdf_path.name)
            print(f"  → Error: {e}")
    
    if failed:
        print(f"\nFailed files: {', '.join(failed)}")
    
    return results


def export_variant_to_json(variant_name: str, output_path: Path, 
                          db: Optional[ProblemsDB] = None) -> bool:
    """Export a variant's problems to JSON file."""
    db = db or ProblemsDB()
    
    problems = db.get_problems_by_variant(variant_name)
    if not problems:
        print(f"No problems found for variant {variant_name}")
        return False
    
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(problems, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(problems)} problems to {output_path}")
    return True
