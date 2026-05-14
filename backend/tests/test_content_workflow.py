"""Tests for the canonical content store, manifest, and frontend sync.

These tests run on every commit and catch:
- Schema drift in seeded activities.
- Stale MANIFEST.json (forgot to ``content_cli manifest`` after an edit).
- Drift between backend/content (canonical) and frontend/src/content
  (mirror used by the Next.js build).
"""
import hashlib
import json
from pathlib import Path

import pytest

from backend.app.content_cli import cmd_validate, main
from backend.app.content_schema import (
    BACKEND_CONTENT_DIR,
    FRONTEND_CONTENT_DIR,
    MANIFEST_FILE,
    _hash_file,
    list_seed_activities,
    list_seed_themes,
    load_content_manifest,
    verify_content_manifest,
)


CANONICAL_FILENAMES = ("activities.json", "skill-tags.json", "themes.json")


def test_all_canonical_files_are_present() -> None:
    for name in CANONICAL_FILENAMES:
        assert (BACKEND_CONTENT_DIR / name).is_file(), f"missing canonical {name}"
    assert MANIFEST_FILE.is_file()


def test_load_seed_activities_validates_full_set() -> None:
    list_seed_activities.cache_clear()  # type: ignore[attr-defined]
    activities = list_seed_activities()
    assert len(activities) >= 50, "expected at least the documented MVP minimum"
    ids = [a.id for a in activities]
    assert len(set(ids)) == len(ids), "duplicate activity ids would have raised"


def test_every_activity_has_at_least_one_valid_skill_tag() -> None:
    for activity in list_seed_activities():
        assert activity.skillTags, f"{activity.id} has no skill tags"
        # SkillTag is a Literal — pydantic already enforces the allowed set.


def test_every_mc_question_has_correct_choice_in_choices() -> None:
    for activity in list_seed_activities():
        for question in activity.questions:
            if question.type == "multiple-choice":
                assert question.choices is not None and question.correctChoice in question.choices, (
                    f"{activity.id}/{question.id} correctChoice not in choices"
                )


def test_every_activity_theme_is_in_themes_file() -> None:
    themes = set(list_seed_themes())
    for activity in list_seed_activities():
        assert activity.theme in themes, f"{activity.id} theme {activity.theme!r} not allowed"


def test_manifest_checksums_match_canonical_files() -> None:
    verify_content_manifest()  # raises if drift


def test_manifest_includes_all_canonical_files() -> None:
    manifest = load_content_manifest()
    listed = set(manifest["files"].keys())
    assert listed == set(CANONICAL_FILENAMES), (
        f"manifest files {listed} do not match canonical {CANONICAL_FILENAMES}"
    )


def test_frontend_mirror_matches_backend_canonical() -> None:
    """If this fails, run scripts/sync-content.sh to refresh the frontend
    copy used by the Next.js bundler."""
    for name in CANONICAL_FILENAMES:
        backend_hash = _hash_file(BACKEND_CONTENT_DIR / name)
        frontend_hash = _hash_file(FRONTEND_CONTENT_DIR / name)
        assert backend_hash == frontend_hash, (
            f"{name}: backend and frontend copies differ — "
            "run scripts/sync-content.sh"
        )


def test_content_cli_validate_returns_zero_on_clean_state() -> None:
    code = main(["validate"])
    assert code == 0


def test_content_cli_validate_returns_one_when_manifest_drifts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corrupt the manifest in-place and confirm validate fails non-zero."""
    import backend.app.content_schema as schema_module

    fake_manifest = tmp_path / "MANIFEST.json"
    fake_manifest.write_text(
        json.dumps(
            {
                "content_version": "0.0.0",
                "files": {"activities.json": "deadbeef" * 8},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(schema_module, "MANIFEST_FILE", fake_manifest)
    import backend.app.content_cli as cli_module

    monkeypatch.setattr(cli_module, "MANIFEST_FILE", fake_manifest)

    code = main(["validate"])
    assert code == 1


def test_content_cli_manifest_writes_current_checksums(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use a throw-away manifest path so we do not rewrite the real one
    during tests, but exercise the real CLI code path."""
    import backend.app.content_schema as schema_module
    import backend.app.content_cli as cli_module

    target = tmp_path / "MANIFEST.json"
    monkeypatch.setattr(schema_module, "MANIFEST_FILE", target)
    monkeypatch.setattr(cli_module, "MANIFEST_FILE", target)

    assert main(["manifest"]) == 0

    written = json.loads(target.read_text(encoding="utf-8"))
    assert set(written["files"].keys()) == set(CANONICAL_FILENAMES)
    # Each recorded SHA matches the actual file.
    for name, sha in written["files"].items():
        expected = hashlib.sha256(
            (BACKEND_CONTENT_DIR / name).read_bytes()
        ).hexdigest()
        assert sha == expected
