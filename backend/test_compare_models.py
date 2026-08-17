"""
Four-model comparison for the Lab Generator, through the REAL pipeline.

Unlike the previous version of this script, this does NOT call the models
raw and score their first draft with custom regex heuristics. It runs each
model through compare_lab_code_models(), which is the exact same code path
generate_lab_exercise() uses in production: per-topic decomposition ->
validation -> up to 2 repair attempts -> plan-compliance check against the
Groq-authored code_plan. What you get out is what a real lab would actually
look like with that model plugged in, not a raw-output proxy for it.

Run from backend/:
    python test_compare_models.py

Note: routing "groq" or "gemini" as a code_model now works (see the
_coder_invoke_safe update) — but be aware this adds real Groq call volume
on top of everything else Groq already does per lesson (scaffold + repair
attempts), so this can hit the same TPM throttling you've seen before.
Test on ONE lesson first, not a full course.
"""

import json
import os
from typing import List, Dict
from agents.tools import (
    generate_lab_exercise,
    detect_gaps,
    generate_course,
    generate_teaching_plan,
    get_papers_with_analysis,
    search_similar_projects,
    compute_similarity_scores,
)

IDEA = "fake news detection using transformer models"
CACHE_FILE = "test_pipeline_cache.json"
MODULE_TITLE_CONTAINS = "Transformer"
CODE_MODEL = "qwen2.5-coder:7b"


def get_or_build_pipeline_output():
    if os.path.exists(CACHE_FILE):
        print(f"[cache] loading pipeline output from {CACHE_FILE}")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[cache] no cache found — running the full pipeline once (uses Groq quota)...")
    papers_with_analysis = get_papers_with_analysis(IDEA, max_papers=3)
    gaps_result = detect_gaps(IDEA, papers_with_analysis)
    teaching_plan = generate_teaching_plan(IDEA, gaps_result.get("gaps", []), papers_with_analysis)
    course = generate_course(teaching_plan, papers_with_analysis)

    similar = search_similar_projects(IDEA, max_results=15)
    scored_similar = compute_similarity_scores(IDEA, similar)
    scored_similar_json = [[score, proj] for score, proj in scored_similar]

    data = {
        "papers_with_analysis": papers_with_analysis,
        "teaching_plan": teaching_plan,
        "course": course,
        "scored_similar": scored_similar_json,
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[cache] saved pipeline output to {CACHE_FILE}")
    return data


def run_one_shot_lab_generator_cache(cache_path: str = "lab_generator_cache.json", model_name: str = "qwen2.5-coder:7b") -> Dict:
    """Run the existing lab generation path once (scaffold + per-topic code generation + repair)
    and save the output to a cache file for faster repeated tests.

    This avoids re-running the expensive Groq scaffold+analysis steps on every test run.
    """
    if os.path.exists(cache_path):
        print(f"[lab cache] loading lab generator cache from {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("[lab cache] no lab cache found — running the lab generator once...")
    data = get_or_build_pipeline_output()
    scored_similar = [tuple(item) for item in data["scored_similar"]]
    module, lesson = find_module_and_lesson(data["teaching_plan"], data["course"], MODULE_TITLE_CONTAINS)

    # Use the production compare path but only keep the RESULTS for a single model run
    chosen = model_name or MODELS[0]
    comparison = compare_lab_code_models(
        lesson=lesson,
        module=module,
        papers_with_analysis=data["papers_with_analysis"],
        similar_projects_scored=scored_similar,
        models=(chosen,),
    )

    if comparison.get("_error"):
        print(f"Lab generator run failed: {comparison.get('_error')}")
        return {"_error": comparison.get("_error")}

    result = {"scaffold": comparison.get("scaffold"), "result": comparison.get("results", {}).get(chosen)}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"[lab cache] saved lab generator output to {cache_path}")
    return result


def find_module_and_lesson(teaching_plan, course, title_contains):
    tp_module = next(
        (m for m in teaching_plan.get("modules", [])
         if title_contains.lower() in m.get("title", "").lower()),
        None,
    )
    course_module = next(
        (m for m in course.get("modules", [])
         if title_contains.lower() in m.get("module_title", "").lower()),
        None,
    )
    if not tp_module or not course_module or not course_module.get("lessons"):
        available = [m.get("title", "") for m in teaching_plan.get("modules", [])]
        raise ValueError(f"No module matched '{title_contains}'. Available module titles: {available}")
    lesson = course_module["lessons"][0]
    return tp_module, lesson


def summarize(model_name, code_result):
    v = code_result.get("validation", {})
    starter_v = v.get("starter", {})
    solution_v = v.get("solution", {})

    dup_names = [
        d["name"] for d in (starter_v.get("duplicate_definitions", []) + solution_v.get("duplicate_definitions", []))
        if d.get("likely_wasteful_repeat")
    ]
    plan_compliance = solution_v.get("plan_compliance")

    return {
        "model_name": model_name,
        "debug_mode": code_result.get("debug_mode", False),
        "starter_valid": starter_v.get("valid"),
        "solution_valid": solution_v.get("valid"),
        "starter_repair_attempts": starter_v.get("repair_attempts", 0),
        "solution_repair_attempts": solution_v.get("repair_attempts", 0),
        "undefined_names": starter_v.get("undefined_names", []) + solution_v.get("undefined_names", []),
        "used_before_defined": [
            u["name"] for u in (starter_v.get("used_before_defined", []) + solution_v.get("used_before_defined", []))
        ],
        "wasteful_duplicate_defs": dup_names,
        "plan_compliance_valid": plan_compliance.get("valid") if plan_compliance else None,
        "plan_missing_produces": [m["name"] for m in plan_compliance.get("missing_produces", [])] if plan_compliance else [],
        "plan_unplanned_definitions": plan_compliance.get("unplanned_definitions", []) if plan_compliance else [],
        "kept_per_topic_cells": "cells" in code_result,  # True only if NOTHING needed repair
        "error": code_result.get("_error"),
    }


LAB_CACHE_FILE = "all_labs_cache.json"

if __name__ == "__main__":
    data = get_or_build_pipeline_output()
    scored_similar = [tuple(item) for item in data["scored_similar"]]
    teaching_plan, course = data["teaching_plan"], data["course"]

    if os.path.exists(LAB_CACHE_FILE):
        print(f"[lab cache] loading from {LAB_CACHE_FILE} — delete this file to force regeneration")
        with open(LAB_CACHE_FILE, "r", encoding="utf-8") as f:
            endpoint_like = json.load(f)
    else:
        modules_output = []
        for tp_module, course_module in zip(teaching_plan.get("modules", []), course.get("modules", [])):
            lessons_output = []
            for lesson in course_module.get("lessons", []):
                print(f"[lab] generating: {tp_module.get('title','')} / {lesson.get('lesson_title','')}")
                lab = generate_lab_exercise(
                    lesson=lesson, module=tp_module,
                    papers_with_analysis=data["papers_with_analysis"],
                    similar_projects_scored=scored_similar,
                    generate_code=True, code_model=CODE_MODEL,
                )
                lessons_output.append({"lab": lab, "notebook_files": None})
            modules_output.append({"module_title": tp_module.get("title", ""), "lessons": lessons_output})

        endpoint_like = {
            "idea": IDEA,
            "modules": modules_output,
            "papers_used": [p.get("title") for p in data.get("papers_with_analysis", [])],
        }
        with open(LAB_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(endpoint_like, f, indent=2)
        print(f"[lab cache] saved to {LAB_CACHE_FILE}")