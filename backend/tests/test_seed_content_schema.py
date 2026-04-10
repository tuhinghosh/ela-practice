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


def test_seed_content_includes_literary_and_informational() -> None:
    activities = load_seed_activities()
    types = {activity.passageType for activity in activities}
    assert "literary" in types
    assert "informational" in types


def test_seed_questions_cover_multiple_choice_and_short_response() -> None:
    activities = load_seed_activities()
    question_types = {question.type for activity in activities for question in activity.questions}
    assert "multiple-choice" in question_types
    assert "short-response" in question_types


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
        sentence_count = len([part for part in re.split(r"(?<=[.!?])\s+", activity.passageText.strip()) if part])
        assert 10 <= sentence_count <= 15
