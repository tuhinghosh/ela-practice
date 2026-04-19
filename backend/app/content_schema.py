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
DifficultyTier = Literal["easy", "medium", "difficult"]

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
)


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
    difficulty: Optional[DifficultyTier] = None
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


def load_seed_activities() -> list[ActivityModel]:
    import json

    allowed_themes = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    raw = json.loads(ACTIVITIES_FILE.read_text(encoding="utf-8"))
    activities = [ActivityModel.model_validate(item) for item in raw]
    _apply_default_difficulties(activities)

    seen_ids: set[str] = set()
    for activity in activities:
        if activity.id in seen_ids:
            raise ValueError(f"Duplicate activity id: {activity.id}")
        seen_ids.add(activity.id)
        if activity.theme not in allowed_themes:
            raise ValueError(f'Activity "{activity.id}" has unsupported theme "{activity.theme}".')
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


def list_seed_difficulty_tiers() -> list[str]:
    return ["easy", "medium", "difficult"]


def get_seed_activity(activity_id: str) -> ActivityModel:
    for activity in load_seed_activities():
        if activity.id == activity_id:
            return activity
    raise ValueError(f'Activity "{activity_id}" not found.')
