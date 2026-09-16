"""Mode 2: Test generation - create new problems based on database via Gemini."""
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from . import config, prompts
from .validate import parse_generated_problem
from .db import ProblemsDB


def generate_new_problem(template_problem: Dict[str, Any], 
                        db: Optional[ProblemsDB] = None) -> Optional[Dict[str, Any]]:
    """
    Generate a new problem based on a template using two-stage prompting.
    
    Args:
        template_problem: Problem from database to use as template
        db: ProblemsDB instance
    
    Returns:
        New generated problem or None if generation failed
    """
    try:
        import google.generativeai as genai
    except ImportError:
        print("google-genai not installed")
        return None
    
    if not config.GEMINI_API_KEY:
        print("GEMINI_API_KEY not set")
        return None
    
    genai.configure(api_key=config.GEMINI_API_KEY)
    
    model = genai.GenerativeModel(config.GENERATE_MODEL)
    
    try:
        # Stage 1: Abstraction (internal, no output yet)
        stage1_prompt = prompts.GENERATE_PROMPT_STAGE1 + "\n\nEtalon problem:\n" + json.dumps(template_problem, ensure_ascii=False)
        
        response1 = model.generate_content(stage1_prompt)
        
        # Stage 2: Instantiation with transformation
        stage2_prompt = prompts.GENERATE_PROMPT_STAGE2
        response2 = model.generate_content([stage1_prompt, response1.text, stage2_prompt])
        
        # Parse the generated problem
        generated = parse_generated_problem(response2.text)
        
        return generated
    
    except Exception as e:
        print(f"Error generating problem: {e}")
        return None


def generate_new_mock_test(variant_name: str, db: Optional[ProblemsDB] = None,
                          distribution: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Generate a complete new mock test maintaining the distribution of original database.
    
    Args:
        variant_name: Name for the new variant
        db: ProblemsDB instance
        distribution: Optional custom problem distribution {theme/difficulty: count}
    
    Returns:
        Generated test with metadata
    """
    db = db or ProblemsDB()
    
    # Get all problems from database
    all_problems = db.get_all_problems()
    if not all_problems:
        print("No problems in database for generation")
        return {"variant_name": variant_name, "problems": []}
    
    # Determine distribution (if not provided)
    if distribution is None:
        # Use same distribution as source database
        stats = db.get_stats()
        # For now, generate one problem per unique difficulty/theme combo
        distribution = {
            "count": len(all_problems)  # Generate same number of problems
        }
    
    target_count = distribution.get("count", len(all_problems))
    
    generated_problems = []
    attempted = 0
    max_attempts = target_count * 2  # Allow retries
    
    while len(generated_problems) < target_count and attempted < max_attempts:
        # Pick random template from database
        template = random.choice(all_problems)
        attempted += 1
        
        print(f"Generating problem from template #{template.get('problem_number')} ({template.get('theme')}/{template.get('difficulty')})...")
        
        new_problem = generate_new_problem(template, db=db)
        
        if new_problem:
            # Assign new problem number
            new_problem["problem_number"] = len(generated_problems) + 1
            new_problem["variant_name"] = variant_name
            new_problem["template_id"] = template.get("id")
            generated_problems.append(new_problem)
            print(f"  ✓ Generated #{new_problem['problem_number']}")
        else:
            print(f"  ✗ Generation failed, retrying...")
    
    result = {
        "variant_name": variant_name,
        "problems": generated_problems,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_problems": len(generated_problems),
            "success_rate": f"{len(generated_problems)/attempted*100:.1f}%" if attempted > 0 else "0%"
        }
    }
    
    return result


def export_test_to_json(test_data: Dict[str, Any], output_path: Path) -> bool:
    """Export generated test to JSON file."""
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"Test exported to {output_path}")
    return True


def print_test_summary(test_data: Dict[str, Any]) -> None:
    """Print summary of generated test."""
    print("\n=== Test Summary ===")
    print(f"Variant: {test_data['variant_name']}")
    print(f"Total problems: {len(test_data['problems'])}")
    
    if "metadata" in test_data:
        meta = test_data["metadata"]
        print(f"Generated at: {meta.get('generated_at', 'N/A')}")
        print(f"Success rate: {meta.get('success_rate', 'N/A')}")
    
    # Summary by difficulty and theme
    difficulty_count = {}
    theme_count = {}
    
    for problem in test_data["problems"]:
        difficulty = problem.get("difficulty", "unknown")
        theme = problem.get("theme", "unknown")
        difficulty_count[difficulty] = difficulty_count.get(difficulty, 0) + 1
        theme_count[theme] = theme_count.get(theme, 0) + 1
    
    print("\nBy difficulty:")
    for difficulty in sorted(difficulty_count.keys()):
        print(f"  {difficulty}: {difficulty_count[difficulty]}")
    
    print("\nBy theme:")
    for theme in sorted(theme_count.keys()):
        print(f"  {theme}: {theme_count[theme]}")
