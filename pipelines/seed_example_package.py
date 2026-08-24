"""Create and publish a small example package so the assessment flow is testable.

Usage: python3 pipelines/seed_example_package.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import packages as P  # noqa: E402


def main():
    subject, package_id = "introduction_to_optimization", "optimization_basics_quiz"
    if P.package_path(subject, package_id).exists():
        print(f"Example package already exists: {subject}/{package_id}")
        return

    pkg = P.new_package(
        subject=subject,
        title="Optimization Basics Quiz",
        level="Undergraduate",
        description="Seed example covering core definitions from the Introduction to Optimization notes.",
    )
    P.add_mcq(
        pkg,
        question="Which statement best describes an objective function f in continuous optimization?",
        options={
            "A": "A scalar function to minimize or maximize over the feasible set",
            "B": "A function that must always be convex",
            "C": "A discrete lookup table of feasible points",
            "D": "Any matrix with full rank",
        },
        correct_option="A",
        difficulty="easy",
        learning_objective="Define the components of an optimization problem",
        slide_refs=["01_data.json"],
        node_links=["Objective Function ($f$)", "Continuous Optimization"],
    )
    P.add_mcq(
        pkg,
        question="What does the first-order necessary condition (FONC) require at a local minimizer x*?",
        options={
            "A": "The Hessian must be positive definite",
            "B": "The gradient of the objective vanishes along feasible directions",
            "C": "The point must be a global minimum",
            "D": "All constraints must be inactive",
        },
        correct_option="B",
        difficulty="medium",
        learning_objective="Explain optimality conditions",
        node_links=["First-Order Necessary Condition (FONC)", "Local Minimizer ($x^*$)"],
    )
    P.add_essay(
        pkg,
        prompt="Explain what convexity of an optimization problem implies about local and global minima.",
        expected_keywords=["convex", "local minimum", "global minimum"],
        criteria=[
            {"keyword": "convex", "weight": 2, "description": "Mentions convexity"},
            {"keyword": "local", "weight": 1, "description": "Refers to local minima"},
            {"keyword": "global", "weight": 2, "description": "Connects local to global optimality"},
        ],
        total_points=5,
        grading_notes="Assistive keyword grading; review evidence before finalizing.",
        difficulty="medium",
        learning_objective="Relate convexity to optimality guarantees",
        node_links=["Convexity"],
    )

    P.save_package(pkg)
    snapshot = P.publish_package(subject, package_id)
    issues = P.validate_package(P.load_package(subject, package_id))
    print(f"Seeded {snapshot['package_key']} v{snapshot['version']} "
          f"({len(snapshot['mcqs'])} MCQs, {len(snapshot['essay'])} essays), "
          f"{sum(1 for i in issues if i['severity'] == 'error')} errors")


if __name__ == "__main__":
    main()
