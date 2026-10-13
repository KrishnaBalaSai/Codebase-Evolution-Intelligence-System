"""
Code metrics and complexity analysis using Radon.
Computes Cyclomatic Complexity (CC), Raw Metrics (LOC/SLOC/Comments),
and calculates multi-factor Code Hotspot scores.
"""

import os
from typing import Dict, Any, List, Optional
import radon.complexity as cc_mod
import radon.raw as raw_mod


def analyze_file_complexity(file_full_path: str, relative_path: str) -> Dict[str, Any]:
    """
    Analyzes complexity and code metrics for a file.
    If the file is a Python file (.py), uses Radon for Cyclomatic Complexity and Raw LOC.
    For non-Python files, performs standard line counting.
    """
    default_metrics = {
        "loc": 0, 
        "sloc": 0,
        "comments": 0,
        "cyclomatic_complexity": 1.0,
        "complexity_rank": "A",
        "functions_count": 0,
        "classes_count": 0,
    }

    if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
        return default_metrics

    # Read file content safely
    content = ""
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(file_full_path, "r", encoding=enc, errors="replace") as f:
                content = f.read()
            break
        except Exception:
            continue

    if not content:
        return default_metrics

    lines = content.splitlines()
    loc = len(lines)
    default_metrics["loc"] = loc

    # Non-Python file fallback
    if not relative_path.lower().endswith(".py"):
        non_blank = sum(1 for line in lines if line.strip())
        comments_approx = sum(1 for line in lines if line.strip().startswith(("//", "#", "/*", "*", "<!--")))
        default_metrics["sloc"] = non_blank - comments_approx
        default_metrics["comments"] = comments_approx
        default_metrics["cyclomatic_complexity"] = 1.0
        default_metrics["complexity_rank"] = "A"
        return default_metrics

    # Python File: Apply Radon Analysis
    try:
        # Raw metrics (LOC, SLOC, Comments, Multi-line docstrings, Blanks)
        raw_res = raw_mod.analyze(content)
        default_metrics["loc"] = raw_res.loc
        default_metrics["sloc"] = raw_res.sloc
        default_metrics["comments"] = raw_res.comments + raw_res.multi
    except Exception:
        default_metrics["sloc"] = loc

    try:
        # Cyclomatic Complexity
        blocks = cc_mod.cc_visit(content)
        if blocks:
            # Calculate average complexity across functions/methods/classes
            complexities = [b.complexity for b in blocks]
            avg_cc = sum(complexities) / len(complexities)
            default_metrics["cyclomatic_complexity"] = round(avg_cc, 2)
            default_metrics["complexity_rank"] = cc_mod.cc_rank(avg_cc)
            default_metrics["functions_count"] = sum(1 for b in blocks if hasattr(b, "letter") and b.letter in ("F", "M"))
            default_metrics["classes_count"] = sum(1 for b in blocks if hasattr(b, "letter") and b.letter == "C")
        else:
            default_metrics["cyclomatic_complexity"] = 1.0
            default_metrics["complexity_rank"] = "A"
    except Exception:
        # Syntax error in target file or Radon parse issue
        default_metrics["cyclomatic_complexity"] = 1.0
        default_metrics["complexity_rank"] = "A"

    return default_metrics


def calculate_hotspot_scores(files_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates Code Hotspot score (0 - 100) based on:
    1. File change frequency (weight 40%)
    2. Bug-fix activity count (weight 35%)
    3. Code complexity (weight 25%)

    Also provides an explanatory text for why the file was identified as a hotspot.
    """
    if not files_data:
        return []

    # Find max values for normalization
    max_changes = max((f.get("change_count", 0) for f in files_data), default=1) or 1
    max_bugs = max((f.get("bug_fix_count", 0) for f in files_data), default=1) or 1
    max_complexity = max((f.get("cyclomatic_complexity", 1.0) for f in files_data), default=1.0) or 1.0

    rank_weight = {
        "A": 1.0,
        "B": 2.0,
        "C": 4.0,
        "D": 6.0,
        "E": 8.0,
        "F": 10.0
    }

    scored_files = []
    for f in files_data:
        changes = f.get("change_count", 0)
        bugs = f.get("bug_fix_count", 0)
        complexity = f.get("cyclomatic_complexity", 1.0)
        rank = f.get("complexity_rank", "A")

        # Normalized values [0.0 - 1.0]
        norm_changes = min(1.0, changes / max_changes)
        norm_bugs = min(1.0, bugs / max_bugs)
        
        # Rank-enhanced complexity factor
        cc_factor = min(1.0, (complexity / max_complexity) * 0.7 + (rank_weight.get(rank, 1.0) / 10.0) * 0.3)

        # Composite score from 0.0 to 100.0
        composite_score = round((0.40 * norm_changes + 0.35 * norm_bugs + 0.25 * cc_factor) * 100, 1)

        # Risk categorization
        if composite_score >= 65:
            risk_level = "High"
        elif composite_score >= 35:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Generate explanatory reason
        reasons = []
        if changes > 0:
            reasons.append(f"{changes} commits")
        if bugs > 0:
            reasons.append(f"{bugs} bug-fixes")
        reasons.append(f"CC: {complexity} (Rank {rank})")
        explanation = f"Hotspot ({risk_level} Risk): modified in {', '.join(reasons)}."

        f_copy = dict(f)
        f_copy["hotspot_score"] = composite_score
        f_copy["risk_level"] = risk_level
        f_copy["hotspot_explanation"] = explanation
        scored_files.append(f_copy)

    # Sort descending by hotspot score
    scored_files.sort(key=lambda x: x["hotspot_score"], reverse=True)
    return scored_files
