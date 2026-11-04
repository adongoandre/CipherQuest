"""The Academy's cipher curriculum: eight tracks, five lessons each.

Plain data — no ORM, no FastAPI. Lesson text is authored here and served by
``app.api.v1.academy``. Step numbers are 1-based and sequential: a track is
"complete" when every step has a ``LessonProgress`` row.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CipherTrack:
    slug: str
    name: str
    blurb: str
    difficulty: str
    # Mission CipherType value this track teaches, when missions exist for it.
    mission_cipher: str | None = None


@dataclass(frozen=True, slots=True)
class Lesson:
    step: int
    title: str
    summary: str
    body: list[str]
    # Optional worked example. {"input": ..., "output": ..., "caption": ...}
    # Interactive lessons additionally carry {"interactive": "shift",
    # "sample_text": "HELLO", "default_shift": 3}.
    example: dict | None = None


TRACKS: list[CipherTrack] = [
    CipherTrack("caesar", "Caesar Cipher", "Shift the whole alphabet by a fixed number.", "beginner", "caesar"),
    CipherTrack("atbash", "Atbash", "Reflect the alphabet back on itself — no key to guess.", "beginner"),
    CipherTrack("vigenere", "Vigenère Cipher", "A repeating keyword drives a different shift per letter.", "intermediate"),
    CipherTrack("rail-fence", "Rail Fence", "Write the letters along a zigzag, then read them off in rows.", "intermediate"),
    CipherTrack("playfair", "Playfair", "Encrypt letter pairs through a 5×5 grid of the alphabet.", "intermediate"),
    CipherTrack("columnar", "Columnar Transposition", "Rearrange the columns of a grid by a numeric key.", "intermediate"),
    CipherTrack("baconian", "Baconian", "Hide a message in five-bit groups — two typefaces, one alphabet.", "advanced"),
    CipherTrack("substitution", "Simple Substitution", "One letter stands for another, the whole way through.", "advanced"),
]

TRACK_BY_SLUG: dict[str, CipherTrack] = {t.slug: t for t in TRACKS}


def _shift_lesson(
    step: int, title: str, summary: str, body: list[str], example: dict | None = None
) -> Lesson:
    return Lesson(step=step, title=title, summary=summary, body=body, example=example)


LESSONS: dict[str, list[Lesson]] = {
    "caesar": [
        _shift_lesson(
            1,
            "What is a Caesar cipher?",
            "The oldest trick in cryptology: move every letter the same distance along the alphabet.",
            [
                "A Caesar cipher replaces each letter with the letter a fixed number of places further along the alphabet. The message below was shifted three places: H became K, E became H, L became O.",
                "The number is called the shift, and it is the whole secret. Shift zero leaves the message alone; a shift of 3 is the classic; a shift of 25 moves every letter back one place.",
                "The cipher is symmetric: the same shift that locks a message unlocks it. That simplicity is its charm and its weakness — there are only 26 possible keys.",
            ],
        ),
        _shift_lesson(
            2,
            "Move each letter along the alphabet",
            "A shift of 3 turns A into D, B into E, and so on. At the end of the alphabet, you wrap round to A.",
            [
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "Write the alphabet twice, line the second up under the first three places to the right, and every substitution becomes a lookup: H three places on is K, E is H, L is O.",
                "Letters past the end wrap around: Y shifted by 3 becomes B, Z becomes C. Spaces, digits and punctuation never move — the cipher only touches letters.",
                "Set a shift below and watch a word travel. Try 1, then 13, then 25.",
            ],
            {"interactive": "shift", "sample_text": "HELLO", "default_shift": 3},
        ),
        _shift_lesson(
            3,
            "Decrypting one letter at a time",
            "Decryption is the same shift in reverse: move every letter back, wrapping at A.",
            [
                "To decrypt, subtract the shift instead of adding it: K three places back is H, H is E, O is L. Wrap past A to Z when you need to — A shifted back one is Z.",
                "A fast practical method: write the ciphertext under a key word whose first letters line up at the secret shift (a shift of 3 lines up under CAT, the third letter of the alphabet being C — or simply count three places from the start of a fresh alphabet).",
                "Work one letter, then check the first word. If it reads like English, the shift is right and the rest falls out quickly.",
            ],
        ),
        _shift_lesson(
            4,
            "Frequency: the cipher's tell",
            "E appears more than any other letter in English — and a Caesar cipher can only move that bump, not hide it.",
            [
                "Shift every letter of English and the frequencies shift with it. E stays the most common letter; it just appears at a different position in the chart.",
                "Plot the ciphertext's letter counts, slide the pattern one position at a time against the known English frequencies, and the shift often announces itself within a few sentences of text.",
                "That weakness is why one-shift ciphers died out — but it is also why short messages still resist frequency analysis: there are too few letters for a pattern to show.",
            ],
        ),
        _shift_lesson(
            5,
            "Put it together: a full decrypt",
            "Riddle first, shift second: the mission pattern in four moves.",
            [
                "Real missions hide the key as well as the message. A riddle points at a word; the word's letter count becomes the shift — that is the key rule our missions use.",
                "So the full solve is: answer the riddle, count the letters, set the shift, and decrypt. Missions give three progressive hints if any step stalls.",
                "You are ready: take a mission from the Play screen and run the loop end to end.",
            ],
        ),
    ],
    "atbash": [
        _shift_lesson(
            1,
            "The mirror alphabet",
            "Atbash reflects the alphabet: A becomes Z, B becomes Y, and the whole message mirrors.",
            [
                "Write the alphabet, then write it again underneath in reverse. Every letter now has a partner directly above it: A↔Z, B↔Y, M↔N.",
                "Atbash is a substitution, not a shift — but it behaves like a shift of 25 with extra steps, which is why it slots neatly into the same wheel tools.",
            ],
        ),
        _shift_lesson(
            2,
            "A swaps with Z",
            "One rule, applied everywhere: fold the alphabet in half and pair the ends.",
            [
                "The pairing is fixed forever — there is no key to choose, no key to leak. HELLO becomes Svool; SV OOL comes back to HELLO by doing exactly the same thing.",
                "Because the mapping is symmetric, encrypting and decrypting are literally the same operation. Apply the mirror twice and you are back where you started.",
            ],
        ),
        _shift_lesson(
            3,
            "Decrypting Atbash",
            "Run the alphabet backwards under the ciphertext and read straight off.",
            [
                "Line up the reversed alphabet beneath the normal one and read each ciphertext letter from the lower row's upper partner. Wrap is automatic: A and Z are already partners.",
                "Watch for letter pairs that never change the word's shape — N and M, for example — Atbash preserves word lengths and punctuation exactly, so the layout of the message stays intact.",
            ],
        ),
        _shift_lesson(
            4,
            "Why Atbash never changes",
            "No key means no key management — and no way to vary the disguise.",
            [
                "Atbash was used by Hebrew scribes precisely because it needed no secret: everyone in the community already knew the one rule.",
                "Its cost is equally simple: frequency analysis works on Atbash exactly as it works on plain text, because a fixed mapping never scrambles which letters are rare or common — it only renames them.",
            ],
        ),
        _shift_lesson(
            5,
            "Spot Atbash in the wild",
            "Recognise it by its giveaways: mirrored words and a suspiciously normal-looking frequency chart.",
            [
                "If a short sample decodes to sensible English with the mirror alphabet, you have Atbash — try it first whenever a message has no key hints at all.",
                "In our missions, Atbash-style answers appear inside Caesar puzzles too: knowing the mirror makes the wrap-around shifts intuitive when you get to negative-feeling ones like 25.",
            ],
        ),
    ],
    "vigenere": [
        _shift_lesson(
            1,
            "More than one shift",
            "A Vigenère cipher changes the shift every letter, driven by a keyword.",
            [
                "A single shift is easy to break because the pattern repeats every letter. Vigenère breaks that pattern: the shift cycles through a sequence of numbers instead of repeating one.",
                "That sequence is spelled out by a keyword — every letter of the keyword is itself a shift (A=0, B=1, C=2 …), applied in turn to the message.",
            ],
        ),
        _shift_lesson(
            2,
            "The keyword",
            "Pick a word only you would think of; its letters become the shift schedule.",
            [
                "The keyword is written above the message, repeating until it covers every letter: KEYKEYKEY… over 'attack at dawn'.",
                "Each message letter is shifted by the letter sitting above it: A (shift 0) under K, T under E, T under Y — three different shifts in the first three letters.",
            ],
        ),
        _shift_lesson(
            3,
            "Encrypting with a keyword",
            "Two alphabets, added together — or one lookup table if you prefer.",
            [
                "For each position, work out the keyword letter's number, add it to the message letter's position, take the result mod 26, and read off the new letter.",
                "The classic tool is the tabula recta: the keyword letter picks a row, the plaintext letter picks a column, and the crossing cell is the ciphertext letter.",
            ],
        ),
        _shift_lesson(
            4,
            "Decrypting step by step",
            "Subtract the keyword shift instead of adding it, then re-align the keyword.",
            [
                "Decryption mirrors encryption: subtract the keyword letter's number (mod 26) rather than adding it. Everything else — alignment, wrap-around — is identical.",
                "Keep the keyword aligned to the start of the message, not to line breaks. A message split over lines does not reset the cycle.",
            ],
        ),
        _shift_lesson(
            5,
            "Reading a Vigenère table",
            "The grid holds every Caesar shift at once — one row per keyword letter.",
            [
                "Rows of the tabula recta are plain Caesar alphabets shifted progressively: row A is the plain alphabet, row B is a shift of 1, and so on.",
                "Because each row is still English shifted, long texts leak clues: repeating ciphertext groups suggest a keyword length, and once that length is known each row reverts to simple frequency analysis.",
            ],
        ),
    ],
    "rail-fence": [
        _shift_lesson(
            1,
            "Writing on fences",
            "Rail fence scatters letters across a zigzag — substitution never happens.",
            [
                "Write the message left to right along a zigzag of rails, then read each rail top to bottom. The letters themselves never change; only their order does.",
                "With two rails, alternate letters go to the top and bottom rows. CRYPTO becomes CTO on the first rail and RPY on the second.",
            ],
        ),
        _shift_lesson(
            2,
            "Two rails and three rails",
            "The rail count is the key — and it reshapes the whole message.",
            [
                "Three rails of SECRET SENDS at noon: S E S N O forms the top rail, E C T E D S T forms the middle, R P D A U forms the bottom.",
                "More rails mean a longer cycle before the pattern repeats: 2 rails alternate every letter, 3 rails visit each rail on a 4-letter cycle.",
            ],
        ),
        _shift_lesson(
            3,
            "Reading rails in order",
            "Decryption reconstructs the fence, then folds it back up.",
            [
                "The ciphertext is the rails concatenated: top rail, then middle, then bottom. Split it back into rails using the zigzag's letter counts, then read down each column of the original shape.",
                "The split counts come from one zigzag period: for n rails a period covers 2(n−1) letters, so full periods fit into the length evenly and the remainder forms a partial period.",
            ],
        ),
        _shift_lesson(
            4,
            "Decrypting a fence",
            "Work out the period, divide the length, rebuild — four steps, no key alphabet.",
            [
                "Take the message length, work out how many letters land on each rail for one period, and allocate the ciphertext accordingly — the last rail of a partial period gets only what the shape allows.",
                "Write empty rail lines, fill each rail with its slice of ciphertext, then read the columns following the zigzag. The sentence reassembles itself.",
            ],
        ),
        _shift_lesson(
            5,
            "Counting rails from context",
            "Try small rail counts first — 2 and 3 solve most short messages.",
            [
                "Rail fence has no frequency signal: every rail contains real letters in real proportions, so the chart never spikes. You detect it by trying decryption and watching for English.",
                "Hints that it is rail fence: word boundaries are lost (it is usually applied after removing spaces), short messages crack at 2 rails, and no letter ever changes.",
            ],
        ),
    ],
    "playfair": [
        _shift_lesson(
            1,
            "Encrypting pairs",
            "Playfair works on two letters at a time — 25 letters in the grid, I and J share a cell.",
            [
                "Split the message into letter pairs (inserting X between doubles, adding a filler at the end if needed) and encrypt each pair as a unit.",
                "Because letters move within pairs, no single letter ever stands alone — a fingerprint that makes Playfair instantly recognisable.",
            ],
        ),
        _shift_lesson(
            2,
            "Building the 5×5 grid",
            "Write the keyword first, then the rest of the alphabet, skipping repeats.",
            [
                "Fill a 5×5 square with your keyword (duplicates dropped), then continue with the unused letters in order — I and J count as one cell.",
                "The grid is the entire key: the same keyword always builds the same square, and every rule of the cipher is a movement inside it.",
            ],
        ),
        _shift_lesson(
            3,
            "The four rules",
            "Same row: shift right. Same column: shift down. Rectangle: swap corners.",
            [
                "For each pair, find the two cells. Same row → each letter moves one step right (wrapping around). Same column → each moves one step down.",
                "Otherwise the two letters form a rectangle: each swaps to the corner in its own row. Row and column pairs are the special cases where the rectangle collapses.",
            ],
        ),
        _shift_lesson(
            4,
            "Decrypting digraphs",
            "Reverse every movement: right becomes left, down becomes up, corners stay.",
            [
                "Decryption uses the same grid and opposite directions: same row shifts left, same column shifts up, rectangle pairs swap corners exactly as they did when encrypting.",
                "When the plaintext reappears, ignore filler letters (X inserted between doubled letters) — context tells you which X's were scaffolding.",
            ],
        ),
        _shift_lesson(
            5,
            "I and J together",
            "One shared cell keeps 26 letters inside 25 spaces.",
            [
                "Historical Playfair grids treat I and J as the same letter — the keyword writer just skips whichever one appears second.",
                "That means a decrypted J may really be an I and vice versa. Read with that in mind: English words with J are rare, so most J's in output are really I's.",
            ],
        ),
    ],
    "columnar": [
        _shift_lesson(
            1,
            "Transposition, not substitution",
            "Columnar keeps every letter — it only moves them somewhere else.",
            [
                "Write the message into rows under a header of digits, then read the columns out in a scrambled order. Letters are never replaced, only reordered.",
                "The key is the header order itself: SECRET might be ordered 4-1-5-3-2 when you sort its letters alphabetically.",
            ],
        ),
        _shift_lesson(
            2,
            "Writing by columns",
            "Fill the grid left to right, top to bottom, then read down each column.",
            [
                "Write the plaintext row by row. Once full, read the first column top to bottom, then the column whose header is 2, and so on until every column is emitted.",
                "The final row may be short; its gaps simply mean the last column has fewer letters — remember that when splitting the ciphertext back up.",
            ],
        ),
        _shift_lesson(
            3,
            "Reading by key order",
            "The numeric key tells you which column to read first — sort the keyword to get it.",
            [
                "Number the keyword letters by their alphabetical rank: KEY becomes 2-3-1 (E before K before Y), so read column 3 first, then 1, then 2.",
                "Ties break left to right: with KEYED, E and D are the first two letters alphabetically, so their columns keep their original left-to-right order among equals.",
            ],
        ),
        _shift_lesson(
            4,
            "Decrypting columnar",
            "Calculate the column widths, carve the ciphertext, then read across.",
            [
                "Work out each column's length from the key and grid height, slice the ciphertext accordingly, and lay the slices back into columns.",
                "Then read the grid row by row — the plaintext reappears in writing order, exactly as it went in.",
            ],
        ),
        _shift_lesson(
            5,
            "Multiple passes",
            "Run the same transposition twice with a different key and the scramble compounds.",
            [
                "A double columnar pass multiplies the work for a decipherer: each pass destroys the row structure the first one preserved.",
                "In our missions, a two-pass message usually signals itself by its length — the key hint stays in the riddle while the layers do the hiding.",
            ],
        ),
    ],
    "baconian": [
        _shift_lesson(
            1,
            "Letters in disguise",
            "Bacon's cipher encodes the alphabet itself, not substitutions of it.",
            [
                "Each plaintext letter becomes a group of five 'bits', written as two alternating symbols — historically two typefaces, A-style and B-style.",
                "The carriers can be almost anything with two states: italic and roman, upper and lower, tap and knock, even a present/absent mark.",
            ],
        ),
        _shift_lesson(
            2,
            "The five-bit alphabet",
            "26 letters map onto 32 possible groups — five unused combinations.",
            [
                "Count in binary with A=aaaaa, B=aaaab, C=aaaba … up to z=zzzzz skipping I/J merges, and the whole alphabet fits in five symbols per letter.",
                "Because only 26 of 32 groups are used, a sloppy message can contain invalid groups — a free checksum that reveals the cipher immediately.",
            ],
        ),
        _shift_lesson(
            3,
            "Encoding with typefaces",
            "Write the cover text normally, then decide each letter's style by the bits.",
            [
                "Take your five-bit groups in order. As you write the cover sentence, style each character: A-type for the first state, B-type for the second.",
                "The result reads like an ordinary page with a slightly fussy typographer — which is exactly the point: the message hides in plain presentation, not in scrambled content.",
            ],
        ),
        _shift_lesson(
            4,
            "Decrypting Bacon",
            "Group the two-state symbols into fives and map each group to a letter.",
            [
                "First split the carrier into its two states — italic vs roman, dot vs dash — then chunk that bitstream into groups of five.",
                "Look each group up in the Bacon alphabet. Groups of four or six mean the alignment slipped; shift the start position until the letters read like English.",
            ],
        ),
        _shift_lesson(
            5,
            "A cipher you can whisper",
            "Two states survive any channel: sound, light, handwriting, or flags.",
            [
                "Bacon's original proposal was a way for prisoners to communicate through visible habits — anything two people can distinguish at a distance works.",
                "Its weakness is bandwidth: five symbols per letter means long cover passages for short messages, and any miscount shifts the entire rest of the decode.",
            ],
        ),
    ],
    "substitution": [
        _shift_lesson(
            1,
            "One letter, one letter",
            "Simple substitution renames the alphabet once and reuses the mapping everywhere.",
            [
                "Choose any permutation of the 26 letters as the new alphabet: A→M, B→Z, C→Q … and apply it to every occurrence of each letter.",
                "Word lengths survive, punctuation survives, double letters survive — only the letter identities change, which is why patterns still break through.",
            ],
        ),
        _shift_lesson(
            2,
            "Frequency analysis",
            "E, T, A, O, I, N — the most common English letters map to the most common ciphertext letters.",
            [
                "Count the ciphertext's letters. The most frequent one is almost certainly E (about 13%), then T, A, O, I, N in the usual English proportions.",
                "Short messages are unreliable — one word can skew everything. Work with as much text as you have, and score candidate mappings by how many common patterns (THE, AND, -TION) appear.",
            ],
        ),
        _shift_lesson(
            3,
            "Drawing the key alphabet",
                "Write the two alphabets side by side and fill the mapping in as you confirm each letter.",
            [
                "Start with two rows: plain on top, cipher below. Fill in what frequency suggests, then confirm each guess against a word you have already partially solved.",
                "Confirmed letters pay for themselves: each one constrains the rest of the alphabet and makes the next guess easier to check.",
            ],
        ),
        _shift_lesson(
            4,
            "Solving a substitution",
                "Word shapes first, then double letters, then the confirm-and-propagate loop.",
            [
                "One-letter words are I or A; three-letter words ending in a vowel-shaped middle are often THE, AND, FOR. Solve those, then propagate into crossings.",
                "Double letters are a gift: English doubles are almost always LL, EE, OO, SS, FF, RR, TT — a double ciphertext letter strongly suggests one of those.",
            ],
        ),
        _shift_lesson(
            5,
            "Common traps",
            "Rare letters are decoys: Q, X and Z guesses mislead more often than they help.",
            [
                "Resist mapping the rarest letters first — frequency counts for Q and Z are noisy, and a wrong guess there derails every word that touches it.",
                "When stuck, leave the alphabet and test a phrase instead: a plausible word at a key position proves or kills three letters at once.",
            ],
        ),
    ],
}

# Guard: every track ships exactly five lessons, steps 1..5 in order.
assert set(LESSONS) == {t.slug for t in TRACKS}
for _slug, _lessons in LESSONS.items():
    assert [les.step for les in _lessons] == [1, 2, 3, 4, 5], _slug