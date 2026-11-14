#!/usr/bin/env python3
"""Conservatively refresh curated BEU Important Topics from structured PYQs.

This tool does NOT invent topic names. It preserves the curated topic catalogue and
only adds an appearance year when the complete normalized topic name is found
inside a question's visible text. Review the audit report before publishing.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def normalize(value: str) -> str:
    value = (value or "").lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def exam_year(paper: dict[str, Any]) -> int | None:
    title = str(paper.get("examTitle", ""))
    match = re.search(r"\b(20\d{2})\b", title)
    if match:
        return int(match.group(1))
    html = str(paper.get("html", ""))
    match = re.search(r"\b(20\d{2})\b", html[:2500])
    return int(match.group(1)) if match else None


def question_texts(html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    nodes = soup.select(".sub-question")
    if nodes:
        return [re.sub(r"\s+", " ", node.get_text(" ", strip=True)) for node in nodes]
    # Fallback for older records without .sub-question wrappers.
    return [re.sub(r"\s+", " ", node.get_text(" ", strip=True))
            for node in soup.select(".question-block")]


def semester_numbers(group: str) -> set[int]:
    found = re.findall(r"\d+", str(group))
    return {int(x) for x in found}


def subject_matches(curated: dict[str, Any], source: dict[str, Any]) -> bool:
    if normalize(curated.get("subjectName", "")) != normalize(source.get("name", "")):
        return False
    sems = semester_numbers(source.get("semesterGroup", ""))
    if sems and int(curated.get("semester", -1)) not in sems:
        return False
    source_branch = normalize(source.get("branch", ""))
    curated_branch = normalize(curated.get("branch", ""))
    if source_branch and source_branch not in {"all", "all branches"}:
        if curated_branch not in {source_branch, "all", "all branches"}:
            return False
    return True


def refresh(pyq: dict[str, Any], curated: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    output = deepcopy(curated)
    audit = {
        "sourceSubjects": 0,
        "sourcePapers": 0,
        "questionEntries": 0,
        "matchedCuratedSubjects": 0,
        "matchedTopics": 0,
        "newYearsAdded": 0,
        "unmatchedSubjects": [],
        "topicMatches": [],
        "unmatchedQuestionSamples": [],
    }

    source_subjects = []
    for collection in ("qp1", "qp2", "qp3", "qp4"):
        source_subjects.extend(pyq.get(collection, []) or [])
    audit["sourceSubjects"] = len(source_subjects)

    for source in source_subjects:
        candidates = [s for s in output.get("subjects", []) if subject_matches(s, source)]
        if not candidates:
            audit["unmatchedSubjects"].append({
                "name": source.get("name", ""),
                "semesterGroup": source.get("semesterGroup", ""),
                "code": source.get("code", ""),
            })
            continue
        # Update only a unique match. Duplicate/ambiguous subject mappings are audited.
        if len(candidates) != 1:
            audit["unmatchedSubjects"].append({
                "name": source.get("name", ""),
                "semesterGroup": source.get("semesterGroup", ""),
                "code": source.get("code", ""),
                "reason": "ambiguous curated subject match",
            })
            continue

        curated_subject = candidates[0]
        audit["matchedCuratedSubjects"] += 1
        topic_years: dict[str, set[int]] = defaultdict(set)
        topic_questions: dict[str, list[str]] = defaultdict(list)
        topics = curated_subject.get("topics", [])

        for paper in source.get("papers", []) or []:
            audit["sourcePapers"] += 1
            year = exam_year(paper)
            texts = question_texts(paper.get("html", ""))
            audit["questionEntries"] += len(texts)
            if year is None:
                continue
            normalized_questions = [(normalize(t), t) for t in texts]
            for topic in topics:
                topic_key = normalize(topic.get("topicName", ""))
                if not topic_key or len(topic_key.split()) < 1:
                    continue
                hits = [original for norm, original in normalized_questions
                        if re.search(r"(?<![a-z0-9])" + re.escape(topic_key) + r"(?![a-z0-9])", norm)]
                if hits:
                    topic_years[topic.get("topicId", "")].add(year)
                    topic_questions[topic.get("topicId", "")].extend(hits)

        for topic in topics:
            tid = topic.get("topicId", "")
            years = topic_years.get(tid, set())
            if not years:
                continue
            audit["matchedTopics"] += 1
            old_years = set(topic.get("yearsAppeared", []) or [])
            merged = sorted(old_years | years)
            added = len(set(merged) - old_years)
            audit["newYearsAdded"] += added
            topic["yearsAppeared"] = merged
            topic["appearanceCount"] = len(merged)
            audit["topicMatches"].append({
                "subject": curated_subject.get("subjectName", ""),
                "topicId": tid,
                "topicName": topic.get("topicName", ""),
                "matchedYears": sorted(years),
                "newYearsAdded": added,
                "matchedQuestionSamples": topic_questions[tid][:3],
            })

    output["lastUpdated"] = __import__("datetime").date.today().isoformat()
    # Preserve schemaVersion/dataVersion; the caller chooses when to bump dataVersion.
    return output, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyq", default="BEUConnect_PYQ_structured.json")
    parser.add_argument("--topics", default="BEUConnect_Important_Topics.json")
    parser.add_argument("--output", default="BEUConnect_Important_Topics_updated.json")
    parser.add_argument("--audit", default="vvi_generation_audit.json")
    args = parser.parse_args()

    pyq = json.loads(Path(args.pyq).read_text(encoding="utf-8"))
    curated = json.loads(Path(args.topics).read_text(encoding="utf-8"))
    updated, audit = refresh(pyq, curated)

    Path(args.output).write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in (
        "sourceSubjects", "sourcePapers", "questionEntries",
        "matchedCuratedSubjects", "matchedTopics", "newYearsAdded"
    )}, indent=2))
    print(f"Updated topics: {args.output}")
    print(f"Audit report: {args.audit}")


if __name__ == "__main__":
    main()
