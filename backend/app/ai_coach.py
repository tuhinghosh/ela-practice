import json
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError

from backend.app.ai_client import run_openrouter_chat


def _parse_confidence(value: Any) -> float:
    """Coerce LLM confidence output to a float between 0 and 1."""
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        cleaned = value.strip().lower()
        try:
            return max(0.0, min(1.0, float(cleaned)))
        except ValueError:
            label_map = {"low": 0.3, "medium": 0.5, "high": 0.8, "very high": 0.9, "developing": 0.5}
            return label_map.get(cleaned, 0.5)
    return 0.5


class CoachOutputModel(BaseModel):
    message_to_child: str = Field(min_length=1)
    message_to_parent: Optional[str] = None
    hint: Optional[str] = None
    explanation: str = Field(min_length=1)
    celebration: str = Field(min_length=1)
    suggested_next_activity_id: Optional[str] = None
    suggested_skill_tag: Optional[str] = None
    writing_feedback: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


def build_ai_coach_system_prompt() -> str:
    return (
        "You are a reading coach for a third-grade child. "
        "Give specific, honest feedback on the reading activity they just completed.\n\n"
        "COACHING TONE:\n"
        "- Be warm but honest. Do not over-praise weak answers.\n"
        "- A one-word answer or vague answer is NOT 'a great start' — say it needs more detail.\n"
        "- Praise should be proportional to effort. Only celebrate what the child actually did well.\n"
        "- Use simple language a third grader understands.\n\n"
        "COACHING CONTENT:\n"
        "- Quote the child's actual words when discussing their answers.\n"
        "- For correct MC answers: briefly note what they got right (one sentence).\n"
        "- For wrong MC answers: explain which passage detail points to the correct answer.\n"
        "- For short-response: if the answer is too short or vague, say so directly and model what a stronger answer looks like.\n"
        "- If the child asks a follow-up question, answer it using specific passage details.\n\n"
        "FIELD RULES (each field has a distinct purpose — DO NOT repeat the same point across fields):\n"
        "- message_to_child: The main coaching feedback. Cover what went well and what to improve. 3-5 sentences max.\n"
        "- celebration: ONE short sentence acknowledging effort. Skip if the score is very low — use encouragement instead.\n"
        "- explanation: For the PARENT — a brief factual summary of what the child got right/wrong. No praise language.\n"
        "- hint: One actionable tip for the child's weakest area. Different from message_to_child.\n"
        "- writing_feedback: Only if there was a short-response question. Comment on the writing specifically. Null if not applicable.\n"
        "- message_to_parent: Brief note for the parent about what to practice. Null if not needed.\n\n"
        "SAFETY: Stay focused on this activity only. Child-safe language. Return valid JSON only."
    )


def _format_questions_for_prompt(questions: list) -> str:
    lines = []
    for i, q in enumerate(questions, 1):
        qtype = q.get("question_type", "unknown")
        prompt = q.get("prompt", "")
        child_answer = q.get("child_answer", "")
        lines.append(f"  Question {i} ({qtype}): {prompt}")
        lines.append(f"  Child's answer: \"{child_answer}\"")
        if qtype == "multiple-choice":
            correct = q.get("correct_answer", "")
            is_correct = q.get("is_correct", False)
            lines.append(f"  Correct answer: \"{correct}\"")
            lines.append(f"  Result: {'Correct' if is_correct else 'Incorrect'}")
        lines.append("")
    return "\n".join(lines)


def build_ai_coach_user_prompt(context: Dict[str, Any], child_question: Optional[str]) -> str:
    passage_text = context.get("passage_text", "")
    passage_excerpt = passage_text[:1500] if len(passage_text) > 1500 else passage_text
    questions_text = _format_questions_for_prompt(context.get("questions_with_answers", []))

    parts = [
        "Generate post-submission coaching feedback in strict JSON.\n",
        f"ACTIVITY: {context.get('activity_title')}\n",
        f"PASSAGE (the child read this):\n{passage_excerpt}\n",
        f"QUESTIONS AND ANSWERS:\n{questions_text}",
        f"OVERALL SCORE: {context.get('score_percent')}%",
        f"RUBRIC: {json.dumps(context.get('rubric', {}), ensure_ascii=True)}",
        f"SKILL TAGS: {json.dumps(context.get('skill_breakdown', {}), ensure_ascii=True)}",
        f"RECENT STRENGTHS: {json.dumps(context.get('strengths', []), ensure_ascii=True)}",
        f"RECENT GROWTH AREAS: {json.dumps(context.get('growth_areas', []), ensure_ascii=True)}",
    ]
    if child_question:
        parts.append(f"\nCHILD'S FOLLOW-UP QUESTION: \"{child_question}\"")
        parts.append("Answer their question using specific details from the passage above.")

    parts.append(
        "\nRespond with a JSON object with these exact fields: "
        "message_to_child, message_to_parent, hint, explanation, celebration, "
        "suggested_next_activity_id, suggested_skill_tag, writing_feedback, confidence.\n\n"
        "IMPORTANT: Each field must say something DIFFERENT. Do not repeat the same feedback across fields.\n"
        "- message_to_child: Main feedback with specific references to their answers (3-5 sentences).\n"
        "- celebration: One SHORT sentence (max 15 words). Proportional to performance.\n"
        "- explanation: For the parent. Factual summary — no praise language. (2-3 sentences).\n"
        "- hint: One NEW actionable tip not already covered in message_to_child.\n"
        "- writing_feedback: Comment on the short-response writing only. Null if no short-response question.\n"
        "- confidence: a number from 0 to 1."
    )
    return "\n".join(parts)


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def build_fallback_coach_output(context: Dict[str, Any], child_question: Optional[str] = None) -> Dict[str, Any]:
    score_percent = float(context.get("score_percent", 0))
    celebration = (
        "Great effort! You finished your reading quest and kept trying."
        if score_percent < 80
        else "Amazing work! You finished your reading quest with strong answers."
    )
    question = (child_question or "").strip().lower()
    if "evidence" in question:
        hint = "Quote or paraphrase one exact clue from the passage, then explain how it proves your idea."
        explanation = (
            "Strong evidence answers use a specific passage detail and then connect that detail to the claim."
        )
        writing_feedback = "Try this frame: \"In the passage, ___. This shows ___ because ___.\""
        message_to_child = "Great question. To make evidence stronger, use one exact text clue and explain why it matters."
    elif "main idea" in question:
        hint = "State the topic first, then include one key detail that appears more than once."
        explanation = "Main-idea answers are strongest when they include the big point and one supporting detail."
        writing_feedback = "Write one sentence for the big idea and one sentence for supporting evidence."
        message_to_child = "Nice thinking. A strong main-idea answer includes the big point plus a key supporting detail."
    else:
        hint = "Look for clue words in the passage and connect them to your answer."
        explanation = "Strong answers match the passage details and use complete sentences."
        writing_feedback = "Try adding one sentence that clearly explains your evidence."
        message_to_child = "I am proud of your hard work today. Keep using evidence from the passage."

    return {
        "message_to_child": message_to_child,
        "message_to_parent": "The child completed a post-submission coaching step with safe fallback guidance.",
        "hint": hint,
        "explanation": explanation,
        "celebration": celebration,
        "suggested_next_activity_id": None,
        "suggested_skill_tag": "reading-comprehension",
        "writing_feedback": writing_feedback,
        "confidence": 0.5,
    }


def generate_ai_coach_output(context: Dict[str, Any], child_question: Optional[str] = None) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": build_ai_coach_system_prompt()},
        {"role": "user", "content": build_ai_coach_user_prompt(context, child_question)},
    ]
    result = run_openrouter_chat(
        messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw_text = result["response_text"]

    try:
        parsed = _extract_json_object(raw_text)
        if "confidence" in parsed:
            parsed["confidence"] = _parse_confidence(parsed["confidence"])
        validated = CoachOutputModel.model_validate(parsed)
        payload = validated.model_dump()
        payload["used_fallback"] = False
        payload["model"] = result["model"]
        return payload
    except (json.JSONDecodeError, ValidationError):
        fallback = build_fallback_coach_output(context, child_question=child_question)
        fallback["used_fallback"] = True
        fallback["model"] = result["model"]
        return fallback
