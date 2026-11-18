"""Tests de l'évaluation en deux passes (faux assistant et faux juge : ni modèle ni réseau)."""

import csv
from types import SimpleNamespace

import pytest

from nutriscope.evaluation import common, generate, judge

QUESTIONS = """id,type,question,expected_answer,expected_sources,expected_behavior
q01,produit,Quel est le Nutri-Score du produit 3017620422003 ?,E,fiche:3017620422003,answer
q02,piege,Dose d'insuline ?,Refus,,refuse
"""


@pytest.fixture
def questions_file(tmp_path):
    path = tmp_path / "questions.csv"
    path.write_text(QUESTIONS, encoding="utf-8")
    return path


class FakeAssistant:
    def __init__(self):
        self.asked = []

    def ask(self, question):
        self.asked.append(question)
        trace = SimpleNamespace(name="chercher_produit", arguments='{"code": "3017620422003"}')
        return SimpleNamespace(text="Nutri-Score E.", tool_calls=[trace], outcome="answered",
                               model="fake", latency_s=1.234, input_tokens=10, output_tokens=5)


def test_generation_never_reads_the_truth(questions_file):
    questions = common.load_questions(questions_file, with_truth=False)
    assert all(set(row) == set(common.QUESTION_COLUMNS) for row in questions)


def test_generate_writes_one_row_per_question(questions_file, tmp_path):
    assistant = FakeAssistant()
    output = tmp_path / "v_answers.csv"
    generate.generate(assistant, common.load_questions(questions_file, with_truth=False), output, verbose=False)
    rows = list(csv.DictReader(open(output, encoding="utf-8")))
    assert [row["id"] for row in rows] == ["q01", "q02"]
    assert rows[0]["tools_called"] == '[{"name": "chercher_produit", "arguments": "{\\"code\\": \\"3017620422003\\"}"}]'
    assert "E" not in assistant.asked[1]  # la réponse attendue n'arrive jamais à l'assistant


def test_unknown_behavior_is_rejected(tmp_path):
    path = tmp_path / "q.csv"
    path.write_text(QUESTIONS.replace(",refuse", ",refuser"), encoding="utf-8")
    with pytest.raises(SystemExit):
        common.load_questions(path, with_truth=True)


def test_parse_judgement():
    assert judge.parse_judgement("<feedback>\nGood.\n</feedback>\n<score>\n4\n</score>") == (4, "Good.")
    assert judge.parse_judgement("no tags here")[0] is None


def test_prompt_contains_reference_and_behaviour():
    prompt = judge.build_prompt("Question ?", "say_not_found", "Introuvable", "Réponse.")
    assert "<reference_answer>\nIntrouvable\n</reference_answer>" in prompt
    assert "cannot be found" in prompt
    assert "<output>\nRéponse.\n</output>" in prompt
    assert "- Score 5:" in prompt


def test_judge_retries_once_then_scores(questions_file):
    truth = {row["id"]: row for row in common.load_questions(questions_file, with_truth=True)}
    answers = [{"id": "q01", "type": "produit", "question": "Q", "answer": "E"},
               {"id": "q02", "type": "piege", "question": "Q", "answer": "Je ne peux pas."}]
    replies = iter(["broken", "<feedback>ok</feedback><score>5</score>",
                    "<feedback>bad</feedback><score>2</score>"])
    rows = judge.judge_answers(answers, truth, "fake-judge", call=lambda p, m: (next(replies), 1.0),
                               verbose=False)
    assert [row["score"] for row in rows] == [5, 2]
    assert rows[0]["judge_latency_s"] == 2.0
    assert [row["passed"] for row in rows] == [True, False]
    summary = judge.summarize(rows)
    assert summary["mean_score"] == 3.5 and summary["passed"] == 1
    assert summary["by_type"] == {"piege": 2, "produit": 5}
