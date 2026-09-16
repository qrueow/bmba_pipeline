"""Validation and robust parsing of JSON responses."""
import json
import re
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Theme(str, Enum):
    ALGEBRA = "algebra"
    GEOMETRY = "geometry"
    TRIGONOMETRY = "trigonometry"
    CALCULUS = "calculus"
    STATISTICS = "statistics"
    LOGIC = "logic"
    OTHER = "other"


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object from text that may contain additional content."""
    # Try to find JSON array or object
    json_pattern = r'\{[\s\S]*\}|\[[\s\S]*\]'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # If no valid JSON found, try parsing the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def validate_problem(problem: Dict[str, Any]) -> bool:
    """Validate problem structure and required fields."""
    required_fields = ["problem_number", "content"]
    
    # Check required fields
    for field in required_fields:
        if field not in problem or not problem[field]:
            return False
    
    # Validate problem_number
    if not isinstance(problem["problem_number"], int) or problem["problem_number"] <= 0:
        return False
    
    # Validate content is non-empty string
    if not isinstance(problem["content"], str) or not problem["content"].strip():
        return False
    
    # Validate optional fields if present
    if "difficulty" in problem and problem["difficulty"]:
        if problem["difficulty"] not in [d.value for d in Difficulty]:
            return False
    
    if "theme" in problem and problem["theme"]:
        if problem["theme"] not in [t.value for t in Theme]:
            return False
    
    return True


def parse_problems_list(response_text: str) -> List[Dict[str, Any]]:
    """Parse response containing list of problems."""
    try:
        # Try to extract JSON from response
        json_data = extract_json_from_text(response_text)
        
        if isinstance(json_data, list):
            problems = json_data
        elif isinstance(json_data, dict):
            # Check if it's a single problem
            if "problem_number" in json_data:
                problems = [json_data]
            # Check if problems are nested under a key
            elif "problems" in json_data:
                problems = json_data["problems"] if isinstance(json_data["problems"], list) else []
            else:
                problems = []
        else:
            problems = []
        
        # Validate each problem
        valid_problems = []
        for problem in problems:
            if isinstance(problem, dict) and validate_problem(problem):
                valid_problems.append(problem)
        
        return valid_problems
    
    except Exception as e:
        print(f"Error parsing problems: {e}")
        return []


def parse_generated_problem(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse response from generation prompt."""
    try:
        json_data = extract_json_from_text(response_text)
        
        if not isinstance(json_data, dict):
            return None
        
        # Validate required fields for generated problem
        required = ["content", "difficulty", "theme"]
        if not all(field in json_data for field in required):
            return None
        
        # Validate values
        if json_data["difficulty"] not in [d.value for d in Difficulty]:
            json_data["difficulty"] = "medium"
        
        if json_data["theme"] not in [t.value for t in Theme]:
            json_data["theme"] = "other"
        
        return {
            "content": str(json_data.get("content", "")).strip(),
            "difficulty": json_data.get("difficulty", "medium"),
            "theme": json_data.get("theme", "other"),
            "context_change": json_data.get("context_change"),
            "numerical_changes": json_data.get("numerical_changes"),
            "anti_copy_checklist": json_data.get("anti_copy_checklist", [])
        }
    
    except Exception as e:
        print(f"Error parsing generated problem: {e}")
        return None


def validate_problem_consistency(problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate problem sequence consistency (numbering, etc)."""
    if not problems:
        return []
    
    # Sort by problem number
    sorted_problems = sorted(problems, key=lambda p: p.get("problem_number", 0))
    
    # Check for gaps in numbering
    valid_problems = []
    expected_number = 1
    
    for problem in sorted_problems:
        actual_number = problem.get("problem_number", 0)
        if actual_number == expected_number:
            valid_problems.append(problem)
            expected_number += 1
        elif actual_number > expected_number:
            # Gap detected - we can either skip or renumber
            # For now, we skip and note it
            print(f"Gap in problem numbering: expected {expected_number}, got {actual_number}")
    
    return valid_problems
