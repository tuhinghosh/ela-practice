from backend.app.content_schema import get_seed_activity
from backend.app.scoring import score_activity_submission


def test_scoring_returns_expected_shape() -> None:
    activity = get_seed_activity("forest-friends")
    payload = {
        "q1": {"answer_choice": "The birds show teamwork while building a nest.", "answer_text": None},
        "q2": {"answer_choice": None, "answer_text": "The bird came back for the twig because it did not give up."},
    }

    result = score_activity_submission(activity, payload)

    assert result["max_score"] == 2.0
    assert "rubric" in result
    assert "question_feedback" in result
    assert result["score_percent"] >= 0
    assert set(result["skill_breakdown"].keys()) == set(activity.skillTags)


def test_scoring_is_deterministic_for_same_payload() -> None:
    activity = get_seed_activity("bees-and-flowers")
    payload = {
        "q1": {"answer_choice": "Bees spread pollen from one flower to another.", "answer_text": None},
        "q2": {"answer_choice": None, "answer_text": "Bees help flowers make seeds and fruit. This helps farms and gardens."},
    }

    first = score_activity_submission(activity, payload)
    second = score_activity_submission(activity, payload)

    assert first["score_percent"] == second["score_percent"]
    assert first["rubric"] == second["rubric"]
