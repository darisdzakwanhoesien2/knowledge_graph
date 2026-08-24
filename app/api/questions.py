from fastapi import APIRouter, Depends, HTTPException
from ..models.domain import Question, EssayPrompt
from core.packages import load_package, validate_package, add_mcq, add_essay
from core.grading import grade_mcq, grade_essay, compute_scores


router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/{question_id}", response_model=Question)
async def get_question(question_id: str) -> Question:
    """Get a question by ID."""
    # Search all packages for the question
    from core.packages import list_packages
    for pkg_info in list_packages():
        pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
        for mcq in pkg.get("mcqs", []):
            if mcq.get("id") == question_id:
                return mcq
        for essay in pkg.get("essay", []):
            if essay.get("id") == question_id:
                return essay
    raise HTTPException(status_code=404, detail=f"Question {question_id} not found")


@router.post("", response_model=Question)
async def create_question(question: Question) -> Question:
    """Create a new question."""
    # Find the active draft package
    from core.packages import list_packages
    for pkg_info in list_packages():
        pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
        if pkg.get("status") == "draft":
            # Determine question type
            if question.options is not None:
                qid = add_mcq(
                    pkg,
                    question.prompt,
                    {k: v.text for k, v in question.options.items()},
                    question.correct_answer_key or "A",
                    question.difficulty or "medium",
                    question.learning_objective,
                    question.slide_reference,
                )
            else:
                qid = add_essay(
                    pkg,
                    question.prompt,
                    question.keywords,
                    question.rubric_criteria,
                    question.total_points if hasattr(question, 'total_points') else 0,
                    question.grading_notes if hasattr(question, 'grading_notes') else "",
                    question.difficulty or "medium",
                    question.learning_objective,
                    question.slide_reference,
                )
            save_package(pkg)
            return question
    raise HTTPException(status_code=404, detail="No draft package found to add question")


@router.post("/{question_id}", response_model=Question)
async def update_question(question_id: str, question: Question) -> Question:
    """Update a question."""
    # Search all packages for the question and update it
    from core.packages import list_packages, save_package
    for pkg_info in list_packages():
        pkg = load_package(pkg_info["subject"], pkg_info["package_id"])
        updated = False
        for idx, mcq in enumerate(pkg.get("mcqs", [])):
            if mcq.get("id") == question_id:
                if question.options is not None:
                    pkg["mcqs"][idx] = {
                        "id": question_id,
                        "kind": "mcq",
                        "question": question.prompt,
                        "options": {k: v.text for k, v in question.options.items()},
                        "correct_option": question.correct_answer_key or "A",
                        "difficulty": question.difficulty or "medium",
                        "learning_objective": question.learning_objective or "",
                        "slide_refs": question.slide_reference or [],
                    }
                updated = True
                break
        if not updated:
            for idx, essay in enumerate(pkg.get("essay", [])):
                if essay.get("id") == question_id:
                    pkg["essay"][idx] = {
                        "id": question_id,
                        "kind": "essay",
                        "prompt": question.prompt,
                        "expected_keywords": question.keywords,
                        "rubric": {
                            "total_points": question.total_points if hasattr(question, 'total_points') else 0,
                            "grading_notes": question.grading_notes if hasattr(question, 'grading_notes') else "",
                            "criteria": question.rubric_criteria or [],
                        },
                        "difficulty": question.difficulty or "medium",
                        "learning_objective": question.learning_objective or "",
                        "slide_refs": question.slide_reference or [],
                    }
                    updated = True
                    break
        if updated:
            save_package(pkg)
            return question
    raise HTTPException(status_code=404, detail=f"Question {question_id} not found")