"""Quality report across graph and question packages (FR-13).

Detects: missing definitions, edges with unknown endpoints, duplicate edges,
malformed MCQ options/answers, invalid rubric weights, broken node_links,
and package_id / directory mismatches.

Usage: python3 pipelines/check_quality.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import packages as P  # noqa: E402
from core.learning_links import find_node  # noqa: E402
from core.store import BASE_DIR, REPORTS_DIR, load_json, now_utc, write_json  # noqa: E402

GRAPH_FILE = BASE_DIR / "data" / "graphs" / "merged_graph.json"


def check_graph(graph):
    issues = []
    nodes = graph.get("nodes", {})
    seen_edges = set()
    for name, props in nodes.items():
        if not isinstance(props, dict):
            issues.append({"severity": "error", "location": f"node:{name}",
                           "message": "node payload is not an object"})
            continue
        if not (props.get("definition") or props.get("description")):
            issues.append({"severity": "warning", "location": f"node:{name}",
                           "message": "missing definition and description"})
        if not props.get("metadata"):
            issues.append({"severity": "warning", "location": f"node:{name}",
                           "message": "missing provenance metadata"})

    for idx, edge in enumerate(graph.get("edges", [])):
        if not isinstance(edge, dict):
            issues.append({"severity": "error", "location": f"edge[{idx}]",
                           "message": "edge record is not an object"})
            continue
        src, dst = edge.get("source"), edge.get("target")
        if src not in nodes:
            issues.append({"severity": "error", "location": f"edge[{idx}]",
                           "message": f"source '{src}' is not a known node"})
        if dst not in nodes:
            issues.append({"severity": "error", "location": f"edge[{idx}]",
                           "message": f"target '{dst}' is not a known node"})
        key = json.dumps([src, dst, edge.get("type", "")], sort_keys=True)
        if key in seen_edges:
            issues.append({"severity": "warning", "location": f"edge[{idx}]",
                           "message": f"duplicate edge {src} -{edge.get('type')}-> {dst}"})
        seen_edges.add(key)
    return issues


def check_packages():
    issues = []
    for entry in P.list_packages():
        pkg = load_json(entry["path"])
        if not isinstance(pkg, dict):
            issues.append({"severity": "error", "location": str(entry["path"]),
                           "message": "package.json is not an object"})
            continue
        issues.extend(P.validate_package(pkg))

        if entry["package_id"] != pkg.get("package_id"):
            issues.append({"severity": "error",
                           "location": f"{entry['subject']}/{entry['package_id']}",
                           "message": f"directory id '{entry['package_id']}' differs from "
                                      f"payload package_id '{pkg.get('package_id')}'"})
        questions = list(pkg.get("mcqs", [])) + list(pkg.get("essay", []))
        if not questions:
            issues.append({"severity": "warning",
                           "location": f"{entry['subject']}/{entry['package_id']}",
                           "message": "package has no questions"})
        for q in questions:
            for link in q.get("node_links", []):
                if find_node(link) is None:
                    issues.append({"severity": "warning",
                                   "location": f"{entry['subject']}/{entry['package_id']}:{q.get('id')}",
                                   "message": f"node_link '{link}' not found in graph"})
    return issues


def main():
    report = {"built_at": now_utc(), "issues": []}
    graph = load_json(GRAPH_FILE, {})
    if graph:
        report["issues"].extend(check_graph(graph))
    report["issues"].extend(check_packages())

    counts = {"error": 0, "warning": 0}
    for issue in report["issues"]:
        counts[issue["severity"]] = counts.get(issue["severity"], 0) + 1
    report["counts"] = counts

    write_json(REPORTS_DIR / "quality_report.json", report)

    print(f"Quality check: {counts.get('error', 0)} errors, {counts.get('warning', 0)} warnings")
    for issue in report["issues"][:50]:
        print(f"  [{issue['severity']}] {issue['location']}: {issue['message']}")
    if len(report["issues"]) > 50:
        print(f"  ... and {len(report['issues']) - 50} more (see data/reports/quality_report.json)")
    print(f"Report saved to {REPORTS_DIR / 'quality_report.json'}")


if __name__ == "__main__":
    main()
