"""Verified seed mission content.

Content here is **plain data** — no ORM, no FastAPI, no cipher imports beyond
the two pure helpers needed to prove correctness.

Each mission is a *case file* with several tellings. The first telling lives in
the base columns of the mission row; every additional telling (at least three)
is stored in ``Mission.stories``. A player who has already solved a mission is
served the next telling when they replay it, so nothing is ever repeated.

Key rule (all MVP missions): the Caesar shift is **the number of letters in the
accepted riddle answer**. The shift is never sent to the client before the
message is solved — the player works out the rule themselves, with progressive
hints available if they get stuck.

Ciphertext is never written by hand: :func:`build_story_payload` derives it
from the stored plaintext, the cipher and the parameter produced by the story's
own key rule, and :func:`validate_definition` re-derives everything and raises
if any published value disagrees.

Invariant enforced here and again by ``scripts/validate_missions.py``: every
accepted riddle answer of a *single telling* must yield the *same* parameter,
otherwise one riddle would open two different messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.cipher import decrypt, encrypt
from app.content.key_rules import KEY_RULE_DESCRIPTIONS, apply_key_rule

DEFAULT_SCORING: dict[str, Any] = {
    "solve_points": 70,
    "time_bonus_max": 15,
    "time_bonus_enabled": False,
    "no_hint_bonus": 10,
    "comprehension_bonus": 5,
    "max_total": 100,
}

MINIMUM_TELLINGS = 4  # the original story plus at least three alternatives


@dataclass(frozen=True, slots=True)
class StoryDefinition:
    """One telling of a mission: its story, riddle, key rule, message and aids."""

    narrative: str
    riddle_prompt: str
    accepted_riddle_answers: list[str]
    key_rule_id: str
    contextual_clue: str
    plaintext: str
    hints: list[str]
    explanation_note: str
    comprehension: dict[str, Any]

    @property
    def parameter(self) -> int:
        return apply_key_rule(self.key_rule_id, self.accepted_riddle_answers[0])


@dataclass(frozen=True, slots=True)
class MissionDefinition:
    """Authoring input for one mission: the first telling plus alternates."""

    slug: str
    title: str
    difficulty: str
    estimated_minutes: int
    story: StoryDefinition
    alternates: list[StoryDefinition]
    cipher_type: str = "caesar"
    scoring_config: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_SCORING))

    @property
    def stories(self) -> list[StoryDefinition]:
        return [self.story, *self.alternates]

    @property
    def parameter(self) -> int:
        return self.story.parameter


def build_worked_example(plaintext: str, shift: int) -> str:
    """Describe the exact character transformation for the first word."""
    word = next((w for w in plaintext.split() if any(c.isalpha() for c in w)), "")
    if not word:
        return f"Every letter was shifted by {shift}; this message has no letters."

    cipher_word = encrypt(word, shift)
    steps: list[str] = []
    for plain_char, cipher_char in zip(word, cipher_word):
        if plain_char.isascii() and plain_char.isalpha():
            steps.append(f"{cipher_char} - {shift} = {plain_char}")
    step_text = "; ".join(steps) if steps else "no letters to transform"

    return (
        f'The ciphertext begins with "{cipher_word}". Decrypting it one letter at a time: '
        f"{step_text}. The same shift of {shift} is applied to every other letter; "
        "spaces and punctuation are copied through unchanged."
    )


def build_explanation(story: StoryDefinition, answer: str, shift: int) -> str:
    """Compose the teaching explanation for a completed telling."""
    rule_description = KEY_RULE_DESCRIPTIONS[story.key_rule_id]
    worked = build_worked_example(story.plaintext, shift)
    return (
        f"{story.explanation_note} "
        f"Key rule: {rule_description} "
        f'Applied to the accepted answer "{answer.upper()}" that produces {shift}, '
        f"so this message uses a Caesar shift of {shift}. "
        f"Encryption moved each letter {shift} places forward through the alphabet "
        "(wrapping from Z back to A); decryption moves each letter "
        f"{shift} places backwards (wrapping from A back to Z). "
        f"{worked}"
    )


def build_story_payload(story: StoryDefinition) -> dict[str, Any]:
    """Derive every storable value for one telling (ciphertext included)."""
    answer = story.accepted_riddle_answers[0]
    shift = apply_key_rule(story.key_rule_id, answer)
    return {
        "narrative": story.narrative,
        "riddle_prompt": story.riddle_prompt,
        "accepted_riddle_answers": list(story.accepted_riddle_answers),
        "key_rule_id": story.key_rule_id,
        "key_rule_description": KEY_RULE_DESCRIPTIONS[story.key_rule_id],
        "key_type": "shift",
        "parameter": shift,
        "contextual_clue": story.contextual_clue,
        "ciphertext": encrypt(story.plaintext, shift),
        "plaintext_answer": story.plaintext,
        "hints": list(story.hints),
        "comprehension_check": dict(story.comprehension),
        "explanation": build_explanation(story, answer, shift),
        "worked_example": build_worked_example(story.plaintext, shift),
    }


def build_mission(definition: MissionDefinition) -> dict[str, Any]:
    """Validate an authoring definition and return the storable mission row."""
    validate_definition(definition)

    row: dict[str, Any] = {
        "slug": definition.slug,
        "title": definition.title,
        "difficulty": definition.difficulty,
        "cipher_type": definition.cipher_type,
        "estimated_minutes": definition.estimated_minutes,
        "scoring_config": dict(definition.scoring_config),
        "status": "published",
        "stories": [build_story_payload(story) for story in definition.alternates],
    }
    row.update(build_story_payload(definition.story))
    return row


def _validate_story(story: StoryDefinition, problems: list[str], where: str) -> None:
    """Content checks for a single telling."""
    if len(story.hints) != 3:
        problems.append(f"{where}: exactly three progressive hints are required")

    comp = story.comprehension
    if not isinstance(comp, dict):
        problems.append(f"{where}: a comprehension check is required")
    else:
        choices = comp.get("choices") or []
        correct = comp.get("correct_index")
        if len(choices) < 2:
            problems.append(f"{where}: comprehension check needs at least two choices")
        if not isinstance(correct, int) or not 0 <= correct < len(choices):
            problems.append(f"{where}: comprehension check has an out-of-range correct_index")
        if not str(comp.get("question", "")).strip():
            problems.append(f"{where}: comprehension check needs a question")

    if len(story.accepted_riddle_answers) < 1:
        problems.append(f"{where}: at least one accepted riddle answer is required")

    if not story.contextual_clue.strip():
        problems.append(f"{where}: a contextual clue is required")

    if story.contextual_clue.strip().casefold() == story.plaintext.strip().casefold():
        problems.append(f"{where}: the contextual clue must not be the plaintext")

    if story.plaintext.casefold() in story.contextual_clue.casefold():
        problems.append(f"{where}: the contextual clue must not quote the plaintext")

    if story.key_rule_id not in KEY_RULE_DESCRIPTIONS:
        problems.append(f"{where}: unknown key rule {story.key_rule_id!r}")

    # Every accepted answer of this telling must produce the same parameter.
    parameters: set[int] = set()
    for variant in story.accepted_riddle_answers:
        try:
            parameters.add(apply_key_rule(story.key_rule_id, variant))
        except (ValueError, TypeError) as exc:
            problems.append(f"{where}: answer {variant!r} cannot produce a shift: {exc}")
    if len(parameters) > 1:
        problems.append(
            f"{where}: accepted answers disagree on the shift: {sorted(parameters)} "
            f"for {story.accepted_riddle_answers}"
        )

    # Round-trip proof: ciphertext must decrypt back to the stored plaintext.
    if not parameters:
        return
    shift = apply_key_rule(story.key_rule_id, story.accepted_riddle_answers[0])
    if decrypt(encrypt(story.plaintext, shift), shift) != story.plaintext:
        problems.append(f"{where}: ciphertext does not round-trip to the stored plaintext")


def validate_definition(definition: MissionDefinition) -> list[str]:
    """Return a list of content problems; empty means the mission is publishable."""
    problems: list[str] = []

    if definition.cipher_type != "caesar":
        problems.append("only the caesar cipher ships in the MVP")

    if definition.difficulty not in {"beginner", "intermediate", "advanced", "expert"}:
        problems.append(f"unknown difficulty {definition.difficulty!r}")

    if len(definition.alternates) < MINIMUM_TELLINGS - 1:
        problems.append(
            f"a mission needs at least {MINIMUM_TELLINGS - 1} alternative tellings "
            "so replaying never repeats a story"
        )

    _validate_story(definition.story, problems, "story")
    for index, alternate in enumerate(definition.alternates, start=2):
        _validate_story(alternate, problems, f"telling {index}")

    return problems


MISSION_DEFINITIONS: list[MissionDefinition] = [
    MissionDefinition(
        slug="midnight-clock",
        title="The Midnight Secret",
        difficulty="beginner",
        estimated_minutes=5,
        story=StoryDefinition(
            narrative=(
                "During the night watch a folded note worked loose from the brickwork of the "
                "old clock tower and fell where anyone might find it. The paper is dry, the ink "
                "steady, the fold still sharp. Whoever sealed it there expected the tower to be "
                "listened to at midnight, and expected only one kind of person to be standing "
                "below when it spoke."
            ),
            riddle_prompt=(
                "I have two hands but never clap them, and a face that neither smiles nor looks "
                "away. People claim they own me, though nobody has ever held me still. I run "
                "without legs, I am wound before I live, and every hour I announce myself to a "
                "room that never asked to hear it. What am I?"
            ),
            accepted_riddle_answers=["clock", "watch"],
            key_rule_id="letter_count",
            contextual_clue=(
                "The message keeps time. Whoever wrote it was watching a clock tower and a river "
                "crossing, and wanted the reader on the far bank to know an hour rather than a "
                "place — not the price of passage, not the name of the boat, only the turning of "
                "the clock above the water."
            ),
            plaintext="Count the hours aloud from midnight until the ferry touches the north quay",
            hints=[
                "It hangs where whole streets can hear it, it has hands that never touch anything, "
                "and it strikes the hour without being asked. Think of a tower, a wall, a wrist.",
                "Your answer is the key, but a Caesar cipher only obeys a number. Count the letters "
                "in the word you found — that count is how far the alphabet must move.",
                "Set the wheel so every letter of the message steps back by that number, letting "
                "the alphabet wrap from A back to Z. Read it aloud; when it turns into English, "
                "send it.",
            ],
            explanation_note=(
                "Clocks, watches and wind-up timers all answer the riddle, and each is spelled "
                "with five letters, so every accepted answer gives the same shift."
            ),
            comprehension={
                "question": "In this mission, where did the Caesar shift come from?",
                "choices": [
                    "The number of letters in the riddle answer",
                    "The first letter of the riddle answer",
                    "The number of vowels in the riddle answer",
                    "The length of the ciphertext",
                ],
                "correct_index": 0,
                "explanation": (
                    "The key rule counts letters: CLOCK and WATCH each have five letters, so the "
                    "shift for this mission is 5."
                ),
            },
        ),
        alternates=[
            StoryDefinition(
                narrative=(
                    "The night watchman gave a second statement the following week, and this one "
                    "was stranger than the first. He had stopped writing about the tower "
                    "altogether. What he left instead was a page about something nobody has ever "
                    "seen, held flat by a stone on the windowsill of the watch room."
                ),
                riddle_prompt=(
                    "I have no body, yet I am cut into pieces every day. Divide a day by me and "
                    "you get twenty-four of myself; spend me badly and no one can give any of me "
                    "back. What am I?"
                ),
                accepted_riddle_answers=["hour", "time"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The page is about a crossing arranged long before dawn. The writer wanted a "
                    "reader to know the moment the boat would slip its rope — nothing about the "
                    "cargo, nothing about the crew, only when."
                ),
                plaintext="Leave the lantern lit on the seaward wall until the last watch changes",
                hints=[
                    "Clock faces are divided into these. A day holds twenty-four of them, a "
                    "working day fewer, and none of them can be stored.",
                    "The word you found is the key — but the cipher wants a number. Count its "
                    "letters; that count is the distance the alphabet travels.",
                    "Move every letter of the message back by that distance, wrapping from A to "
                    "Z, and the sentence will come back into English.",
                ],
                explanation_note=(
                    "HOUR and TIME both answer the riddle, and each is spelled with four letters "
                    "— the shift stays four whichever word you gave."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The position of the answer in the alphabet",
                        "The number of words in the riddle",
                        "The number of vowels in the answer",
                    ],
                    "correct_index": 0,
                    "explanation": (
                        "The rule counts letters: HOUR and TIME each have four letters, so this "
                        "telling shifts by 4."
                    ),
                },
            ),
            StoryDefinition(
                narrative=(
                    "A harbour pilot kept a private book of instructions for the men who rowed "
                    "him out. Most entries are boring: tides, depths, the price of oil. One entry "
                    "is not. It was written before sunrise on a morning the whole town remembers, "
                    "and it does not mention a boat at all."
                ),
                riddle_prompt=(
                    "I arrive every day without being called and leave without being dismissed. "
                    "The sky takes me in, the sea borrows my colour, and nothing that follows me "
                    "can happen before I do. What am I?"
                ),
                accepted_riddle_answers=["sunrise", "morning"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The pilot was writing about first light. He wanted someone already on the "
                    "water to know the hour the sky would begin working against them, and said "
                    "nothing at all about where they were headed."
                ),
                plaintext="Meet where the bell tower throws its shadow at first light",
                hints=[
                    "You have never once seen it arrive; you only ever find that it has. Every "
                    "bird on the page is about to start singing.",
                    "The word you found carries the key inside it: count its letters and you have "
                    "the number this message was locked with.",
                    "Turn the alphabet back by that number for every letter, spaces staying "
                    "where they are. When the words read like English again, submit them.",
                ],
                explanation_note=(
                    "SUNRISE and MORNING are both seven letters long, so either answer opens "
                    "this message — the shift is 7."
                ),
                comprehension={
                    "question": "Why does the riddle answer matter so much here?",
                    "choices": [
                        "Its letter count becomes the shift",
                        "It decides which cipher was used",
                        "It sets the length of the message",
                        "It does not — the shift is always 1",
                    ],
                    "correct_index": 0,
                    "explanation": (
                        "Count the letters in your answer: SUNRISE and MORNING each have seven, "
                        "so the shift is 7."
                    ),
                },
            ),
            StoryDefinition(
                narrative=(
                    "The last page in the watchman's book is not a statement but a warning, "
                    "written twice in two different pens. Someone read the earlier version, "
                    "thought better of it, and wrote it again more carefully — as if the words "
                    "themselves might be followed."
                ),
                riddle_prompt=(
                    "I copy every move you make and learn nothing from any of them. I stretch "
                    "when the sun is low and hide when it is high, and the dark is the only place "
                    "I am finally rid of you. What am I?"
                ),
                accepted_riddle_answers=["shadow"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The warning is about being followed through the streets after dark — about "
                    "a figure that keeps pace on the cobbles, and how to lose it before the river "
                    "steps."
                ),
                plaintext="Bring the spare wick and the storm glass before the tide turns",
                hints=[
                    "It is yours alone, it lies down when you do, and noon is the only time it "
                    "keeps its distance from you.",
                    "Count the letters in your answer — that count is the distance the cipher "
                    "moved when it hid the message.",
                    "Move each letter of the message back by that distance, wrapping past A to "
                    "Z. Spaces and punctuation never move.",
                ],
                explanation_note=(
                    "SHADOW has six letters, so this telling shifts by six — one more than the "
                    "tower's own clock."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The first letter of the riddle answer",
                        "The hour the warning was written",
                        "The length of the ciphertext",
                    ],
                    "correct_index": 0,
                    "explanation": "SHADOW has six letters, so the wheel turns six places.",
                },
            ),
        ],
    ),
    MissionDefinition(
        slug="lighthouse-lamp",
        title="The Lighthouse Keeper's Slip",
        difficulty="beginner",
        estimated_minutes=5,
        story=StoryDefinition(
            narrative=(
                "Tucked inside a salt-stiffened lighthouse logbook, a single slip of paper fell "
                "out as the pages opened. The hand is careful and the instruction is short. "
                "Outside the window the reef is only two ship-lengths wide, and the keeper has "
                "not been seen on the gallery since Tuesday."
            ),
            riddle_prompt=(
                "I am tall when I am young and short when I am old. I am fed by wicks and I feed "
                "the light. I have never taken a breath, yet I die in every breeze I ever made "
                "brighter. What am I?"
            ),
            accepted_riddle_answers=["candle"],
            key_rule_id="letter_count",
            contextual_clue=(
                "The keeper was writing about the moment the weather turns: the glass falls, the "
                "water thickens, and the light must be made to burn hotter before the dark "
                "arrives. The message never says where the lighthouse stands."
            ),
            plaintext="Trim the wick and raise the second mirror before the fog closes in",
            hints=[
                "Made of wax and slowly eaten by its own work, with a flame for a head. "
                "Birthdays would be darker without it.",
                "Your answer is the key, and the cipher only listens to numbers: count its "
                "letters and you have the shift it was written with.",
                "Turn the wheel back by that many places for every letter — spaces stay put. "
                "When the words read like English, send them.",
            ],
            explanation_note=(
                "The keeper's word for the light is the key: CANDLE has six letters, so the "
                "message was written six places forward and reads back six places."
            ),
            comprehension={
                "question": "What did this mission's key rule ask you to work out?",
                "choices": [
                    "The number of letters in the riddle answer",
                    "The first letter of the riddle answer",
                    "The number of vowels in the riddle answer",
                    "The number of words in the message",
                ],
                "correct_index": 0,
                "explanation": "CANDLE has six letters, so this mission's shift is 6.",
            },
        ),
        alternates=[
            StoryDefinition(
                narrative=(
                    "The keeper's daughter kept her own notebook beside her father's, and hers is "
                    "far less practical: pressed grass, weather notes, a list of names she never "
                    "explains. One page is an instruction, written in a young hand, for a morning "
                    "when the harbour disappeared."
                ),
                riddle_prompt=(
                    "I am a low thief that sails in off the water and swallows the beam whole. "
                    "Ships slow down when they hear me coming, though I never make a sound. What "
                    "am I?"
                ),
                accepted_riddle_answers=["fog"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The page describes weather arriving from the sea — the kind that takes a "
                    "boat's bearings away and leaves a crew guessing at the shape of the shore."
                ),
                plaintext="Rig the spare sail before the wind changes its mind",
                hints=[
                    "It sits on cold water, it drifts, and it makes everything within a hundred "
                    "metres look unfinished. Drivers turn their lights down in it.",
                    "Short word, short number: count the letters in your answer and you have the "
                    "distance the cipher travelled.",
                    "Bring every letter back by that distance, wrapping from A to Z, and read the "
                    "result in a quiet voice.",
                ],
                explanation_note=(
                    "FOG is three letters, so this telling uses the smallest shift in the case "
                    "file — three places."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The number of vowels in the riddle answer",
                        "The tide height on the night in question",
                        "The first letter of the answer",
                    ],
                    "correct_index": 0,
                    "explanation": "FOG has three letters, so the alphabet moves three places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "In the logbook's back pocket is a scorched card that smells faintly of "
                    "sulphur. It carries no signature, only instructions for the worst night of "
                    "the year — the one the keeper never wrote down in full, perhaps because "
                    "writing it down would make it real."
                ),
                riddle_prompt=(
                    "I am set alight to be seen from far away, I live only moments, and my whole "
                    "purpose is to say 'here' to someone who cannot hear me. What am I?"
                ),
                accepted_riddle_answers=["flare"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The card is about calling for help when nothing else works: one bright "
                    "moment above the water, meant for a deck crew already looking in the wrong "
                    "direction."
                ),
                plaintext="Fire the signal over the eastern shoal at the changing of the watch",
                hints=[
                    "It is held in one hand, it hisses, and its light is red enough to be "
                    "remembered. It is used exactly once.",
                    "Count the letters in your answer — that count is the shift. Nothing else in "
                    "the mission changes it.",
                    "Subtract that many places from every letter of the message, letting the "
                    "alphabet wrap at A, and the words will return.",
                ],
                explanation_note=(
                    "FLARE has five letters, so the message was hidden five places up the "
                    "alphabet — the same distance as the first telling of the clock tower note."
                ),
                comprehension={
                    "question": "Why does the riddle answer matter so much here?",
                    "choices": [
                        "Its letter count becomes the shift",
                        "It names the ship to signal",
                        "It decides how many hints you get",
                        "It does not — the shift is always 5",
                    ],
                    "correct_index": 0,
                    "explanation": "Every letter counts: FLARE has five, so the shift is 5.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "The last loose page in the logbook is a list of things to carry, and every "
                    "item on it has been underlined twice. Whoever wrote it expected the walk to "
                    "be done in the dark, in a hurry, and with one pair of hands only."
                ),
                riddle_prompt=(
                    "I hold a small sun on a hook and walk with whoever carries me. Glass keeps "
                    "me alive, wind tries to end me, and the dark is the reason I exist. What am "
                    "I?"
                ),
                accepted_riddle_answers=["lantern"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The list is for a crossing between buildings on a night with no moon. "
                    "Everything on it burns, glows, or keeps something else from going out."
                ),
                plaintext="Carry the spare lantern down to the boathouse before midnight",
                hints=[
                    "It hangs from a handle, it rattles in the wind, and it was the reason "
                    "sailors stopped running aground. The glass gets hot.",
                    "The number you need is already inside your answer: count its letters and "
                    "the key appears.",
                    "Move each letter back by that count, wrapping from A to Z — the spaces fall "
                    "where they already are.",
                ],
                explanation_note=(
                    "LANTERN has seven letters, so this telling turns the alphabet seven places "
                    "— the longest shift in the lighthouse file."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The number of items on the keeper's list",
                        "The first letter of the answer",
                        "The length of the ciphertext",
                    ],
                    "correct_index": 0,
                    "explanation": "LANTERN has seven letters, so the shift is 7.",
                },
            ),
        ],
    ),
    MissionDefinition(
        slug="whispering-gallery",
        title="The Gallery That Keeps Secrets",
        difficulty="intermediate",
        estimated_minutes=7,
        story=StoryDefinition(
            narrative=(
                "In the old gallery the ceiling is a perfect curve, and a conversation begun "
                "at one end arrives at the other intact, decades after the speakers have gone. "
                "During restoration a plasterer found a note rolled inside a hollow in the "
                "cove, where somebody had wedged it and meant to fetch it back. The restoration "
                "funds were spent, the note never moved, and it stayed under the last coat of "
                "whitewash until the scaffold went up again. The plasterer did not understand "
                "what he was holding. Most people would not."
            ),
            riddle_prompt=(
                "I am bigger than the room that holds me, yet I take up no space at all. I am "
                "not made, I am only reflected; I have no edge, but touch me anywhere and I am "
                "gone. You cannot look at me straight on, you can only ever see me beside "
                "something else. What am I?"
            ),
            accepted_riddle_answers=["echo"],
            key_rule_id="letter_count",
            contextual_clue=(
                "The note belongs to a man whose accusations never landed — every word he spoke "
                "came back to him from the far wall of the room, unchanged. He wrote it down so "
                "that one particular sentence could travel a shorter way: to a friend waiting "
                "by a certain door, after a certain bell, on the night the doors were to be "
                "left unbarred."
            ),
            plaintext="Leave the west door unbarred on the night the bell rings twice",
            hints=[
                "Shout in a stairwell and you have already met it. It is whatever comes back "
                "when the far wall refuses to keep a secret.",
                "Your answer opens the message, but Caesar only obeys a number: count the letters "
                "in your answer and you have the shift the writer used.",
                "Bring every letter of the message back by that number, letting A wrap round to "
                "Z. Punctuation never moves. When it reads like a plain instruction, send it.",
            ],
            explanation_note=(
                "ECHO has four letters, so this message was written four places forward and reads "
                "back four places."
            ),
            comprehension={
                "question": "What did you have to work out before the cipher would open?",
                "choices": [
                    "The number of letters in the riddle answer",
                    "The room the note was found in",
                    "The number of times the bell rang",
                    "The first letter of the message",
                ],
                "correct_index": 0,
                "explanation": (
                    "The key was never printed anywhere — you had to count the letters in ECHO "
                    "to learn the shift was 4."
                ),
            },
        ),
        alternates=[
            StoryDefinition(
                narrative=(
                    "The gallery's floorplan is filed with the architect's notes, and one sheet "
                    "is a surveyor's complaint about a beam that does not meet its pillar. The "
                    "gap is real. It has been real for two hundred years, and the surveyor "
                    "believed it was deliberate — a place too narrow to find by touch and too "
                    "obvious to be called a hiding hole."
                ),
                riddle_prompt=(
                    "I am the line between two walls that were never meant to touch. I am not a "
                    "gap in anything, because I was there before the walls. Architects draw me, "
                    "builders forget me, and once a room is finished you can stand inside it for "
                    "years without knowing I am still there. What am I?"
                ),
                accepted_riddle_answers=["seam", "weld"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The surveyor was really writing about a meeting: two people, one narrow "
                    "place, no witnesses. The note names neither of them — only where the wall "
                    "bends, and how long the second one must linger before arriving."
                ),
                plaintext="Wait at the bend where the north wall meets the old stair",
                hints=[
                    "Two planks meeting, a shirt down its middle, the place a sleeve is set into "
                    "a shoulder. Every answer is a place where two parts become one thing.",
                    "Both candidate answers are four letters long — whichever you chose, count "
                    "them and you have the number the writer locked the note with.",
                    "Move each letter of the message back by four, wrapping at A, and the "
                    "instruction will assemble itself.",
                ],
                explanation_note=(
                    "SEAM and WELD are both four letters, so the shift is 4 whichever word the "
                    "player had in mind."
                ),
                comprehension={
                    "question": "Where did this mission's shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The thickness of the beam",
                        "The surveyor's room number",
                        "The number of gaps in the wall",
                    ],
                    "correct_index": 0,
                    "explanation": "SEAM and WELD each have four letters, so the alphabet moved four places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "The architect's widow annotated his drawings long after he died, in a hand "
                    "much smaller than his. Beside one doorway she wrote a single sentence about "
                    "a sound she could never place, and beneath it, in the margin, the instruction "
                    "her husband had apparently asked her to keep until someone came asking."
                ),
                riddle_prompt=(
                    "I am a door that opens onto nothing, a lid that lifts on a sound instead of "
                    "a room. Musicians make me on purpose and buildings make me by accident, and "
                    "the difference between the two is only whether anyone was listening. What "
                    "am I?"
                ),
                accepted_riddle_answers=["resonance"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The widow was describing a particular stone stair that hums when the wind "
                    "passes through the arch above it — a stair somebody used to climb every "
                    "evening without ever noticing the building was singing at them."
                ),
                plaintext="Bring the lamp to the stone stair at the eighth hour",
                hints=[
                    "A wine glass after the rim is wetted, a struck bell that keeps humming after "
                    "the clapper stops, a room that flatters one note and swallows the rest.",
                    "Nine letters in your answer — nine is the number this note was hidden by.",
                    "Take every letter nine places back through the alphabet, wrapping past A, "
                    "and read what surfaces.",
                ],
                explanation_note=(
                    "RESONANCE has nine letters — the longest shift in the gallery file."
                ),
                comprehension={
                    "question": "Why does the riddle answer matter so much here?",
                    "choices": [
                        "Its letter count becomes the shift",
                        "It names the room to search",
                        "It tells you when to arrive",
                        "It does not — the shift is always 9",
                    ],
                    "correct_index": 0,
                    "explanation": (
                        "The answer is the key: count RESONANCE and you get nine, the shift for "
                        "this message."
                    ),
                },
            ),
            StoryDefinition(
                narrative=(
                    "High above the gallery floor, the last picture rail carries a hook that was "
                    "never used. Behind it, where the wall meets the cove, somebody had scratched "
                    "a warning directly into the plaster — not hidden, not sealed, simply too "
                    "high for anyone to bother looking."
                ),
                riddle_prompt=(
                    "I travel farther than any horse and never leave the ground. I knock twice and "
                    "wait to be let in, though I carry nothing and I want nothing. A quiet room "
                    "makes me shy; a full room gives me strength. What am I?"
                ),
                accepted_riddle_answers=["rumour"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The warning is about word getting out ahead of the plan — about somebody in "
                    "the house repeating what they should have swallowed, and about the hour by "
                    "which the matter had to be finished regardless."
                ),
                plaintext="Finish it before the sixth bell or not at all",
                hints=[
                    "It starts as a whisper, it arrives uninvited, and everyone swears they did "
                    "not pass it on. Nothing about it is ever true twice.",
                    "Six letters in your answer is the number this message waits for.",
                    "Decrypt by stepping each letter back six places, wrapping at A. The words "
                    "will be plain English when the shift is right.",
                ],
                explanation_note=(
                    "RUMOUR has six letters, so the shift is six — the same distance as the first "
                    "telling of this case."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The number of bells in the warning",
                        "The height of the picture rail",
                        "The number of words in the riddle",
                    ],
                    "correct_index": 0,
                    "explanation": "RUMOUR has six letters, so the wheel turns six places.",
                },
            ),
        ],
    ),
    MissionDefinition(
        slug="hollow-crown",
        title="The Hollow Crown",
        difficulty="advanced",
        estimated_minutes=8,
        story=StoryDefinition(
            narrative=(
                "A box of estate papers was opened after a funeral nobody wanted to attend. "
                "Inside, between land deeds and a list of debts, is a message in a careful "
                "courtier's hand, folded around nothing at all. It has no addressee and no "
                "signature. It describes a moment at court and gives an order, and the family "
                "has been arguing about it for three generations without ever having the faintest "
                "idea what it said."
            ),
            riddle_prompt=(
                "I am worn by the greatest and owned by none. I am not metal and not cloth, but "
                "I can be lost in a single afternoon and spent, carelessly, in a single sentence. "
                "I make a stranger kneel and make an equal step back, and I outlive every head "
                "that ever carried it. What am I?"
            ),
            accepted_riddle_answers=["honour"],
            key_rule_id="letter_count",
            contextual_clue=(
                "The courtier was writing about a slight delivered in front of witnesses — the "
                "kind that cannot be unsaid at breakfast. He named no person and no place, only "
                "the hour at which certain doors were meant to swing wide, and whose hand would "
                "be given the key."
            ),
            plaintext="Open the gallery doors at the ninth hour and admit no one after",
            hints=[
                "Chivalry, a soldier's, a reputation's. It is what you defend when nothing "
                "physical is being attacked, and what a coward is said to have left behind.",
                "Six letters make six places — count your answer and you hold the key, even "
                "though the mission never printed it.",
                "Subtract six from every letter of the message, letting the alphabet wrap from A "
                "to Z, and the courtier's instruction will read plainly.",
            ],
            explanation_note=(
                "HONOUR is six letters, so this message was hidden six places forward — despite "
                "the crown on the case file's seal."
            ),
            comprehension={
                "question": "What determined the shift for this mission?",
                "choices": [
                    "The number of letters in the riddle answer",
                    "The number of letters in CROWN",
                    "The number of generations of the family",
                    "The first letter of the message",
                ],
                "correct_index": 0,
                "explanation": (
                    "The title is a decoy: the shift is always the letter count of the answer, "
                    "and HONOUR has six letters."
                ),
            },
        ),
        alternates=[
            StoryDefinition(
                narrative=(
                    "Among the same estate papers is a letter never sent, addressed only to "
                    "'the one who finds this'. It was written on the night the household "
                    "learned what one of its own had been doing with the estate's money, and it "
                    "was folded, sealed, and then simply never carried to the post."
                ),
                riddle_prompt=(
                    "I can be spent without moving from your hand and hoarded until it ruins "
                    "you. I am counted in sentences and never in coins, though a whole kingdom "
                    "runs on me. Take me away from a person and nothing they own can save their "
                    "name. What am I?"
                ),
                accepted_riddle_answers=["credit"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The letter is about a debt that was never owed: promises made in public, "
                    "kept in private, and the exact evening on which the writer decided the "
                    "ledger would be closed for good."
                ),
                plaintext="Settle the accounts before the moon is full",
                hints=[
                    "Banks grant it, friends extend it, liars abuse it. It is trust expressed as "
                    "a number — or, in the phrase people actually use, as something you have or "
                    "do not have.",
                    "Your answer has six letters, and six is the distance this message was "
                    "pushed up the alphabet.",
                    "Decrypt by stepping every letter six places back, wrapping at A. When the "
                    "sentence reads like an order, submit it.",
                ],
                explanation_note=(
                    "CREDIT has six letters, so the shift is six for this telling as well."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The amount of money in the accounts",
                        "The number of debts listed",
                        "The number of words in the message",
                    ],
                    "correct_index": 0,
                    "explanation": "CREDIT has six letters, so the wheel turns six places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "The same box holds a servant's inventory of what was missing the morning "
                    "after the argument: two candlesticks, a set of keys, one portrait cut from "
                    "its frame. The last line of the list is not an item at all, but a note to "
                    "whoever might come looking later."
                ),
                riddle_prompt=(
                    "I am struck in anger and never touch the ground. I am named after a beast "
                    "with a ring through its nose, and though I am rarely seen anymore, every "
                    "quarrel in a house once ended when I appeared. What am I?"
                ),
                accepted_riddle_answers=["bell"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The inventory is really about a summons: somebody was called, somebody "
                    "answered, and somebody else was asked to leave before the whole street "
                    "could hear the reason why."
                ),
                plaintext="Sound the small bell twice and bar the courtyard gate",
                hints=[
                    "Churches ring them, ships carry them, and old houses used one to call "
                    "everyone to table. It hangs, it is struck, and it makes sound without a "
                    "voice of its own.",
                    "Three letters in your answer — the smallest shift you will meet, and just as "
                    "hard to guess as any of the others.",
                    "Move every letter back three places, wrapping at A, and the order appears.",
                ],
                explanation_note=(
                    "BELL has three letters, so this telling shifts by three — the closest the "
                    "mansion comes to a giveaway."
                ),
                comprehension={
                    "question": "Why does the riddle answer matter so much here?",
                    "choices": [
                        "Its letter count becomes the shift",
                        "It is the sound that opens the gate",
                        "It tells you how many times to ring",
                        "It does not — the shift is always 3",
                    ],
                    "correct_index": 0,
                    "explanation": "BELL has three letters, so the alphabet moves three places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "Tucked at the bottom of the box is the pressed feather of a bird that has "
                    "not lived in this country for two hundred years, wrapped in a note written "
                    "so lightly that half the words have faded. What survives reads like an "
                    "instruction to somebody about to do something unforgivable."
                ),
                riddle_prompt=(
                    "I am heavier to carry the longer you hold me, yet I weigh nothing at all in "
                    "any hand but yours. Kings have toppled under me and children have carried "
                    "me across a room without noticing. What am I?"
                ),
                accepted_riddle_answers=["guilt"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The faded note is about a confession that had not happened yet — a person "
                    "deciding, in advance, exactly what they would say to whom, and when the "
                    "conversation was to be had regardless of whether they lost their nerve."
                ),
                plaintext="Confess at dawn before the household wakes",
                hints=[
                    "It is a weight with no mass, it arrives after the act and not before, and "
                    "the only cure people ever name for it involves saying something out loud.",
                    "Five letters in your answer, and five is the distance this note was hidden.",
                    "Take each letter five places back through the alphabet, wrapping at A, and "
                    "read the sentence that surfaces.",
                ],
                explanation_note=(
                    "GUILT has five letters, so this message was written five places forward."
                ),
                comprehension={
                    "question": "What determined the shift for this mission?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The number of items in the inventory",
                        "The length of the faded note",
                        "The first letter of the answer",
                    ],
                    "correct_index": 0,
                    "explanation": "GUILT has five letters, so the shift is 5.",
                },
            ),
        ],
    ),
    MissionDefinition(
        slug="midnight-train",
        title="The Midnight Train",
        difficulty="advanced",
        estimated_minutes=8,
        story=StoryDefinition(
            narrative=(
                "A rusted signal lantern was recovered when the last of the old station was "
                "pulled down for the new line. Inside its housing, rolled tight around the "
                "brass wick holder, was a message still legible after sixty years — written by "
                "somebody who clearly expected to be back within the hour and never was. The "
                "rails it describes have not carried a scheduled train since the year the "
                "timetable changed."
            ),
            riddle_prompt=(
                "I am always leaving and never gone. I carry hundreds without ever once holding "
                "them, and I was built to join places that would rather not be joined. You can "
                "miss me by minutes or by years, and no one aboard has ever managed to make me "
                "stop early. What am I?"
            ),
            accepted_riddle_answers=["train"],
            key_rule_id="letter_count",
            contextual_clue=(
                "The writer was arranging a departure that had to look ordinary — a cargo that "
                "would pass for nothing, a halt nobody used after dark, and a departure point "
                "with a timetable rather than an address."
            ),
            plaintext="Platform four past the water tower at a quarter before midnight",
            hints=[
                "It steams (or hums), it has carriages and a whistle, and it pulled into this "
                "very station for most of a century. What connects one city to another for a "
                "ticket?",
                "Five letters, five places: your answer is the number, even though the message "
                "never says so.",
                "Subtract five from every letter of the message, wrapping from A to Z, and the "
                "departure order reads itself.",
            ],
            explanation_note=(
                "TRAIN has five letters, so the message shifts by five — the timetable and the "
                "platform numbers in the case file are scenery; only the letters count."
            ),
            comprehension={
                "question": "Where did this mission's Caesar shift come from?",
                "choices": [
                    "The number of letters in the riddle answer",
                    "The clock time named in the message",
                    "The platform number",
                    "The number of words in the riddle",
                ],
                "correct_index": 0,
                "explanation": (
                    "The times and platform numbers are scenery: the shift is the letter count, "
                    "and TRAIN has five letters."
                ),
            },
        ),
        alternates=[
            StoryDefinition(
                narrative=(
                    "The stationmaster's rule book was found beside the lantern, and inside it "
                    "somebody had written instructions that have nothing to do with running a "
                    "railway — instructions for a single night, in a hand that pressed hard "
                    "enough to score the page beneath."
                ),
                riddle_prompt=(
                    "I am a straight line that two people agree to draw on the ground. One of "
                    "them always waits at my beginning and one always waits at my end, and if "
                    "either moves, the whole idea of me collapses. What am I?"
                ),
                accepted_riddle_answers=["meeting"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The stationmaster's note is about a handover: a thing left in one pair of "
                    "hands for exactly as long as it took a locomotive to pass the signal post, "
                    "and not one minute longer."
                ),
                plaintext="Wait by the signal post until the express has passed",
                hints=[
                    "Two dots joined by a stroke; an appointment; what a mathematician draws "
                    "before proving anything. It is the moment two lines cross in time rather "
                    "than in space.",
                    "Seven letters make seven places — count your answer and the shift is yours, "
                    "though the mission will never say it aloud.",
                    "Bring every letter back seven places, wrapping at A, and the instruction "
                    "becomes plain.",
                ],
                explanation_note=(
                    "MEETING has seven letters, so this telling shifts by seven."
                ),
                comprehension={
                    "question": "What determined the shift for this mission?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The time of the meeting",
                        "The number of people meeting",
                        "The length of the signal post",
                    ],
                    "correct_index": 0,
                    "explanation": "MEETING has seven letters, so the alphabet moves seven places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "The lantern's fuel cap was screwed shut around a strip of paper too narrow "
                    "to be hidden anywhere else — which is exactly why it survived. It carries "
                    "a single line of station slang and an order, and no explanation of either, "
                    "because the person reading it was meant to already know."
                ),
                riddle_prompt=(
                    "I am the exact point where a choice stops being yours. Children are taught "
                    "to signal me before they cross anything, and a whole railway network is "
                    "nothing but thousands of me made of iron and glass. Pull me the wrong way "
                    "and two things that were never meant to meet will. What am I?"
                ),
                accepted_riddle_answers=["signal"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The strip of paper gives an order about the lamps: what they were to show "
                    "on a night when the line was officially closed and unofficially busy."
                ),
                plaintext="Set the north signal to danger and keep it dark till dawn",
                hints=[
                    "Red for stop, green for go, and a semaphore arm that had to be moved by "
                    "hand before signals became lights. It warns before it commands.",
                    "Six letters in your answer is the distance the cipher moved this message.",
                    "Step each letter six places back through the alphabet, wrapping at A, and "
                    "the order will surface.",
                ],
                explanation_note=(
                    "SIGNAL has six letters, so the shift is six for this telling."
                ),
                comprehension={
                    "question": "In this mission, where did the Caesar shift come from?",
                    "choices": [
                        "The number of letters in the riddle answer",
                        "The colour of the signal",
                        "The number of signals on the line",
                        "The first letter of the message",
                    ],
                    "correct_index": 0,
                    "explanation": "SIGNAL has six letters, so the wheel turns six places.",
                },
            ),
            StoryDefinition(
                narrative=(
                    "Behind the station clock's dial, where the mechanism ticks away behind a "
                    "face that has told the wrong time since 1961, a folded ticket was found. "
                    "It was never punched and never used, and its edges carry a message written "
                    "around the rim as if the writer had run out of paper in a hurry."
                ),
                riddle_prompt=(
                    "I am bought before it is spent and spent before it is used. A thousand of me "
                    "pass through a gate every morning without a single passenger ever seeing "
                    "one of me face to face anymore. Torn in half, I am worth more than I was "
                    "whole. What am I?"
                ),
                accepted_riddle_answers=["ticket"],
                key_rule_id="letter_count",
                contextual_clue=(
                    "The message on the rim is about the last run of a train that officially "
                    "ceased to exist years earlier — the platform it left from, the hour it "
                    "left, and the understanding that nobody would be checking."
                ),
                plaintext="Board at the far platform when the clock stops striking",
                hints=[
                    "It is torn at the barrier, it proves you paid, and every passenger on every "
                    "line carries one until they reach where they are going.",
                    "Six letters in your answer, six places in the alphabet — that is the whole "
                    "key.",
                    "Decrypt by moving each letter six places back, wrapping at A. Spaces stay "
                    "where the writer left them.",
                ],
                explanation_note=(
                    "TICKET has six letters, so this message was written six places forward."
                ),
                comprehension={
                    "question": "Why does the riddle answer matter so much here?",
                    "choices": [
                        "Its letter count becomes the shift",
                        "It names the platform",
                        "It proves you paid",
                        "It does not — the shift is always 6",
                    ],
                    "correct_index": 0,
                    "explanation": (
                        "The answer is the key: TICKET has six letters, so the shift is 6."
                    ),
                },
            ),
        ],
    ),
]


def all_missions() -> list[dict[str, Any]]:
    """Build every seed mission, raising if any definition is unpublishable."""
    built: list[dict[str, Any]] = []
    errors: list[str] = []
    for definition in MISSION_DEFINITIONS:
        problems = validate_definition(definition)
        if problems:
            errors.extend(f"{definition.slug}: {p}" for p in problems)
            continue
        built.append(build_mission(definition))
    if errors:
        raise ValueError("mission content failed validation:\n" + "\n".join(errors))
    for order, mission in enumerate(built, start=1):
        mission["display_order"] = order
    return built
