import functools
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


SkillTag = Literal[
    "reading-comprehension",
    "main-idea",
    "inference",
    "sequence",
    "summary",
    "vocabulary",
    "sentence-quality",
    "short-writing",
]

PassageType = Literal["literary", "informational", "poetry"]
QuestionType = Literal["multiple-choice", "short-response"]
DifficultyTier = Literal["easy", "medium", "difficult"]
ReviewStatus = Literal["reviewed", "draft", "rewrite-required"]

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
FRONTEND_CONTENT_DIR = REPO_ROOT / "frontend" / "src" / "content"

# backend/content/ is the canonical source. frontend/src/content/ is a
# checked-in mirror synced by scripts/sync-content.sh so the Next.js build
# can import the JSON at compile time. Drift between the two is caught by
# backend/tests/test_content_workflow.py.
CONTENT_DIR = BACKEND_CONTENT_DIR

ACTIVITIES_FILE = CONTENT_DIR / "activities.json"
SKILL_TAGS_FILE = CONTENT_DIR / "skill-tags.json"
THEMES_FILE = CONTENT_DIR / "themes.json"
MANIFEST_FILE = CONTENT_DIR / "MANIFEST.json"
REVIEW_STATUS_FILE = CONTENT_DIR / "review-status.json"
MIN_PASSAGE_SENTENCES = 8
MIN_PASSAGE_PARAGRAPHS = 2
MIN_PARAGRAPH_SENTENCES = 2
SETUP_CUES = (
    "needed to",
    "had to",
    "problem",
    "challenge",
    "question",
    "goal",
    "plan",
    "clue",
    "worried",
    "noticed",
    "task",
    "decided",
    "wanted",
    "tried",
    "began",
    "hoped",
    "set out",
    "wondered",
)
OUTCOME_CUES = (
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


class QuestionModel(BaseModel):
    id: str = Field(min_length=1)
    type: QuestionType
    prompt: str = Field(min_length=1)
    choices: Optional[list[str]] = None
    correctChoice: Optional[str] = None
    skillTag: Optional[SkillTag] = None
    writingSkillTags: list[SkillTag] = Field(default_factory=list)
    answerExplanation: Optional[str] = None
    responseGuidance: Optional[str] = None


class ActivityModel(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    difficulty: Optional[DifficultyTier] = None
    passageType: PassageType
    missionLabel: str = Field(min_length=1)
    passageTitle: str = Field(min_length=1)
    passageText: str = Field(min_length=1)
    questions: list[QuestionModel] = Field(min_length=2)
    skillTags: list[SkillTag] = Field(min_length=1)
    sourceUrls: list[str] = Field(default_factory=list)


class DeterministicWritingRubricModel(BaseModel):
    completion: str
    relevance: str
    sentence_completeness: str
    skill_specific_checks: list[str]


def _hash_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_content_manifest() -> dict:
    """Read MANIFEST.json. Raises ``ValueError`` if missing or malformed."""
    import json

    if not MANIFEST_FILE.exists():
        raise ValueError(f"Content manifest missing at {MANIFEST_FILE}.")
    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MANIFEST.json must be a JSON object.")
    if "content_version" not in data or "files" not in data:
        raise ValueError("MANIFEST.json must include content_version and files.")
    if not isinstance(data["files"], dict) or not data["files"]:
        raise ValueError("MANIFEST.json files entry must be a non-empty object.")
    return data


def verify_content_manifest() -> dict:
    """Return the manifest, raising ``ValueError`` if any file's checksum does
    not match the recorded value or any expected file is missing."""
    manifest = load_content_manifest()
    for name, expected in manifest["files"].items():
        file_path = CONTENT_DIR / name
        if not file_path.exists():
            raise ValueError(f"Manifest lists {name} but file is missing.")
        actual = _hash_file(file_path)
        if actual != expected:
            raise ValueError(
                f"Manifest checksum mismatch for {name}: "
                f"expected {expected[:12]}…, got {actual[:12]}…. "
                "Regenerate via python3 -m backend.app.content_cli manifest."
            )
    return manifest


def _count_sentences(text: str) -> int:
    import re

    return len([part for part in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ").strip()) if part])


def _count_paragraphs(text: str) -> int:
    import re

    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()])


def _split_paragraphs(text: str) -> list[str]:
    import re

    return [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]


def _count_sentences_in_block(text: str) -> int:
    return _count_sentences(text)


def _has_any_cue(text: str, cues: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def _apply_default_difficulties(activities: list[ActivityModel]) -> None:
    tiers: tuple[DifficultyTier, DifficultyTier, DifficultyTier] = ("easy", "medium", "difficult")
    sorted_activities = sorted(activities, key=lambda item: item.id)
    for index, activity in enumerate(sorted_activities):
        if activity.difficulty is None:
            activity.difficulty = tiers[index % len(tiers)]


def load_review_statuses() -> dict[str, ReviewStatus]:
    """Load the explicit editorial status for every canonical activity."""
    import json

    raw = json.loads(REVIEW_STATUS_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("review-status.json must be a JSON object.")
    allowed: tuple[ReviewStatus, ...] = ("reviewed", "draft", "rewrite-required")
    statuses: dict[str, ReviewStatus] = {}
    for status in allowed:
        ids = raw.get(status)
        if not isinstance(ids, list):
            raise ValueError(f'review-status.json needs a "{status}" array.')
        for activity_id in ids:
            if not isinstance(activity_id, str) or not activity_id:
                raise ValueError(f'review-status.json "{status}" entries must be non-empty strings.')
            if activity_id in statuses:
                raise ValueError(f'Duplicate review status for activity "{activity_id}".')
            statuses[activity_id] = status
    extra = sorted(set(raw) - set(allowed))
    if extra:
        raise ValueError(f"Unsupported review status groups: {', '.join(extra)}")
    return statuses


def load_seed_activities() -> list[ActivityModel]:
    import json

    allowed_themes = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    raw = json.loads(ACTIVITIES_FILE.read_text(encoding="utf-8"))
    activities = [ActivityModel.model_validate(item) for item in raw]
    statuses = load_review_statuses()
    reviewed_ids = {activity_id for activity_id, status in statuses.items() if status == "reviewed"}
    for activity in activities:
        if activity.id in reviewed_ids and activity.difficulty is None:
            raise ValueError(f'Reviewed activity "{activity.id}" needs explicit difficulty.')
    _apply_default_difficulties(activities)

    seen_ids: set[str] = set()
    for activity in activities:
        if activity.id in seen_ids:
            raise ValueError(f"Duplicate activity id: {activity.id}")
        seen_ids.add(activity.id)
        if activity.theme not in allowed_themes:
            raise ValueError(f'Activity "{activity.id}" has unsupported theme "{activity.theme}".')
        if activity.passageType == "poetry":
            lines = [line for line in activity.passageText.split("\n") if line.strip()]
            stanzas = [s.strip() for s in activity.passageText.split("\n\n") if s.strip()]
            if len(lines) < 8:
                raise ValueError(f'Poetry activity "{activity.id}" must include at least 8 lines.')
            if len(stanzas) < 2:
                raise ValueError(f'Poetry activity "{activity.id}" must include at least 2 stanzas.')
        else:
            if _count_sentences(activity.passageText) < MIN_PASSAGE_SENTENCES:
                raise ValueError(
                    f'Activity "{activity.id}" must include at least {MIN_PASSAGE_SENTENCES} sentences in passageText.'
                )
            if _count_paragraphs(activity.passageText) < MIN_PASSAGE_PARAGRAPHS:
                raise ValueError(
                    f'Activity "{activity.id}" must include at least {MIN_PASSAGE_PARAGRAPHS} paragraphs in passageText.'
                )
            paragraphs = _split_paragraphs(activity.passageText)
            if _count_sentences_in_block(paragraphs[0]) < MIN_PARAGRAPH_SENTENCES:
                raise ValueError(
                    f'Activity "{activity.id}" first paragraph must include at least {MIN_PARAGRAPH_SENTENCES} sentences.'
                )
            if _count_sentences_in_block(paragraphs[1]) < MIN_PARAGRAPH_SENTENCES:
                raise ValueError(
                    f'Activity "{activity.id}" second paragraph must include at least {MIN_PARAGRAPH_SENTENCES} sentences.'
                )
            if not _has_any_cue(paragraphs[0], SETUP_CUES):
                raise ValueError(f'Activity "{activity.id}" first paragraph must include setup/challenge context cues.')
            if not _has_any_cue(activity.passageText, OUTCOME_CUES):
                raise ValueError(f'Activity "{activity.id}" must include outcome/reflection cues in the passage.')

        for question in activity.questions:
            if question.skillTag is not None and question.skillTag not in activity.skillTags:
                raise ValueError(
                    f'Question "{question.id}" in activity "{activity.id}" uses skill tag '
                    f'"{question.skillTag}" that is not listed on the activity.'
                )
            if question.type == "multiple-choice":
                if question.choices is None or len(question.choices) < 2:
                    raise ValueError(
                        f'Multiple-choice question "{question.id}" in activity "{activity.id}" needs at least two choices.'
                    )
                if not question.correctChoice or question.correctChoice not in question.choices:
                    raise ValueError(
                        f'Multiple-choice question "{question.id}" in activity "{activity.id}" needs a valid correctChoice.'
                    )
            else:
                if question.choices:
                    raise ValueError(
                        f'Short-response question "{question.id}" in activity "{activity.id}" should not define choices.'
                    )
                if question.correctChoice:
                    raise ValueError(
                        f'Short-response question "{question.id}" in activity "{activity.id}" should not define correctChoice.'
                    )
            if question.type != "short-response" and question.writingSkillTags:
                raise ValueError(
                    f'Question "{question.id}" in activity "{activity.id}" may only define '
                    "writingSkillTags for a short response."
                )

    return activities


@functools.lru_cache(maxsize=1)
def list_seed_activities() -> tuple[ActivityModel, ...]:
    return tuple(load_seed_activities())


def list_seed_themes() -> list[str]:
    import json

    raw = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("themes.json must be a non-empty array.")
    parsed = [str(item) for item in raw if isinstance(item, str) and item.strip()]
    if len(parsed) != len(raw):
        raise ValueError("themes.json must include non-empty strings only.")
    if len(set(parsed)) != len(parsed):
        raise ValueError("themes.json contains duplicate values.")
    return parsed


def list_seed_difficulty_tiers() -> list[str]:
    return ["easy", "medium", "difficult"]


def get_seed_activity(activity_id: str) -> ActivityModel:
    for activity in list_seed_activities():
        if activity.id == activity_id:
            return activity
    raise ValueError(f'Activity "{activity_id}" not found.')
