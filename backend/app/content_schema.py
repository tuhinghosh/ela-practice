from pathlib import Path
import re
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


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _ensure_terminal_punctuation(sentence: str) -> str:
    stripped = sentence.strip()
    if not stripped:
        return stripped
    if stripped[-1] in ".!?":
        return stripped
    return f"{stripped}."


def _build_extension_sentences(activity: ActivityModel) -> list[str]:
    difficulty_guidance = {
        "easy": [
            "Try retelling each part in your own words before moving on.",
            "Look for one strong clue in each paragraph.",
        ],
        "medium": [
            "Pay attention to how details connect across different parts of the passage.",
            "Ask yourself what evidence best supports the author's key point.",
        ],
        "difficult": [
            "Notice both explicit details and implied meanings as the ideas develop.",
            "Compare multiple clues before deciding on the strongest interpretation.",
        ],
    }
    theme_bank: dict[str, list[str]] = {
        "nature": [
            "The setting includes patterns in plants, animals, and weather that help explain what happens.",
            "Small observations, like sounds or tracks, can reveal important clues about the environment.",
            "Writers often use nature details to show cause and effect in a clear way.",
            "A careful reader can connect habitat details to the choices characters or scientists make.",
            "Nature topics reward slow reading because key evidence is often spread across several lines.",
            "When you reread, notice which details describe change over time in the natural world.",
        ],
        "space": [
            "Space passages often use precise vocabulary, so context clues are especially helpful.",
            "Readers can track sequence carefully to understand how a mission or observation unfolds.",
            "Scientific examples in space texts usually support one central explanation.",
            "Descriptions of tools, charts, and signals can provide evidence for strong inferences.",
            "Good summaries in space topics include both the big idea and one supporting detail.",
            "As you read, connect each fact to the larger goal of exploration or discovery.",
        ],
        "community": [
            "Community texts show how different roles and responsibilities work together.",
            "One useful strategy is to track who does each job and why that job matters.",
            "Writers often include step-by-step actions to show how a service project succeeds.",
            "Look for evidence about teamwork, planning, and communication in public settings.",
            "A strong response explains both what people did and how it helped others.",
            "These passages often connect individual choices to wider community outcomes.",
        ],
        "sports": [
            "Sports passages often highlight decisions, timing, and teamwork rather than just final scores.",
            "Pay attention to sequence words to understand practice routines and game changes.",
            "A key clue may come from how players adjust strategy during a challenge.",
            "Strong inferences in sports texts usually combine actions with results.",
            "When summarizing, include both the team's goal and the method they used.",
            "Notice how effort, communication, and planning shape the outcome.",
        ],
        "mystery": [
            "Mystery passages reward close reading because clues are placed in different parts of the text.",
            "Readers should separate strong evidence from distracting details.",
            "A useful strategy is to ask what each clue suggests before jumping to a conclusion.",
            "Sequence matters in mysteries because order can reveal cause and effect.",
            "Good inferences come from combining at least two clear text clues.",
            "As you read, test your prediction and revise it when new evidence appears.",
        ],
        "history": [
            "History passages often compare past and present to explain why changes happened.",
            "Timelines and records can provide strong evidence for sequence and summary tasks.",
            "Look for details that show how people adapted tools, ideas, or systems over time.",
            "A strong historical inference connects specific evidence to a broader trend.",
            "When summarizing history text, include both key events and their significance.",
            "Rereading helps readers catch cause-and-effect links across different time points.",
        ],
        "ocean-weather": [
            "Weather and ocean texts often describe patterns that repeat across different situations.",
            "Watch for warning signs, measurements, and observations that support decisions.",
            "Sequence helps explain how conditions change from one stage to the next.",
            "Strong responses connect scientific details to practical safety or planning choices.",
            "A clear summary includes both the process and why it matters for people or places.",
            "As you read, notice how evidence in one sentence is explained in the next.",
        ],
        "arts": [
            "Arts passages often show how planning and revision improve final work.",
            "Look for vocabulary that describes creative choices and their effects.",
            "Writers may describe process steps to show how ideas become finished projects.",
            "Strong inferences in arts texts connect technique to outcome.",
            "A good summary includes both what was created and how it was improved.",
            "Careful reading helps identify why feedback and practice matter in creative work.",
        ],
        "friendship": [
            "Friendship passages often reveal character growth through small actions and dialogue.",
            "Look for clues that show feelings, trust, and problem solving between classmates.",
            "A strong inference can explain why one choice changed a relationship.",
            "Sequence helps readers see how conflicts are resolved over time.",
            "When summarizing, include both the challenge and the supportive action.",
            "These passages often teach social lessons through specific, realistic details.",
        ],
        "logic": [
            "Logic passages ask readers to connect clues in a careful, step-by-step way.",
            "One strong strategy is to check whether each new detail confirms or changes your idea.",
            "Sequence and precision are important because one small change can alter the solution.",
            "Good summaries of logic texts explain both the method and the final result.",
            "A useful inference should be supported by multiple clues, not a single guess.",
            "Rereading can help readers spot hidden patterns they missed on the first pass.",
        ],
    }
    base = theme_bank.get(activity.theme, theme_bank["nature"])
    guidance = difficulty_guidance.get(activity.difficulty or "medium", difficulty_guidance["medium"])
    seed = sum(ord(char) for char in activity.id)
    start = seed % len(base)
    ordered = [base[(start + offset) % len(base)] for offset in range(len(base))]
    return [*ordered, *guidance]


EDITORIALLY_CURATED_IDS = {
    "forest-friends",
    "bees-and-flowers",
    "river-map",
    "garden-helpers",
    "mountain-stream",
    "park-ranger-note",
    "moon-garden",
    "planet-parade",
    "satellite-clue",
    "rocket-rules",
    "star-map-helpers",
    "library-day",
    "mail-route",
    "bus-stop-safety",
    "clinic-visit",
    "recycling-team",
    "soccer-formation",
    "relay-race-steps",
    "swim-practice",
    "basketball-clue",
    "gym-fair-play",
    "locker-note",
    "cafeteria-clue",
    "museum-riddle",
    "library-map-mystery",
    "playground-code",
    "paper-bridge",
    "pattern-path",
    "logic-lunch-line",
    "maze-message",
}


def _build_editorial_continuations(activity: ActivityModel) -> list[str]:
    title = activity.title
    theme_bank: dict[str, list[str]] = {
        "nature": [
            f"In {title}, each observation adds another clue about how living systems work together.",
            "Small details in the setting reveal changes that are easy to miss at first glance.",
            "As the scene develops, cause-and-effect links become clearer through concrete examples.",
            "The final details highlight how careful attention leads to better understanding of nature.",
        ],
        "space": [
            f"In {title}, scientific tools and careful measurements guide each decision in the activity.",
            "The sequence of events shows how evidence builds over time instead of all at once.",
            "Each new detail supports the main explanation and helps remove weaker guesses.",
            "By the end, the key idea is reinforced through both observation and teamwork.",
        ],
        "community": [
            f"{title} shows how people with different roles solve shared problems step by step.",
            "The middle of the passage highlights planning, communication, and follow-through.",
            "Each action supports the next, so the results depend on cooperation across the group.",
            "The closing details emphasize practical impact on neighbors, classmates, or families.",
        ],
        "sports": [
            f"{title} focuses on strategy, communication, and timing rather than one big moment.",
            "As the events move forward, each adjustment changes how the team performs.",
            "The strongest clues come from linking decisions to outcomes on the field or court.",
            "The ending reinforces that smart teamwork can shift results even in close situations.",
        ],
        "mystery": [
            f"In {title}, each clue narrows the possibilities and rules out weaker ideas.",
            "The order of clues matters because later details make earlier details clearer.",
            "The passage rewards careful thinking by connecting scattered hints into one explanation.",
            "By the final lines, the mystery resolves through evidence rather than guesswork.",
        ],
        "history": [
            f"{title} highlights how change over time can be traced through clear evidence.",
            "The middle details connect earlier conditions to later improvements or adjustments.",
            "Historical clues become stronger when readers compare what stayed the same and what changed.",
            "The ending points to a broader lesson about adaptation, planning, or innovation.",
        ],
        "ocean-weather": [
            f"{title} shows how observations and timing can shape safe, smart decisions.",
            "Each stage in the passage adds evidence about changing environmental conditions.",
            "The process is easier to understand when details are connected in sequence.",
            "The final result demonstrates how preparation can reduce risk during real events.",
        ],
        "arts": [
            f"In {title}, progress comes from planning, revision, and thoughtful creative choices.",
            "The passage connects technique with outcome so readers can see why each step matters.",
            "Key details show how feedback or collaboration strengthens the final product.",
            "By the conclusion, the artistic goal is clearer because the process is fully explained.",
        ],
        "friendship": [
            f"{title} develops through small actions that build trust and understanding.",
            "The middle moments show how communication changes the tone between classmates.",
            "Each decision affects relationships, so details about feelings and responses are important.",
            "The final lines highlight growth, support, and shared success.",
        ],
        "logic": [
            f"{title} demonstrates that strong solutions come from checking each clue carefully.",
            "As the challenge continues, each step removes confusion and sharpens the pattern.",
            "The passage emphasizes method: test, revise, and verify before deciding.",
            "The ending confirms that reasoning works best when evidence is combined systematically.",
        ],
    }
    base = theme_bank.get(activity.theme, theme_bank["nature"])
    seed = sum(ord(ch) for ch in activity.id)
    start = seed % len(base)
    return [base[(start + idx) % len(base)] for idx in range(len(base))]


def _normalize_passage_text(activity: ActivityModel, min_sentences: int = 10, max_sentences: int = 15) -> None:
    sentences = _split_sentences(activity.passageText)
    if len(sentences) < min_sentences:
        if activity.id in EDITORIALLY_CURATED_IDS:
            extensions = _build_extension_sentences(activity)
        else:
            extensions = _build_editorial_continuations(activity) + _build_extension_sentences(activity)
        idx = 0
        while len(sentences) < min_sentences:
            sentences.append(extensions[idx % len(extensions)])
            idx += 1
    if len(sentences) > max_sentences:
        sentences = sentences[:max_sentences]
    activity.passageText = " ".join(_ensure_terminal_punctuation(sentence) for sentence in sentences)


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
    for activity in activities:
        _normalize_passage_text(activity)

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


def list_seed_difficulty_tiers() -> list[str]:
    return ["easy", "medium", "difficult"]


def get_seed_activity(activity_id: str) -> ActivityModel:
    for activity in load_seed_activities():
        if activity.id == activity_id:
            return activity
    raise ValueError(f'Activity "{activity_id}" not found.')
