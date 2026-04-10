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

PassageType = Literal["literary", "informational"]
QuestionType = Literal["multiple-choice", "short-response"]

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CONTENT_DIR = REPO_ROOT / "frontend" / "src" / "content"
BACKEND_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

if (BACKEND_CONTENT_DIR / "activities.json").exists():
    CONTENT_DIR = BACKEND_CONTENT_DIR
else:
    CONTENT_DIR = FRONTEND_CONTENT_DIR

ACTIVITIES_FILE = CONTENT_DIR / "activities.json"
SKILL_TAGS_FILE = CONTENT_DIR / "skill-tags.json"
THEMES_FILE = CONTENT_DIR / "themes.json"


class QuestionModel(BaseModel):
    id: str = Field(min_length=1)
    type: QuestionType
    prompt: str = Field(min_length=1)
    choices: Optional[list[str]] = None
    correctChoice: Optional[str] = None


class ActivityModel(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    passageType: PassageType
    missionLabel: str = Field(min_length=1)
    passageTitle: str = Field(min_length=1)
    passageText: str = Field(min_length=1)
    questions: list[QuestionModel] = Field(min_length=2)
    skillTags: list[SkillTag] = Field(min_length=1)


class DeterministicWritingRubricModel(BaseModel):
    completion: str
    relevance: str
    sentence_completeness: str
    skill_specific_checks: list[str]


def load_seed_activities() -> list[ActivityModel]:
    import json

    allowed_themes = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    raw = json.loads(ACTIVITIES_FILE.read_text(encoding="utf-8"))
    activities = [ActivityModel.model_validate(item) for item in raw]

    seen_ids: set[str] = set()
    for activity in activities:
        if activity.id in seen_ids:
            raise ValueError(f"Duplicate activity id: {activity.id}")
        seen_ids.add(activity.id)
        if activity.theme not in allowed_themes:
            raise ValueError(f'Activity "{activity.id}" has unsupported theme "{activity.theme}".')

        for question in activity.questions:
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

    return activities


def list_seed_activities() -> list[ActivityModel]:
    return load_seed_activities()


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


def get_seed_activity(activity_id: str) -> ActivityModel:
    for activity in load_seed_activities():
        if activity.id == activity_id:
            return activity
    raise ValueError(f'Activity "{activity_id}" not found.')
