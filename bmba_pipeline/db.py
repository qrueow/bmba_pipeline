"""SQLite database management for problems storage."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from . import config


class ProblemsDB:
    """Database wrapper for BMBA problems."""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    variant_name TEXT NOT NULL,
                    problem_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    solution TEXT,
                    difficulty TEXT,
                    theme TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT,
                    UNIQUE(variant_name, problem_number)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS variants (
                    name TEXT PRIMARY KEY,
                    file_path TEXT,
                    problem_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            """)
            conn.commit()
    
    def insert_problem(self, variant_name: str, problem_number: int, 
                      content: str, solution: Optional[str] = None,
                      difficulty: Optional[str] = None, theme: Optional[str] = None,
                      source_file: Optional[str] = None) -> int:
        """Insert a problem into the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO problems 
                (variant_name, problem_number, content, solution, difficulty, theme, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (variant_name, problem_number, content, solution, difficulty, theme, source_file))
            conn.commit()
            return cursor.lastrowid
    
    def get_problems_by_variant(self, variant_name: str) -> List[Dict[str, Any]]:
        """Retrieve all problems for a variant."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM problems WHERE variant_name = ? ORDER BY problem_number
            """, (variant_name,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_problems(self) -> List[Dict[str, Any]]:
        """Retrieve all problems from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM problems ORDER BY variant_name, problem_number")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM problems")
            total_problems = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT variant_name) FROM problems")
            total_variants = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT difficulty, COUNT(*) as count FROM problems 
                GROUP BY difficulty ORDER BY difficulty
            """)
            difficulty_dist = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor = conn.execute("""
                SELECT theme, COUNT(*) as count FROM problems 
                GROUP BY theme ORDER BY theme
            """)
            theme_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_problems": total_problems,
            "total_variants": total_variants,
            "difficulty_distribution": difficulty_dist,
            "theme_distribution": theme_dist
        }
