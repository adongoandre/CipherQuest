"""Mission content package — plain data, independent of the ORM and HTTP layers."""

from app.content.key_rules import KEY_RULES, KEY_RULE_DESCRIPTIONS, apply_key_rule
from app.content.missions import (
    DEFAULT_SCORING,
    MINIMUM_TELLINGS,
    MISSION_DEFINITIONS,
    MissionDefinition,
    StoryDefinition,
    all_missions,
    build_mission,
    build_story_payload,
    validate_definition,
)

__all__ = [
    "DEFAULT_SCORING",
    "KEY_RULES",
    "KEY_RULE_DESCRIPTIONS",
    "MINIMUM_TELLINGS",
    "MISSION_DEFINITIONS",
    "MissionDefinition",
    "StoryDefinition",
    "all_missions",
    "apply_key_rule",
    "build_mission",
    "build_story_payload",
    "validate_definition",
]
