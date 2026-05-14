import logging

import pytest

from backend.app.config import (
    DEV_SESSION_SECRET,
    ConfigError,
    load_settings,
)


def test_dev_default_uses_placeholder_secret_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="backend.app.config"):
        settings = load_settings(env={})

    assert settings.env == "dev"
    assert settings.session_secret == DEV_SESSION_SECRET
    assert settings.session_cookie_name == "ela_session"
    assert settings.session_cookie_secure is False
    assert settings.session_cookie_samesite == "lax"
    assert any("dev placeholder" in record.message for record in caplog.records)


def test_dev_with_explicit_secret_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="backend.app.config"):
        settings = load_settings(env={"SESSION_SECRET": "explicit-dev-secret"})

    assert settings.session_secret == "explicit-dev-secret"
    assert not any("dev placeholder" in record.message for record in caplog.records)


def test_prod_requires_session_secret() -> None:
    with pytest.raises(ConfigError, match="SESSION_SECRET is required"):
        load_settings(env={"ELA_ENV": "prod"})


def test_prod_rejects_dev_placeholder_secret() -> None:
    with pytest.raises(ConfigError, match="dev placeholder"):
        load_settings(env={"ELA_ENV": "prod", "SESSION_SECRET": DEV_SESSION_SECRET})


_PROD_ENV = {
    "ELA_ENV": "prod",
    "SESSION_SECRET": "a-strong-random-value",
    "ELA_BOOTSTRAP_USERNAME": "admin",
    "ELA_BOOTSTRAP_PASSWORD": "a-very-secure-bootstrap-password",
}


def test_prod_defaults_to_secure_cookies() -> None:
    settings = load_settings(env=_PROD_ENV)

    assert settings.env == "prod"
    assert settings.is_prod is True
    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "lax"


def test_cookie_secure_can_be_overridden() -> None:
    settings = load_settings(
        env={
            **_PROD_ENV,
            "SESSION_COOKIE_SECURE": "false",
            "SESSION_COOKIE_SAMESITE": "strict",
        },
    )

    assert settings.session_cookie_secure is False
    assert settings.session_cookie_samesite == "strict"


def test_samesite_none_requires_secure_cookie() -> None:
    with pytest.raises(ConfigError, match="SAMESITE=none requires"):
        load_settings(
            env={
                **_PROD_ENV,
                "SESSION_COOKIE_SECURE": "false",
                "SESSION_COOKIE_SAMESITE": "none",
            },
        )


def test_invalid_env_value_raises() -> None:
    with pytest.raises(ConfigError, match="Invalid ELA_ENV"):
        load_settings(env={"ELA_ENV": "staging"})


def test_invalid_boolean_raises() -> None:
    with pytest.raises(ConfigError, match="Invalid boolean"):
        load_settings(env={"SESSION_COOKIE_SECURE": "maybe"})


def test_custom_cookie_name_is_used() -> None:
    settings = load_settings(env={"SESSION_COOKIE_NAME": "custom_session"})
    assert settings.session_cookie_name == "custom_session"
