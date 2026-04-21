import json
import re

from backend.app.content_schema import (
    ACTIVITIES_FILE,
    SKILL_TAGS_FILE,
    ActivityModel,
    load_seed_activities,
)


def test_seed_content_validates_against_schema() -> None:
    activities = load_seed_activities()
    assert activities, "Expected at least one seeded activity."
    assert all(isinstance(activity, ActivityModel) for activity in activities)


def test_seed_content_includes_literary_informational_and_poetry() -> None:
    activities = load_seed_activities()
    types = {activity.passageType for activity in activities}
    assert "literary" in types
    assert "informational" in types
    assert "poetry" in types


def test_seed_questions_cover_multiple_choice_and_short_response() -> None:
    activities = load_seed_activities()
    question_types = {question.type for activity in activities for question in activity.questions}
    assert "multiple-choice" in question_types
    assert "short-response" in question_types


def test_seed_activities_have_two_or_more_follow_up_questions() -> None:
    activities = load_seed_activities()
    for activity in activities:
        assert len(activity.questions) >= 2
        assert all(question.prompt.strip() for question in activity.questions)


def test_seed_skill_tags_are_known() -> None:
    skill_tags = json.loads(SKILL_TAGS_FILE.read_text(encoding="utf-8"))
    activities = load_seed_activities()

    used_tags = {tag for activity in activities for tag in activity.skillTags}
    assert used_tags.issubset(set(skill_tags))
    assert used_tags, "Expected seeded activities to include skill tags."


def test_seed_content_has_no_malformed_missing_fields() -> None:
    raw = json.loads(ACTIVITIES_FILE.read_text(encoding="utf-8"))
    required_activity_fields = {
        "id",
        "title",
        "theme",
        "passageType",
        "missionLabel",
        "passageTitle",
        "passageText",
        "questions",
        "skillTags",
    }
    required_question_fields = {"id", "type", "prompt"}

    for activity in raw:
        assert required_activity_fields.issubset(set(activity.keys()))
        assert activity["questions"], "Each activity must include questions."
        for question in activity["questions"]:
            assert required_question_fields.issubset(set(question.keys()))


def test_seed_content_has_balanced_difficulty_distribution() -> None:
    activities = load_seed_activities()
    counts = {"easy": 0, "medium": 0, "difficult": 0}
    for activity in activities:
        tier = str(activity.difficulty)
        counts[tier] += 1

    assert all(value > 0 for value in counts.values())
    assert max(counts.values()) - min(counts.values()) <= 1


def test_seed_passages_have_required_sentence_length() -> None:
    activities = load_seed_activities()
    for activity in activities:
        if activity.passageType == "poetry":
            continue
        sentence_count = len([part for part in re.split(r"(?<=[.!?])\s+", activity.passageText.strip()) if part])
        assert sentence_count >= 8


def test_seed_passages_have_at_least_two_paragraphs() -> None:
    activities = load_seed_activities()
    for activity in activities:
        if activity.passageType == "poetry":
            continue
        paragraphs = [part for part in re.split(r"\n\s*\n", activity.passageText.strip()) if part.strip()]
        assert len(paragraphs) >= 2


def test_seed_passages_follow_two_paragraph_narrative_arc() -> None:
    activities = [a for a in load_seed_activities() if a.passageType != "poetry"]
    setup_cues = ("needed to", "had to", "problem", "challenge", "question", "goal", "plan", "clue", "worried", "noticed", "task", "decided", "wanted", "tried", "began", "hoped", "set out", "wondered")
    outcome_cues = (
        "by the end",
        "learned",
        "as a result",
        "this showed",
        "this helped",
        "improved",
        "solved",
        "understood",
        "agreed",
        "realized",
        "discovered",
        "finally",
        "after that",
        "from then on",
        "knew",
    )
    for activity in activities:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", activity.passageText.strip()) if part.strip()]
        first_sentences = [part for part in re.split(r"(?<=[.!?])\s+", paragraphs[0].replace("\n", " ").strip()) if part]
        second_sentences = [part for part in re.split(r"(?<=[.!?])\s+", paragraphs[1].replace("\n", " ").strip()) if part]
        assert len(first_sentences) >= 2
        assert len(second_sentences) >= 2
        first_lowered = paragraphs[0].lower()
        full_lowered = activity.passageText.lower()
        assert any(cue in first_lowered for cue in setup_cues)
        assert any(cue in full_lowered for cue in outcome_cues)


def test_seed_passages_do_not_include_coaching_meta_text() -> None:
    activities = [a for a in load_seed_activities() if a.passageType != "poetry"]
    banned_phrases = (
        "when summarizing",
        "these passages",
        "as you read",
        "a careful reader",
    )
    for activity in activities:
        lowered = activity.passageText.lower()
        assert all(phrase not in lowered for phrase in banned_phrases)
