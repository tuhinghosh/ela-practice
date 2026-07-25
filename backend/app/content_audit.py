"""Deterministic quality gates for the reviewed content pool."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

from backend.app.content_schema import ActivityModel, ReviewStatus

MIN_REVIEWED_ACTIVITIES = 9
MIN_REVIEWED_PER_TIER = 3
MAX_ANSWER_POSITION_SHARE = 0.60
MIN_ANSWER_POSITIONS_USED = 3


@dataclass
class ContentAuditReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reviewed_count: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    tier_counts: dict[str, int] = field(default_factory=dict)
    answer_position_counts: dict[int, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.errors


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _passage_sentences(text: str) -> list[str]:
    flattened = text.replace("\n", " ")
    return [
        _normalized(sentence)
        for sentence in re.split(r"(?<=[.!?])\s+", flattened)
        if len(sentence.split()) >= 7
    ]


def _valid_source_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def audit_content(
    activities: Iterable[ActivityModel],
    statuses: dict[str, ReviewStatus],
) -> ContentAuditReport:
    activity_list = list(activities)
    report = ContentAuditReport()
    ids = {activity.id for activity in activity_list}

    missing = sorted(ids - statuses.keys())
    unknown = sorted(statuses.keys() - ids)
    if missing:
        report.errors.append(f"Activities missing review status: {', '.join(missing)}")
    if unknown:
        report.errors.append(f"Review registry contains unknown activities: {', '.join(unknown)}")

    report.status_counts = dict(sorted(Counter(statuses.values()).items()))
    reviewed = [activity for activity in activity_list if statuses.get(activity.id) == "reviewed"]
    report.reviewed_count = len(reviewed)
    if len(reviewed) < MIN_REVIEWED_ACTIVITIES:
        report.errors.append(
            f"Reviewed pool regressed to {len(reviewed)} activities; minimum is {MIN_REVIEWED_ACTIVITIES}."
        )

    tier_counts = Counter(activity.difficulty for activity in reviewed)
    report.tier_counts = {
        tier: int(tier_counts.get(tier, 0)) for tier in ("easy", "medium", "difficult")
    }
    for tier, count in report.tier_counts.items():
        if count < MIN_REVIEWED_PER_TIER:
            report.errors.append(
                f'Reviewed "{tier}" coverage regressed to {count}; minimum is {MIN_REVIEWED_PER_TIER}.'
            )

    answer_positions: Counter[int] = Counter()
    prompts: defaultdict[str, list[str]] = defaultdict(list)
    sentences: defaultdict[str, list[str]] = defaultdict(list)
    for activity in reviewed:
        if activity.difficulty is None:
            report.errors.append(f"{activity.id}: reviewed activity needs explicit difficulty.")
        if len(activity.questions) != 4:
            report.errors.append(f"{activity.id}: reviewed activity must have exactly four questions.")

        multiple_choice_count = 0
        short_response_count = 0
        for question in activity.questions:
            key = f"{activity.id}/{question.id}"
            prompts[_normalized(question.prompt)].append(key)
            if question.skillTag is None:
                report.errors.append(f"{key}: reviewed question needs a primary reading skill tag.")
            if question.type == "multiple-choice":
                multiple_choice_count += 1
                if not question.answerExplanation:
                    report.errors.append(f"{key}: multiple-choice question needs an answer explanation.")
                if question.choices and question.correctChoice in question.choices:
                    answer_positions[question.choices.index(question.correctChoice) + 1] += 1
            else:
                short_response_count += 1
                if not question.responseGuidance:
                    report.errors.append(f"{key}: short response needs response guidance.")
                if not question.writingSkillTags:
                    report.errors.append(f"{key}: short response needs separate writing skill tags.")

        if multiple_choice_count != 3 or short_response_count != 1:
            report.errors.append(
                f"{activity.id}: reviewed activity needs three multiple-choice and one short-response question."
            )
        if activity.passageType == "informational":
            if not activity.sourceUrls:
                report.errors.append(f"{activity.id}: reviewed informational passage needs sources.")
            for url in activity.sourceUrls:
                if not _valid_source_url(url):
                    report.errors.append(f"{activity.id}: source must be a valid HTTPS URL: {url}")
        for sentence in _passage_sentences(activity.passageText):
            sentences[sentence].append(activity.id)

    report.answer_position_counts = dict(sorted(answer_positions.items()))
    total_answers = sum(answer_positions.values())
    if total_answers:
        largest = max(answer_positions.values())
        if largest / total_answers > MAX_ANSWER_POSITION_SHARE:
            report.errors.append(
                "Correct-answer position is too predictable: "
                f"{largest}/{total_answers} ({largest / total_answers:.0%}) use one position; "
                f"maximum is {MAX_ANSWER_POSITION_SHARE:.0%}."
            )
        if len(answer_positions) < MIN_ANSWER_POSITIONS_USED:
            report.errors.append(
                f"Correct answers use only {len(answer_positions)} positions; "
                f"minimum is {MIN_ANSWER_POSITIONS_USED}."
            )
        ideal_max = math.ceil(total_answers / 4)
        if any(count > ideal_max for count in answer_positions.values()):
            report.warnings.append(
                "Answer positions pass the predictability gate but are not yet evenly balanced."
            )

    for prompt, locations in sorted(prompts.items()):
        if len(locations) > 1:
            report.warnings.append(
                f'Duplicate reviewed prompt "{prompt}" at {", ".join(locations)}.'
            )
    for sentence, activity_ids in sorted(sentences.items()):
        unique_ids = sorted(set(activity_ids))
        if len(unique_ids) > 1:
            report.errors.append(
                f'Duplicate reviewed passage sentence "{sentence}" in {", ".join(unique_ids)}.'
            )
    return report
