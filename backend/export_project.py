import os
import json
import re
import tempfile
import zipfile
from typing import Dict, Any, Optional

from ingestion.pdf_processor import UPLOAD_DIR
from ingestion.chroma_client import collection


def _slug(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(text or "")).strip("_").lower()
    if len(slug) <= max_len:
        return slug or "project"
    truncated = slug[:max_len]
    return truncated.rsplit("_", 1)[0] if "_" in truncated else truncated


def _generate_technical_plan_markdown(plan: Any) -> str:
    if isinstance(plan, str):
        return plan
    if not isinstance(plan, dict):
        return str(plan)

    md = ["# Technical Project Plan\n"]
    if plan.get("project_title"):
        md.append(f"## Title: {plan['project_title']}\n")
    if plan.get("overview"):
        md.append(f"### Overview\n{plan['overview']}\n")
    if plan.get("recommended_stack"):
        md.append("### Recommended Technology Stack")
        stack = plan["recommended_stack"]
        if isinstance(stack, dict):
            for k, v in stack.items():
                md.append(f"- **{k}**: {v}")
        elif isinstance(stack, list):
            for item in stack:
                md.append(f"- {item}")
        else:
            md.append(str(stack))
        md.append("")
    if plan.get("phases") or plan.get("milestones"):
        items = plan.get("phases") or plan.get("milestones")
        md.append("### Project Phases & Milestones")
        if isinstance(items, list):
            for i, p in enumerate(items, 1):
                if isinstance(p, dict):
                    title = p.get("title") or p.get("name") or f"Phase {i}"
                    desc = p.get("description") or p.get("deliverables") or ""
                    md.append(f"#### {i}. {title}\n{desc}\n")
                else:
                    md.append(f"- {p}")
        md.append("")
    if plan.get("risk_mitigation"):
        md.append(f"### Risk Mitigation\n{plan['risk_mitigation']}\n")
    return "\n".join(md)


def _generate_teaching_plan_markdown(plan: Any) -> str:
    if isinstance(plan, str):
        return plan
    if not isinstance(plan, dict):
        return str(plan)

    md = ["# Teaching & Pedagogical Plan\n"]
    if plan.get("course_title"):
        md.append(f"## {plan['course_title']}\n")
    if plan.get("pedagogical_approach"):
        md.append(f"### Pedagogical Approach\n{plan['pedagogical_approach']}\n")
    if plan.get("target_audience"):
        md.append(f"**Target Audience:** {plan['target_audience']}\n")

    modules = plan.get("modules") or []
    if isinstance(modules, list) and modules:
        md.append("### Curriculum Modules")
        for i, mod in enumerate(modules, 1):
            if isinstance(mod, dict):
                m_title = mod.get("title") or mod.get("module_title") or f"Module {i}"
                md.append(f"#### Module {i}: {m_title}")
                if mod.get("problem_addressed"):
                    md.append(f"- **Problem Addressed:** {mod['problem_addressed']}")
                if mod.get("solution_approach"):
                    md.append(f"- **Solution Approach:** {mod['solution_approach']}")
                lessons = mod.get("lessons") or []
                if lessons:
                    md.append("- **Lessons:**")
                    for les in lessons:
                        if isinstance(les, dict):
                            md.append(f"  - {les.get('lesson_title', les.get('title', 'Lesson'))}")
                        else:
                            md.append(f"  - {les}")
                md.append("")
    return "\n".join(md)


def _generate_course_markdown(course: Any) -> str:
    if isinstance(course, str):
        return course
    if not isinstance(course, dict):
        return str(course)

    md = [f"# {course.get('course_title', 'Course Syllabus')}\n"]
    if course.get("overview"):
        md.append(f"### Course Overview\n{course['overview']}\n")
    if course.get("target_audience"):
        md.append(f"**Target Audience:** {course['target_audience']}\n")

    modules = course.get("modules") or []
    for mi, mod in enumerate(modules, 1):
        if not isinstance(mod, dict):
            continue
        m_title = mod.get("module_title") or mod.get("title") or f"Module {mi}"
        md.append(f"## Module {mi}: {m_title}\n")
        if mod.get("module_objective"):
            md.append(f"*Objective:* {mod['module_objective']}\n")
        lessons = mod.get("lessons") or []
        for li, les in enumerate(lessons, 1):
            if not isinstance(les, dict):
                continue
            l_title = les.get("lesson_title") or les.get("title") or f"Lesson {li}"
            md.append(f"### Lesson {mi}.{li}: {l_title}")
            if les.get("learning_outcomes"):
                md.append(f"**Learning Outcomes:** {les['learning_outcomes']}\n")
            sections = les.get("sections") or []
            for sec in sections:
                if isinstance(sec, dict):
                    md.append(f"#### {sec.get('topic', 'Section')}")
                    if sec.get("content"):
                        md.append(f"{sec['content']}\n")
                    if sec.get("slide_bullet_points"):
                        for pt in sec["slide_bullet_points"]:
                            md.append(f"- {pt}")
                        md.append("")
    return "\n".join(md)


def _generate_labs_markdown(lab_exercises: Any) -> str:
    if not lab_exercises:
        return ""
    md = ["# Hands-On Lab Exercises & Practice Guide\n"]
    modules = lab_exercises.get("modules") if isinstance(lab_exercises, dict) else lab_exercises
    if not isinstance(modules, list):
        return json.dumps(lab_exercises, indent=2)

    for mi, mod in enumerate(modules, 1):
        if not isinstance(mod, dict):
            continue
        m_title = mod.get("module_title") or f"Module {mi}"
        md.append(f"## Module {mi}: {m_title}\n")
        lessons = mod.get("lessons") or []
        for li, les in enumerate(lessons, 1):
            if not isinstance(les, dict):
                continue
            lab = les.get("lab") if isinstance(les.get("lab"), dict) else les
            title = lab.get("exercise_title") or lab.get("title") or f"Exercise {li}"
            md.append(f"### Exercise {mi}.{li}: {title}")
            if lab.get("learning_objective"):
                md.append(f"**Objective:** {lab['learning_objective']}\n")
            if lab.get("difficulty"):
                md.append(f"**Difficulty:** {lab['difficulty']}")
            if lab.get("format"):
                md.append(f"**Format:** {lab['format']}")
            if lab.get("instructions"):
                md.append(f"\n#### Instructions\n{lab['instructions']}\n")
            if lab.get("hints"):
                md.append("#### Hints")
                for h in lab["hints"]:
                    md.append(f"- {h}")
                md.append("")
            if lab.get("based_on_repo"):
                repo = lab["based_on_repo"]
                if isinstance(repo, dict):
                    md.append(f"**Reference Repo:** [{repo.get('name', 'Repo')}]({repo.get('url', '#')})\n")
    return "\n".join(md)


def _generate_gaps_markdown(gaps: Any) -> str:
    if isinstance(gaps, str):
        return gaps
    if not isinstance(gaps, list):
        return json.dumps(gaps, indent=2)

    md = ["# Research Gaps & Novel Opportunities\n"]
    for i, g in enumerate(gaps, 1):
        if isinstance(g, dict):
            title = g.get("gap_title") or g.get("title") or f"Gap {i}"
            md.append(f"## {i}. {title}")
            if g.get("description"):
                md.append(f"\n{g['description']}\n")
            if g.get("why_it_matters"):
                md.append(f"**Why It Matters:** {g['why_it_matters']}\n")
            if g.get("suggested_direction"):
                md.append(f"**Suggested Direction:** {g['suggested_direction']}\n")
            if g.get("papers_involved"):
                md.append("**Supporting Papers:**")
                for p in g["papers_involved"]:
                    md.append(f"- {p}")
                md.append("")
        else:
            md.append(f"- {g}")
    return "\n".join(md)


def _generate_experiments_markdown(experiments_obj: Any) -> str:
    if isinstance(experiments_obj, str):
        return experiments_obj
    exp_list = experiments_obj.get("experiments") if isinstance(experiments_obj, dict) else experiments_obj
    if not isinstance(exp_list, list):
        return json.dumps(experiments_obj, indent=2)

    md = ["# Empirical Experiment Protocols\n"]
    for i, exp in enumerate(exp_list, 1):
        if isinstance(exp, dict):
            title = exp.get("title") or exp.get("experiment_title") or f"Experiment {i}"
            md.append(f"## {i}. {title}")
            if exp.get("hypothesis"):
                md.append(f"**Hypothesis:** {exp['hypothesis']}\n")
            if exp.get("gap_addressed"):
                md.append(f"**Target Gap:** {exp['gap_addressed']}\n")
            if exp.get("baseline"):
                md.append(f"**Baseline:** {exp['baseline']}\n")
            if exp.get("evaluation_metrics"):
                md.append("**Evaluation Metrics:**")
                metrics = exp["evaluation_metrics"]
                if isinstance(metrics, list):
                    for m in metrics:
                        md.append(f"- {m}")
                else:
                    md.append(f"- {metrics}")
                md.append("")
            if exp.get("procedure") or exp.get("steps"):
                steps = exp.get("procedure") or exp.get("steps")
                md.append("#### Protocol Steps")
                if isinstance(steps, list):
                    for si, st in enumerate(steps, 1):
                        md.append(f"{si}. {st}")
                else:
                    md.append(str(steps))
                md.append("")
    return "\n".join(md)


def _generate_evaluations_markdown(evaluations: Any) -> str:
    if not isinstance(evaluations, list) or not evaluations:
        return ""
    md = ["# Experiment Benchmark Evaluations\n"]
    for i, ev in enumerate(evaluations, 1):
        if not isinstance(ev, dict):
            continue
        exp_title = ev.get("experiment_title") or f"Evaluation Run {i}"
        run_id = ev.get("run_id") or f"Run #{i}"
        score = ev.get("overall_score", "N/A")
        pass_rate = ev.get("pass_rate", "N/A")

        md.append(f"## {i}. {exp_title} — {run_id}")
        md.append(f"- **Overall Benchmark Score:** {score}/100")
        md.append(f"- **Success Rate:** {pass_rate}%")
        
        hyp = ev.get("hypothesis_check") or {}
        if isinstance(hyp, dict):
            md.append(f"- **Hypothesis Match:** {hyp.get('matches_expectation', 'unclear').upper()} — {hyp.get('explanation', '')}")

        comp_table = ev.get("comparison_table") or []
        if isinstance(comp_table, list) and comp_table:
            md.append("\n### Benchmark Comparison Table\n")
            md.append("| Metric | Model | Student Result | Literature Baseline | Delta | Direction | Source Paper |")
            md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for row in comp_table:
                if isinstance(row, dict):
                    m = row.get("metric", "")
                    mod = row.get("model", "")
                    s_val = row.get("student_reported", "N/A")
                    l_val = row.get("literature_reported", "N/A")
                    d = row.get("delta")
                    d_str = f"{d:+.4f}" if isinstance(d, (int, float)) else "N/A"
                    dir_str = row.get("delta_direction", "N/A")
                    src = row.get("source_paper", "Literature")
                    md.append(f"| {m} | {mod} | {s_val} | {l_val} | {d_str} | {dir_str} | {src} |")
            md.append("")

        strengths = ev.get("strengths") or []
        if strengths:
            md.append("### Strengths & Outperformed Benchmarks")
            for s in strengths:
                md.append(f"- {s}")
            md.append("")

        weaknesses = ev.get("weaknesses") or []
        if weaknesses:
            md.append("### Weaknesses & Divergences")
            for w in weaknesses:
                md.append(f"- {w}")
            md.append("")

        improvements = ev.get("areas_for_improvement") or []
        if improvements:
            md.append("### Actionable Areas for Improvement")
            for imp in improvements:
                md.append(f"- {imp}")
            md.append("")

        if ev.get("proposed_gap"):
            gap = ev["proposed_gap"]
            md.append("### Candidate New Research Gap Discovered")
            md.append(f"- **Description:** {gap.get('gap_description', '')}")
            md.append(f"- **Evidence:** {gap.get('supporting_evidence', '')}")
            md.append(f"- **Opportunity:** {gap.get('opportunity', '')}\n")
    return "\n".join(md)


def _generate_papers_markdown(papers: Any) -> str:
    if not isinstance(papers, list):
        return json.dumps(papers, indent=2)
    md = ["# Literature Review & Analyzed Papers\n"]
    for i, p in enumerate(papers, 1):
        if not isinstance(p, dict):
            continue
        md.append(f"## {i}. {p.get('title', 'Untitled Paper')}")
        if p.get("authors"):
            authors = ", ".join(p["authors"]) if isinstance(p["authors"], list) else str(p["authors"])
            md.append(f"*Authors:* {authors}")
        if p.get("url"):
            md.append(f"*URL:* [{p['url']}]({p['url']})")
        if p.get("pdf_url"):
            md.append(f"*PDF:* [{p['pdf_url']}]({p['pdf_url']})")
        if p.get("source"):
            md.append(f"*Source:* {p['source']}")
        if p.get("abstract"):
            md.append(f"\n### Abstract\n{p['abstract']}\n")
        analysis = p.get("analysis")
        if isinstance(analysis, dict) and analysis:
            md.append("### Key Section Findings")
            for sec_name, sec_val in analysis.items():
                if isinstance(sec_val, dict):
                    md.append(f"**{sec_name.capitalize()}:**")
                    for k, v in sec_val.items():
                        md.append(f"- *{k}*: {v}")
                elif isinstance(sec_val, str):
                    md.append(f"- **{sec_name}**: {sec_val}")
            md.append("")
    return "\n".join(md)


def _generate_similar_projects_markdown(projects: Any) -> str:
    if not isinstance(projects, list):
        return json.dumps(projects, indent=2)
    md = ["# Related Repositories & Implementations\n"]
    for i, item in enumerate(projects, 1):
        if isinstance(item, (tuple, list)) and len(item) == 2 and isinstance(item[1], dict):
            score, proj = item[0], item[1]
        elif isinstance(item, dict):
            proj = item
            score = proj.get("similarity_score", proj.get("score", 0.5))
        else:
            continue
        pct = round(score * 100, 1) if isinstance(score, (int, float)) and score <= 1.0 else score
        name = proj.get("name") or proj.get("title", f"Repo {i}")
        md.append(f"## {i}. {name} ({pct}% Match)")
        if proj.get("url"):
            md.append(f"*Repository Link:* [{proj['url']}]({proj['url']})")
        if proj.get("source"):
            md.append(f"*Ecosystem:* {proj['source']}")
        desc = proj.get("description") or proj.get("readme_snippet") or proj.get("readme")
        if desc:
            md.append(f"\n{desc}\n")
    return "\n".join(md)


def _generate_transcript_markdown(messages: list) -> str:
    md = ["# ConsiliAI Project Chat Transcript\n"]
    for m in messages:
        if isinstance(m, dict):
            role = m.get("role", "user").capitalize()
            content = m.get("content", "")
            md.append(f"### {role}\n{content}\n")
        else:
            m_type = getattr(m, "type", "human")
            role = "User" if m_type == "human" else "Assistant"
            content = getattr(m, "content", str(m))
            md.append(f"### {role}\n{content}\n")
    return "\n".join(md)


def build_project_zip_archive(conv: Any, state: Dict[str, Any], user_id: str) -> tuple[str, str]:
    """
    Dynamically collects all existing content generated for a project and builds
    a single organized ZIP archive.

    Folder structure:
      project_name/
      ├── courses/
      ├── labs/
      ├── exercises/
      ├── plans/
      ├── experiments/
      ├── notebooks/
      ├── documents/
      ├── code/
      └── other/

    Only directories and files that actually exist are included.
    Returns (zip_file_path, filename).
    """
    idea = state.get("idea") or getattr(conv, "title", None) or "ConsiliAI_Project"
    safe_name = _slug(idea, max_len=40)
    zip_filename = f"{safe_name}.zip"

    temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temp_zip_path = temp_zip.name
    temp_zip.close()

    with zipfile.ZipFile(temp_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Track if anything was written
        written_paths = set()

        # 1. COURSES
        # PPTX presentations
        course_paths = state.get("course_export_path")
        if course_paths and isinstance(course_paths, str):
            for path in [p.strip() for p in course_paths.split(",") if p.strip()]:
                if os.path.isfile(path):
                    arc = f"{safe_name}/courses/{os.path.basename(path)}"
                    zf.write(path, arcname=arc)
                    written_paths.add(arc)
        if state.get("course"):
            course_data = state["course"]
            syllabus_md = _generate_course_markdown(course_data)
            zf.writestr(f"{safe_name}/courses/course_syllabus.md", syllabus_md)
            zf.writestr(f"{safe_name}/courses/course_structure.json", json.dumps(course_data, indent=2))
            written_paths.add("course")

        # 2. NOTEBOOKS
        lab_exercises = state.get("lab_exercises")
        if lab_exercises:
            modules = lab_exercises.get("modules") if isinstance(lab_exercises, dict) else lab_exercises
            if isinstance(modules, list):
                for mod in modules:
                    if not isinstance(mod, dict):
                        continue
                    for les in mod.get("lessons", []):
                        if not isinstance(les, dict):
                            continue
                        notebooks = les.get("notebook_files") or {}
                        if isinstance(notebooks, dict):
                            for nb_type, nb_path in notebooks.items():
                                if nb_path and isinstance(nb_path, str) and os.path.isfile(nb_path):
                                    arc = f"{safe_name}/notebooks/{os.path.basename(nb_path)}"
                                    if arc not in written_paths:
                                        zf.write(nb_path, arcname=arc)
                                        written_paths.add(arc)

        # Also search consiliai_labs temp dir for notebooks if any
        labs_temp_dir = os.path.join(tempfile.gettempdir(), "consiliai_labs")
        if os.path.isdir(labs_temp_dir):
            for root, dirs, files in os.walk(labs_temp_dir):
                for f in files:
                    if f.endswith(".ipynb"):
                        fp = os.path.join(root, f)
                        arc = f"{safe_name}/notebooks/{f}"
                        if arc not in written_paths:
                            zf.write(fp, arcname=arc)
                            written_paths.add(arc)

        # 3. LABS
        if lab_exercises:
            labs_md = _generate_labs_markdown(lab_exercises)
            if labs_md.strip():
                zf.writestr(f"{safe_name}/labs/labs_guide.md", labs_md)
                zf.writestr(f"{safe_name}/labs/labs_data.json", json.dumps(lab_exercises, indent=2))
                written_paths.add("labs")

        # 4. EXERCISES
        practical_exercises = state.get("practical_exercises")
        if practical_exercises:
            zf.writestr(f"{safe_name}/exercises/practical_exercises.json", json.dumps(practical_exercises, indent=2))
            written_paths.add("exercises")

        # 5. PLANS
        if state.get("technical_plan"):
            plan = state["technical_plan"]
            zf.writestr(f"{safe_name}/plans/technical_plan.md", _generate_technical_plan_markdown(plan))
            zf.writestr(f"{safe_name}/plans/technical_plan.json", json.dumps(plan, indent=2))
            written_paths.add("technical_plan")

        if state.get("teaching_plan"):
            plan = state["teaching_plan"]
            zf.writestr(f"{safe_name}/plans/teaching_plan.md", _generate_teaching_plan_markdown(plan))
            zf.writestr(f"{safe_name}/plans/teaching_plan.json", json.dumps(plan, indent=2))
            written_paths.add("teaching_plan")

        if state.get("gaps"):
            gaps = state["gaps"]
            zf.writestr(f"{safe_name}/plans/research_gaps.md", _generate_gaps_markdown(gaps))
            zf.writestr(f"{safe_name}/plans/research_gaps.json", json.dumps(gaps, indent=2))
            written_paths.add("gaps")

        if state.get("novelty_analysis"):
            zf.writestr(f"{safe_name}/plans/novelty_analysis.md", str(state["novelty_analysis"]))
            written_paths.add("novelty")

        # 6. EXPERIMENTS
        if state.get("experiments"):
            experiments = state["experiments"]
            zf.writestr(f"{safe_name}/experiments/experiment_protocols.md", _generate_experiments_markdown(experiments))
            zf.writestr(f"{safe_name}/experiments/experiments.json", json.dumps(experiments, indent=2))
            written_paths.add("experiments")

        # 6.5. EVALUATIONS
        if state.get("evaluations"):
            evaluations = state["evaluations"]
            eval_md = _generate_evaluations_markdown(evaluations)
            if eval_md.strip():
                zf.writestr(f"{safe_name}/evaluations/benchmark_evaluations.md", eval_md)
                zf.writestr(f"{safe_name}/evaluations/evaluations.json", json.dumps(evaluations, indent=2))
                written_paths.add("evaluations")

        # 7. DOCUMENTS
        # User uploaded PDFs associated with this conversation or user
        conv_id = getattr(conv, "id", None)
        try:
            matched_sources = set()
            if conv_id:
                res = collection.get(where={"conversation_id": str(conv_id)})
                for m in (res.get("metadatas") or []):
                    if m and m.get("source"):
                        matched_sources.add(m["source"])
            if not matched_sources and user_id:
                res = collection.get(where={"user_id": str(user_id)})
                for m in (res.get("metadatas") or []):
                    if m and m.get("source"):
                        matched_sources.add(m["source"])

            for src in matched_sources:
                fpath = os.path.join(UPLOAD_DIR, src)
                if os.path.isfile(fpath):
                    arc = f"{safe_name}/documents/{src}"
                    zf.write(fpath, arcname=arc)
                    written_paths.add(arc)
        except Exception as e:
            print(f"[export] Could not attach user documents: {e}")

        if state.get("papers_with_analysis"):
            papers = state["papers_with_analysis"]
            zf.writestr(f"{safe_name}/documents/literature_summary.md", _generate_papers_markdown(papers))
            zf.writestr(f"{safe_name}/documents/literature_papers.json", json.dumps(papers, indent=2))
            written_paths.add("papers")

        projects = state.get("similar_projects_scored") or state.get("similar_projects_raw")
        if projects:
            zf.writestr(f"{safe_name}/documents/similar_projects.md", _generate_similar_projects_markdown(projects))
            zf.writestr(f"{safe_name}/documents/similar_projects.json", json.dumps(projects, indent=2))
            written_paths.add("projects")

        # 8. CODE
        if lab_exercises:
            modules = lab_exercises.get("modules") if isinstance(lab_exercises, dict) else lab_exercises
            if isinstance(modules, list):
                for mi, mod in enumerate(modules, 1):
                    if not isinstance(mod, dict):
                        continue
                    m_slug = _slug(mod.get("module_title") or f"mod_{mi}", max_len=20)
                    for li, les in enumerate(mod.get("lessons", []), 1):
                        if not isinstance(les, dict):
                            continue
                        lab = les.get("lab") if isinstance(les.get("lab"), dict) else les
                        l_slug = _slug(lab.get("exercise_title") or lab.get("title") or f"les_{li}", max_len=20)
                        sol = lab.get("code_solution") or lab.get("solution_code")
                        if sol and isinstance(sol, str) and sol.strip():
                            zf.writestr(f"{safe_name}/code/{m_slug}_{l_slug}_solution.py", sol)
                            written_paths.add("code")
                        starter = lab.get("starter_code")
                        if starter and isinstance(starter, str) and starter.strip():
                            zf.writestr(f"{safe_name}/code/{m_slug}_{l_slug}_starter.py", starter)
                            written_paths.add("code")

        # 9. OTHER
        messages = state.get("messages") or []
        if messages:
            formatted_messages = []
            for m in messages:
                m_type = getattr(m, "type", None)
                if m_type in {"human", "ai"}:
                    formatted_messages.append({
                        "role": "user" if m_type == "human" else "assistant",
                        "content": str(getattr(m, "content", ""))
                    })
                elif isinstance(m, dict) and m.get("role") and m.get("content"):
                    formatted_messages.append({
                        "role": m["role"],
                        "content": str(m["content"])
                    })
            if formatted_messages:
                zf.writestr(f"{safe_name}/other/chat_transcript.md", _generate_transcript_markdown(formatted_messages))
                zf.writestr(f"{safe_name}/other/chat_transcript.json", json.dumps(formatted_messages, indent=2))
                written_paths.add("other")

        # In the rare event that state was empty, provide a summary file
        if not written_paths:
            summary = (
                f"# Project: {getattr(conv, 'title', 'Untitled')}\n\n"
                f"Created at: {getattr(conv, 'created_at', 'N/A')}\n"
                "No generated deliverables exist for this project yet."
            )
            zf.writestr(f"{safe_name}/project_summary.md", summary)

    return temp_zip_path, zip_filename
