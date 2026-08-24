from core.mcq_parser import parse_mcq_block


SAMPLE = """
1. What does SVD stand for?
A) Singular Value Decomposition
B) Standard Vector Distance
Answer: A
Difficulty: easy
Objective: Recall terminology
Slides: 3, 4

2) Which method uses partial pivoting?
a) Gaussian elimination
b) Cholesky
c) Jacobi
Answer: b
"""


def test_parses_multiple_blocks_with_metadata():
    questions, errors = parse_mcq_block(SAMPLE)
    assert errors == []
    assert len(questions) == 2

    q1, q2 = questions
    assert q1["question"] == "What does SVD stand for?"
    assert q1["correct_option"] == "A"
    assert q1["difficulty"] == "easy"
    assert q1["learning_objective"] == "Recall terminology"
    assert q1["slide_refs"] == ["3, 4"]

    assert q2["options"]["B"] == "Cholesky"
    assert q2["correct_option"] == "B"


def test_reports_missing_answer_line():
    questions, errors = parse_mcq_block("Q?\nA) one\nB) two")
    assert questions == []
    assert len(errors) == 1 and "missing 'Answer:'" in errors[0]


def test_reports_answer_without_matching_option():
    questions, errors = parse_mcq_block("Q?\nA) one\nB) two\nAnswer: C")
    assert questions == []
    assert "answer 'C'" in errors[0]


def test_ignores_blank_noise_between_blocks():
    questions, _ = parse_mcq_block("\n\n\nQ?\nA) 1\nB) 2\nAnswer: A\n\n\n\n")
    assert len(questions) == 1
