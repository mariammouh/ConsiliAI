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

from agents.tools import (
    compare_lab_code_models,   # from lab_generator.py, once merged into tools.py
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
MODELS = ("groq", "gemini", "qwen2.5-coder:7b", "deepseek-coder-v2:16b")


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


if __name__ == "__main__":
    data = get_or_build_pipeline_output()
    scored_similar = [tuple(item) for item in data["scored_similar"]]

    module, lesson = find_module_and_lesson(
        data["teaching_plan"], data["course"], MODULE_TITLE_CONTAINS
    )
    print(f"\nTesting on module: {module.get('title')}")
    print(f"Lesson: {lesson.get('lesson_title')}\n")

    comparison = compare_lab_code_models(
        lesson=lesson,
        module=module,
        papers_with_analysis=data["papers_with_analysis"],
        similar_projects_scored=scored_similar,
        models=MODELS,
    )

    if comparison.get("_error"):
        print(f"Could not run comparison: {comparison['_error']}")
        raise SystemExit(1)

    summaries = []
    print("--- RESULTS (post-decomposition, post-repair, post-plan-compliance) ---")
    for model_name, code_result in comparison["results"].items():
        s = summarize(model_name, code_result)
        summaries.append(s)
        print(
            f"{model_name}: starter_valid={s['starter_valid']} | solution_valid={s['solution_valid']} | "
            f"debug_mode={s['debug_mode']} | repairs={s['starter_repair_attempts'] + s['solution_repair_attempts']} | "
            f"plan_ok={s['plan_compliance_valid']} | wasteful_dupes={len(s['wasteful_duplicate_defs'])}"
        )

    with open("model_comparison_results_v2.json", "w", encoding="utf-8") as f:
        json.dump(
            {"scaffold": comparison.get("scaffold"), "summary": summaries, "full_results": comparison["results"]},
            f, indent=2,
        )
    print("\nFull results (including all generated code) saved to model_comparison_results_v2.json")