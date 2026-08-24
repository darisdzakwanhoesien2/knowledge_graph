"""Parse pasted question blocks into MCQ records (curator authoring helper).

Accepted shape per question:

    1. What does X mean?
    A) First option
    B) Second option
    Answer: B
    Difficulty: medium
    Objective: Explain X

Blocks may be separated by blank lines; numbering ("12.") is optional.
"""

import re

from core.store import new_id

OPTION_RE = re.compile(r"^\s*\(?([A-Ea-e])[\)\.\:]\s+(?P<text>.+)$")
NUMBERING_RE = re.compile(r"^\s*\d+\s*[\.\)]\s*")
ANSWER_RE = re.compile(r"^\s*(?:answer|correct(?:\s+answer)?|ans)\s*[:\-]\s*\(?([A-Ea-e])\)?", re.I)
DIFFICULTY_RE = re.compile(r"^\s*difficulty\s*[:\-]\s*(.+)$", re.I)
OBJECTIVE_RE = re.compile(r"^\s*(?:objective|learning\s+objective)\s*[:\-]\s*(.+)$", re.I)
SLIDE_RE = re.compile(r"^\s*(?:slide|slides|source)\s*[:\-]\s*(.+)$", re.I)


def parse_mcq_block(raw_text: str):
    """Return (questions, errors). Each question mirrors core.packages.add_mcq output."""
    questions, errors = [], []
    for block_idx, block in enumerate(_split_blocks(raw_text), start=1):
        q = _parse_single(block)
        if isinstance(q, str):
            errors.append(f"Block {block_idx}: {q}")
        else:
            questions.append(q)
    return questions, errors


def _split_blocks(raw_text: str):
    lines = (raw_text or "").replace("\r\n", "\n").split("\n")
    blocks, current = [], []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _parse_single(lines):
    options, slide_refs = {}, []
    question_lines, objective, difficulty, answer = [], "", "", ""

    for i, line in enumerate(lines):
        option_match = OPTION_RE.match(line)
        answer_match = ANSWER_RE.match(line)
        difficulty_match = DIFFICULTY_RE.match(line)
        objective_match = OBJECTIVE_RE.match(line)
        slide_match = SLIDE_RE.match(line)

        if option_match and not answer_match:
            key = option_match.group(1).upper()
            options[key] = option_match.group("text").strip()
        elif answer_match:
            answer = answer_match.group(1).upper()
        elif difficulty_match:
            difficulty = difficulty_match.group(1).strip().lower()
        elif objective_match:
            objective = objective_match.group(1).strip()
        elif slide_match:
            slide_refs.append(slide_match.group(1).strip())
        else:
            if i == 0:
                line = NUMBERING_RE.sub("", line)
            question_lines.append(line.strip())

    prompt = " ".join(question_lines).strip()
    if not prompt:
        return "could not find a question prompt"
    if not options:
        return f"no options found for: {prompt[:60]}..."
    if not answer:
        return f"missing 'Answer:' line for: {prompt[:60]}..."
    if answer not in options:
        return f"answer '{answer}' has no matching option for: {prompt[:60]}..."

    return {
        "id": new_id("mcq"),
        "kind": "mcq",
        "question": prompt,
        "options": options,
        "correct_option": answer,
        "difficulty": difficulty or "medium",
        "learning_objective": objective,
        "slide_refs": slide_refs,
        "node_links": [],
    }
