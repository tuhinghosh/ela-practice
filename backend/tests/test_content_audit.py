from copy import deepcopy

from backend.app.content_audit import audit_content
from backend.app.content_schema import list_seed_activities, load_review_statuses


def _content():
    return deepcopy(list(list_seed_activities())), dict(load_review_statuses())


def test_review_registry_classifies_every_activity_once() -> None:
    activities, statuses = _content()
    assert set(statuses) == {activity.id for activity in activities}
    assert list(statuses.values()).count("reviewed") == 9
    assert list(statuses.values()).count("rewrite-required") == 26
    assert list(statuses.values()).count("draft") == 53


def test_reviewed_pool_passes_all_hard_quality_gates() -> None:
    activities, statuses = _content()
    report = audit_content(activities, statuses)
    assert report.errors == []
    assert report.reviewed_count == 9
    assert report.tier_counts == {"easy": 3, "medium": 3, "difficult": 3}


def test_reviewed_skill_by_difficulty_coverage_matches_verified_baseline() -> None:
    activities, statuses = _content()
    report = audit_content(activities, statuses)
    assert report.skill_tier_coverage == {
        "reading-comprehension": {"easy": 3, "medium": 2, "difficult": 1},
        "main-idea": {"easy": 1, "medium": 2, "difficult": 2},
        "inference": {"easy": 3, "medium": 3, "difficult": 3},
        "sequence": {"easy": 1, "medium": 1, "difficult": 0},
        "summary": {"easy": 2, "medium": 2, "difficult": 3},
        "vocabulary": {"easy": 2, "medium": 2, "difficult": 3},
    }
    assert report.skill_tier_target_gaps["sequence"] == {
        "easy": 3,
        "medium": 3,
        "difficult": 4,
    }
    assert report.skill_tier_target_gaps["inference"] == {
        "easy": 1,
        "medium": 1,
        "difficult": 1,
    }


def test_audit_rejects_skill_by_difficulty_coverage_regression() -> None:
    activities, statuses = _content()
    easy_main_idea = next(
        activity
        for activity in activities
        if statuses[activity.id] == "reviewed"
        and activity.difficulty == "easy"
        and any(question.skillTag == "main-idea" for question in activity.questions)
    )
    question = next(
        question for question in easy_main_idea.questions if question.skillTag == "main-idea"
    )
    question.skillTag = None

    report = audit_content(activities, statuses)

    assert report.skill_tier_coverage["main-idea"]["easy"] == 0
    assert any(
        '"main-idea" / "easy" coverage regressed to 0 activities; baseline is 1.'
        in error
        for error in report.errors
    )


def test_audit_rejects_missing_review_status() -> None:
    activities, statuses = _content()
    statuses.pop(activities[0].id)
    report = audit_content(activities, statuses)
    assert any("missing review status" in error for error in report.errors)


def test_audit_rejects_reviewed_content_without_required_feedback() -> None:
    activities, statuses = _content()
    reviewed = next(activity for activity in activities if statuses[activity.id] == "reviewed")
    objective = next(q for q in reviewed.questions if q.type == "multiple-choice")
    objective.answerExplanation = None
    response = next(q for q in reviewed.questions if q.type == "short-response")
    response.responseGuidance = None
    response.writingSkillTags = []
    report = audit_content(activities, statuses)
    assert any("answer explanation" in error for error in report.errors)
    assert any("response guidance" in error for error in report.errors)
    assert any("writing skill tags" in error for error in report.errors)


def test_audit_rejects_unsourced_reviewed_informational_content() -> None:
    activities, statuses = _content()
    reviewed = next(
        activity
        for activity in activities
        if statuses[activity.id] == "reviewed" and activity.passageType == "informational"
    )
    reviewed.sourceUrls = []
    report = audit_content(activities, statuses)
    assert any("informational passage needs sources" in error for error in report.errors)


def test_audit_rejects_predictable_answer_positions() -> None:
    activities, statuses = _content()
    for activity in activities:
        if statuses[activity.id] != "reviewed":
            continue
        for question in activity.questions:
            if question.type == "multiple-choice" and question.choices:
                question.correctChoice = question.choices[0]
    report = audit_content(activities, statuses)
    assert any("too predictable" in error for error in report.errors)


def test_audit_rejects_duplicate_reviewed_passage_sentence() -> None:
    activities, statuses = _content()
    reviewed = [activity for activity in activities if statuses[activity.id] == "reviewed"]
    sentence = "This deliberately repeated sentence contains enough words to trigger the exact duplication check."
    reviewed[0].passageText += " " + sentence
    reviewed[1].passageText += " " + sentence
    report = audit_content(activities, statuses)
    assert any("Duplicate reviewed passage sentence" in error for error in report.errors)
