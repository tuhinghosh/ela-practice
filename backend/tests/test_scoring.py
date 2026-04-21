from backend.app.content_schema import get_seed_activity
from backend.app.scoring import score_activity_submission


def test_scoring_returns_expected_shape() -> None:
    activity = get_seed_activity("nature-01")
    payload = {
        "q1": {"answer_choice": "The oak tree's roots took the water", "answer_text": None},
        "q2": {"answer_choice": "Healthy things that help plants grow", "answer_text": None},
        "q3": {"answer_choice": "Determined", "answer_text": None},
        "q4": {"answer_choice": None, "answer_text": "Lila did not give up because she tried moving the pot to a sunny spot."},
    }

    result = score_activity_submission(activity, payload)

    assert result["max_score"] == 4.0
    assert "rubric" in result
    assert "question_feedback" in result
    assert result["score_percent"] >= 0
    assert set(result["skill_breakdown"].keys()) == set(activity.skillTags)


def test_scoring_is_deterministic_for_same_payload() -> None:
    activity = get_seed_activity("nature-02")
    payload = {
        "q1": {"answer_choice": "A baby duck was trapped between rocks", "answer_text": None},
        "q2": {"answer_choice": "To give the duckling's feet something to grip", "answer_text": None},
        "q3": {"answer_choice": None, "answer_text": "Marco helped the duckling by placing sticks so it could climb out."},
    }

    first = score_activity_submission(activity, payload)
    second = score_activity_submission(activity, payload)

    assert first["score_percent"] == second["score_percent"]
    assert first["rubric"] == second["rubric"]
