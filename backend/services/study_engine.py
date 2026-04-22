import os
import re
from typing import List, Dict, Any
from backend.models.schema import Study, StudyFile, StudySummary
from backend.routers.analyze import analyze_cached
from backend.routers.datasets import register_local_file
from tools.auto_analyzer.analyzer import compare_results

def discover_study(directory: str, study_name: str = "Auto Study") -> Study:
    """Scan directory for H-Walker CSVs and group into a Study."""
    files = []
    for f in os.listdir(directory):
        if f.endswith(".csv"):
            path = os.path.join(directory, f)
            # Register with datasets router to get a ds_id
            ds_id = register_local_file(path)
            
            # Simple metadata extraction from filename (Subject_Condition_Trial)
            # Example: S01_Pre_T1.csv
            subject_id = "unknown"
            condition = "baseline"
            parts = f.split("_")
            if len(parts) >= 2:
                subject_id = parts[0]
                condition = parts[1]
            
            files.append(StudyFile(
                id=ds_id,
                name=f,
                path=path,
                subject_id=subject_id,
                condition=condition
            ))
    
    return Study(id=study_name.lower().replace(" ", "_"), name=study_name, files=files)

def run_study_analysis(study: Study) -> StudySummary:
    """Run analysis on all files in study and generate summary."""
    results = []
    file_summaries = []
    
    for sf in study.files:
        res_obj, payload = analyze_cached(sf.id)
        if res_obj:
            results.append(res_obj)
            file_summaries.append(payload)
    
    comparison = compare_results(results) if len(results) >= 2 else {}
    
    report_md = _generate_markdown_report(study.name, file_summaries, comparison)
    report_latex = _generate_latex_report(study.name, file_summaries)
    
    return StudySummary(
        study_id=study.id,
        study_name=study.name,
        file_summaries=file_summaries,
        comparison=comparison,
        report_md=report_md,
        report_latex=report_latex
    )

def _generate_markdown_report(name: str, summaries: List[dict], comparison: dict) -> str:
    md = f"# H-Walker Research Report: {name}\n\n"
    
    md += "## 1. Dataset Overview\n"
    md += "| Filename | Duration (s) | L Strides | R Strides | Stride Time (s) |\n"
    md += "| :--- | :--- | :--- | :--- | :--- |\n"
    for s in summaries:
        if s.get("mode") == "hwalker":
            md += f"| {s['filename']} | {s['duration_s']} | {s['left']['n_strides']} | {s['right']['n_strides']} | {s['left']['stride_time_mean']:.3f} |\n"
    
    if comparison:
        md += "\n## 2. Condition Comparison\n"
        md += "| Metric | Mean Diff | Change (%) |\n"
        md += "| :--- | :--- | :--- |\n"
        # Simple comparison logic (if exactly 2 files, e.g. Pre/Post)
        if len(summaries) == 2:
            s1, s2 = summaries[0], summaries[1]
            metrics = [
                ("Stride Time (L)", "stride_time_mean", "left"),
                ("Stride Length (L)", "stride_length_mean", "left"),
                ("Force RMSE (L)", "rmse", "left", "force_tracking"),
                ("Foot Pitch ROM (L)", "rom", "left", "joint"),
            ]
            for label, key, side, *nest in metrics:
                try:
                    v1 = s1[side]
                    v2 = s2[side]
                    for n in nest:
                        v1 = v1[n]
                        v2 = v2[n]
                    v1 = v1[key]
                    v2 = v2[key]
                    diff = v2 - v1
                    pct = (diff / v1 * 100) if v1 != 0 else 0
                    md += f"| {label} | {diff:.3f} | {pct:+.1f}% |\n"
                except (KeyError, ZeroDivisionError):
                    continue

    md += "\n## 3. Detailed Statistics\n"
    for s in summaries:
        if s.get("mode") == "hwalker":
            md += f"### {s['filename']}\n"
            md += f"- **Symmetry (Time/Force)**: {s['symmetry']['stride_time']}% / {s['symmetry']['force']}%\n"
            md += f"- **Foot Pitch ROM (L/R)**: {s['left']['joint']['rom']}° / {s['right']['joint']['rom']}°\n"
            md += f"- **Force Bias (L/R)**: {s['left']['force_tracking']['bias']:.2f}N / {s['right']['force_tracking']['bias']:.2f}N\n"
            md += "\n"
            
    return md

def _generate_latex_report(name: str, summaries: List[dict]) -> str:
    """Generate a journal-ready LaTeX table for the study."""
    tex = [
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Biomechanical metrics summary for " + name + "}",
        "\\begin{tabular}{l c c c c c}",
        "\\hline",
        "Dataset & Stride T (s) & Pitch ROM L ($^\\circ$) & Pitch ROM R ($^\\circ$) & Bias L (N) & Bias R (N) \\\\",
        "\\hline"
    ]
    
    for s in summaries:
        if s.get("mode") == "hwalker":
            fname = s['filename'].replace("_", "\\_")
            st = f"{s['left']['stride_time_mean']:.3f}"
            rom_l = f"{s['left']['joint']['rom']:.1f}"
            rom_r = f"{s['right']['joint']['rom']:.1f}"
            bias_l = f"{s['left']['force_tracking']['bias']:.2f}"
            bias_r = f"{s['right']['force_tracking']['bias']:.2f}"
            tex.append(f"{fname} & {st} & {rom_l} & {rom_r} & {bias_l} & {bias_r} \\\\")
            
    tex.extend([
        "\\hline",
        "\\end{tabular}",
        "\\end{table}"
    ])
    
    return "\n".join(tex)
