from itertools import count
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.app.config import ConfigError, load_settings
from backend.app.main import app, login_limiter
from backend.app.rate_limit import SlidingWindowLimiter


@pytest.fixture
def fake_clock() -> Iterator[list[float]]:
    """A shared 1-element list lets tests advance time without sleeping."""
    state = [0.0]
    yield state


def _limiter(state: list[float], *, max_attempts: int = 3, window_seconds: float = 60.0) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(
        max_attempts=max_attempts,
        window_seconds=window_seconds,
        clock=lambda: state[0],
    )


def test_failures_accumulate_then_block(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=3)

    limiter.register_failure("ip-1")
    assert limiter.check("ip-1").allowed is True and limiter.check("ip-1").remaining == 2
    limiter.register_failure("ip-1")
    assert limiter.check("ip-1").remaining == 1
    limiter.register_failure("ip-1")

    blocked = limiter.check("ip-1")
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds > 0


def test_check_does_not_record(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=2)
    for _ in range(5):
        assert limiter.check("ip-x").allowed is True
    limiter.register_failure("ip-x")
    assert limiter.check("ip-x").allowed is True
    assert limiter.check("ip-x").remaining == 1


def test_clear_releases_a_key(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=2)
    limiter.register_failure("ip-2")
    limiter.register_failure("ip-2")
    assert limiter.check("ip-2").allowed is False

    limiter.clear("ip-2")
    assert limiter.check("ip-2").allowed is True


def test_window_expiry_releases_old_attempts(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=2, window_seconds=30.0)
    limiter.register_failure("ip-3")
    limiter.register_failure("ip-3")
    assert limiter.check("ip-3").allowed is False

    fake_clock[0] = 31.0  # advance past window
    result = limiter.check("ip-3")
    assert result.allowed is True
    assert result.remaining == 2


def test_keys_are_independent(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=2)
    limiter.register_failure("alpha")
    limiter.register_failure("alpha")
    assert limiter.check("alpha").allowed is False
    assert limiter.check("beta").allowed is True


def test_zero_max_attempts_disables_limiter(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=0)
    assert limiter.is_enabled is False
    for _ in range(100):
        limiter.register_failure("k")
        assert limiter.check("k").allowed is True


def test_zero_window_disables_limiter(fake_clock: list[float]) -> None:
    limiter = _limiter(fake_clock, max_attempts=3, window_seconds=0.0)
    assert limiter.is_enabled is False
    for _ in range(100):
        limiter.register_failure("k")
        assert limiter.check("k").allowed is True


def test_negative_config_rejected() -> None:
    with pytest.raises(ValueError):
        SlidingWindowLimiter(max_attempts=-1, window_seconds=10)
    with pytest.raises(ValueError):
        SlidingWindowLimiter(max_attempts=1, window_seconds=-1)


def test_config_parses_rate_limit_env_vars() -> None:
    settings = load_settings(
        env={
            "LOGIN_RATE_LIMIT_MAX_ATTEMPTS": "5",
            "LOGIN_RATE_LIMIT_WINDOW_SECONDS": "120",
        }
    )
    assert settings.login_rate_limit_max_attempts == 5
    assert settings.login_rate_limit_window_seconds == 120


def test_config_defaults_rate_limit_when_unset() -> None:
    settings = load_settings(env={})
    assert settings.login_rate_limit_max_attempts == 10
    assert settings.login_rate_limit_window_seconds == 60


def test_config_rejects_non_integer_rate_limit() -> None:
    with pytest.raises(ConfigError, match="must be an integer"):
        load_settings(env={"LOGIN_RATE_LIMIT_MAX_ATTEMPTS": "lots"})


def test_config_rejects_negative_rate_limit() -> None:
    with pytest.raises(ConfigError, match="must be >= 0"):
        load_settings(env={"LOGIN_RATE_LIMIT_WINDOW_SECONDS": "-5"})


def test_login_endpoint_returns_429_after_too_many_failures() -> None:
    # The shipped runtime limiter is 10/60s; flood it to confirm the 11th
    # failure flips to 429 with a Retry-After header.
    counter = count()
    with TestClient(app) as client:
        for _ in range(10):
            resp = client.post(
                "/api/auth/login",
                json={"username": f"nope-{next(counter)}", "password": "wrong"},
            )
            assert resp.status_code == 401

        blocked = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "wrong"},
        )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
        assert int(blocked.headers["Retry-After"]) >= 1

        # Even the correct password is refused while blocked, since the
        # gate fires before credential check.
        still_blocked = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
        assert still_blocked.status_code == 429


def test_successful_login_clears_prior_failures() -> None:
    with TestClient(app) as client:
        for _ in range(5):
            assert (
                client.post(
                    "/api/auth/login",
                    json={"username": "user", "password": "wrong"},
                ).status_code
                == 401
            )

        ok = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
        assert ok.status_code == 200

        # After a successful login the counter is cleared, so we should
        # have a full budget of fresh failures again.
        for _ in range(10):
            assert (
                client.post(
                    "/api/auth/login",
                    json={"username": "user", "password": "wrong"},
                ).status_code
                == 401
            )

        # The 11th failure should now trip the limiter, proving the budget
        # really did reset (otherwise we'd have tripped earlier).
        assert (
            client.post(
                "/api/auth/login",
                json={"username": "user", "password": "wrong"},
            ).status_code
            == 429
        )


def test_module_limiter_is_reset_between_tests() -> None:
    # Sanity: the autouse conftest fixture cleared state, so we should not
    # see leftover failures from any earlier test in the suite.
    assert login_limiter.check("127.0.0.1").allowed is True
    assert login_limiter.check("127.0.0.1").remaining == 10
