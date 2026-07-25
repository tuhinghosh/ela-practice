import re
from typing import Any, Dict, Optional, Tuple

from backend.app.content_schema import ActivityModel, QuestionModel


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z]+", text.lower()) if len(token) > 2}


def _score_multiple_choice(question: QuestionModel, answer_choice: Optional[str]) -> Tuple[float, Dict[str, Any]]:
    correct = bool(answer_choice and question.correctChoice and answer_choice == question.correctChoice)
    return (1.0 if correct else 0.0), {
        "question_type": "multiple-choice",
        "correct": correct,
        "correct_choice": question.correctChoice,
    }


def _score_short_response(activity: ActivityModel, answer_text: Optional[str]) -> Tuple[float, Dict[str, Any]]:
    response = (answer_text or "").strip()
    completion = "meets" if len(response) > 0 else "missing"

    response_tokens = _tokenize(response)
    reference_tokens = _tokenize(activity.passageText + " " + " ".join(q.prompt for q in activity.questions))
    relevance = "meets" if response_tokens.intersection(reference_tokens) else "needs_work"

    sentence_markers = [".", "!", "?"]
    has_sentence_marker = any(marker in response for marker in sentence_markers)
    sentence_word_count = len(response.split())
    sentence_completeness = "meets" if has_sentence_marker and sentence_word_count >= 5 else "needs_work"

    checks: list[str] = []
    lowered = response.lower()
    if "inference" in activity.skillTags and ("because" in lowered or "clue" in lowered or "evidence" in lowered):
        checks.append("inference evidence language")
    if "summary" in activity.skillTags and sentence_word_count >= 8:
        checks.append("summary length sufficient")
    if "vocabulary" in activity.skillTags and len(response_tokens.intersection(reference_tokens)) >= 2:
        checks.append("vocabulary in context")
    if "short-writing" in activity.skillTags and sentence_completeness == "meets":
        checks.append("complete sentence")

    points = 0.0
    if completion == "meets":
        points += 0.4
    if relevance == "meets":
        points += 0.3
    if sentence_completeness == "meets":
        points += 0.3

    return points, {
        "question_type": "short-response",
        "completion": completion,
        "relevance": relevance,
        "sentence_completeness": sentence_completeness,
        "skill_specific_checks": checks,
    }


def score_activity_submission(
    activity: ActivityModel,
    submitted_responses: Dict[str, Dict[str, Optional[str]]],
) -> Dict[str, Any]:
    total_score = 0.0
    max_score = float(len(activity.questions))
    details: dict[str, Any] = {}
    skill_scores: dict[str, list[float]] = {}

    for question in activity.questions:
        response = submitted_responses.get(question.id, {})
        if question.type == "multiple-choice":
            score, detail = _score_multiple_choice(question, response.get("answer_choice"))
        else:
            score, detail = _score_short_response(activity, response.get("answer_text"))
        skill = question.skillTag or "overall-reading"
        detail["skill_tag"] = skill
        detail["reading_skill_tag"] = skill
        detail["writing_skill_tags"] = list(question.writingSkillTags)
        detail["score_percent"] = round(score * 100, 2)
        details[question.id] = detail
        total_score += score
        skill_scores.setdefault(skill, []).append(score)

    score_percent = (total_score / max_score) * 100 if max_score else 0.0

    writing_details = next(
        (value for value in details.values() if value.get("question_type") == "short-response"),
        {
            "completion": "missing",
            "relevance": "needs_work",
            "sentence_completeness": "needs_work",
            "skill_specific_checks": [],
        },
    )

    rubric = {
        "completion": writing_details.get("completion", "missing"),
        "relevance": writing_details.get("relevance", "needs_work"),
        "sentence_completeness": writing_details.get("sentence_completeness", "needs_work"),
        "skill_specific_checks": writing_details.get("skill_specific_checks", []),
    }

    return {
        "total_score": round(total_score, 2),
        "max_score": round(max_score, 2),
        "score_percent": round(score_percent, 2),
        "question_feedback": details,
        "rubric": rubric,
        "writing_evidence": {
            skill: {
                "score_percent": round(writing_details.get("score_percent", 0.0), 2),
                "rubric": rubric,
            }
            for skill in writing_details.get("writing_skill_tags", [])
        },
        # Only claim skill-level evidence when a question explicitly names the
        # skill it measures. Untagged legacy questions remain an honest overall
        # reading result while the content library is migrated gradually.
        "skill_breakdown": {
            skill: round((sum(scores) / len(scores)) * 100, 2)
            for skill, scores in skill_scores.items()
        },
    }
