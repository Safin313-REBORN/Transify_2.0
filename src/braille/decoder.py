"""
UEB Grade 1 Deterministic Decoder for Transify Module 02.
Complies with ICEB Rules of Unified English Braille, Third Edition (2024).
"""

from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class RecognizedCell:
    """Represents a classified Braille cell from computer vision stage."""
    cell_id: str
    line_idx: int
    col_idx: int
    dot_vector: Tuple[int, int, int, int, int, int]  # (d1, d2, d3, d4, d5, d6)
    unicode_char: str
    confidence: float
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    is_space: bool = False


@dataclass
class DecodedDocument:
    """Represents the complete decoded textual document output."""
    raw_text: str
    clean_text: str
    total_cells: int
    confidence_mean: float
    uncertain_cells: List[Dict[str, Any]] = field(default_factory=list)
    grade2_warnings: List[str] = field(default_factory=list)
    line_transcriptions: List[str] = field(default_factory=list)


# --- ICEB UEB GRADE 1 LOOKUP TABLES ---

DOT_TO_UNICODE_OFFSET = 0x2800

ALPHABET_MAP: Dict[Tuple[int, ...], str] = {
    (1, 0, 0, 0, 0, 0): 'a',  # ⠁
    (1, 1, 0, 0, 0, 0): 'b',  # ⠃
    (1, 0, 0, 1, 0, 0): 'c',  # ⠉
    (1, 0, 0, 1, 1, 0): 'd',  # ⠙
    (1, 0, 0, 0, 1, 0): 'e',  # ⠑
    (1, 1, 0, 1, 0, 0): 'f',  # ⠋
    (1, 1, 0, 1, 1, 0): 'g',  # ⠛
    (1, 1, 0, 0, 1, 0): 'h',  # ⠓
    (0, 1, 0, 1, 0, 0): 'i',  # ⠊
    (0, 1, 0, 1, 1, 0): 'j',  # ⠚
    (1, 0, 1, 0, 0, 0): 'k',  # ⠅
    (1, 1, 1, 0, 0, 0): 'l',  # ⠇
    (1, 0, 1, 1, 0, 0): 'm',  # ⠍
    (1, 0, 1, 1, 1, 0): 'n',  # ⠝
    (1, 0, 1, 0, 1, 0): 'o',  # ⠕
    (1, 1, 1, 1, 0, 0): 'p',  # ⠏
    (1, 1, 1, 1, 1, 0): 'q',  # ⠟
    (1, 1, 1, 0, 1, 0): 'r',  # ⠗
    (0, 1, 1, 1, 0, 0): 's',  # ⠎
    (0, 1, 1, 1, 1, 0): 't',  # ⠞
    (1, 0, 1, 0, 0, 1): 'u',  # ⠥
    (1, 1, 1, 0, 0, 1): 'v',  # ⠧
    (0, 1, 0, 1, 1, 1): 'w',  # ⠺
    (1, 0, 1, 1, 0, 1): 'x',  # ⠭
    (1, 0, 1, 1, 1, 1): 'y',  # ⠽
    (1, 0, 1, 0, 1, 1): 'z',  # ⠵
}

NUMERIC_MAP: Dict[Tuple[int, ...], str] = {
    (1, 0, 0, 0, 0, 0): '1',  # a
    (1, 1, 0, 0, 0, 0): '2',  # b
    (1, 0, 0, 1, 0, 0): '3',  # c
    (1, 0, 0, 1, 1, 0): '4',  # d
    (1, 0, 0, 0, 1, 0): '5',  # e
    (1, 1, 0, 1, 0, 0): '6',  # f
    (1, 1, 0, 1, 1, 0): '7',  # g
    (1, 1, 0, 0, 1, 0): '8',  # h
    (0, 1, 0, 1, 0, 0): '9',  # i
    (0, 1, 0, 1, 1, 0): '0',  # j
}

PUNCTUATION_MAP: Dict[Tuple[int, ...], str] = {
    (0, 1, 0, 0, 1, 1): '.',   # ⠲ Period / Full Stop (dots 2-5-6)
    (0, 1, 0, 0, 0, 0): ',',   # ⠂ Comma (dot 2)
    (0, 1, 1, 0, 0, 0): ';',   # ⠆ Semicolon (dots 2-3)
    (0, 1, 0, 0, 1, 0): ':',   # ⠒ Colon (dots 2-5)
    (0, 1, 1, 0, 0, 1): '?',   # ⠦ Question mark (dots 2-3-6)
    (0, 1, 1, 0, 1, 0): '!',   # ⠖ Exclamation mark (dots 2-3-5)
    (0, 0, 1, 0, 0, 1): '-',   # ⠤ Hyphen (dots 3-6)
    (0, 0, 1, 0, 0, 0): "'",   # ⠄ Apostrophe (dot 3)
    (0, 0, 1, 0, 1, 1): '"',   # ⠴ Close double quote (dots 3-5-6)
}

# Special Indicators
CAPITAL_INDICATOR = (0, 0, 0, 0, 0, 1)          # Dot 6 (⠠)
NUMERIC_INDICATOR = (0, 0, 1, 1, 1, 1)          # Dots 3-4-5-6 (⠼)
GRADE1_INDICATOR  = (0, 0, 0, 0, 1, 1)          # Dots 5-6 (⠰)
CAPITAL_TERMINATOR_2ND = (0, 0, 1, 0, 0, 0)     # Dot 3 (⠄) when preceded by Dot 6
EMPTY_CELL        = (0, 0, 0, 0, 0, 0)          # Space (⠀)

# Common Grade 2 strong contractions to audit and warn about
GRADE2_STRONG_CONTRACTIONS: Dict[Tuple[int, ...], str] = {
    (1, 1, 1, 1, 0, 1): "and (⠯)",
    (1, 1, 1, 1, 1, 1): "for (⠿)",
    (1, 1, 1, 0, 1, 1): "of (⠷)",
    (0, 1, 1, 1, 0, 1): "the (⠮)",
    (0, 1, 1, 1, 1, 1): "with (⠾)",
}

GRADE2_SUPPORTED_CONTRACTIONS: List[str] = [
    "and (dots 1-2-3-4-6 / ⠯)",
    "for (dots 1-2-3-4-5-6 / ⠿)",
    "of (dots 1-2-3-5-6 / ⠷)",
    "the (dots 2-3-4-6 / ⠮)",
    "with (dots 2-3-4-5-6 / ⠾)"
]

GRADE2_UNSUPPORTED_CONTRACTIONS: List[str] = [
    "Shortform words (e.g., ab = about, af = after, al = also, b = but, c = can, d = do, e = every)",
    "Two-cell initial-letter contractions (e.g., dot 5 + d = day, dot 5 + e = ever, dot 5 + f = father)",
    "Final-letter groupsigns (e.g., dots 4-6 + e = ance, dots 5-6 + e = ence, dots 4-6 + n = sion)",
    "Lower groupsigns and wordsigns (e.g., ea, bb, cc, ff, gg, be, con, dis, en, in)",
    "Standing-alone word contractions (e.g., child, shall, still, this, which, out)"
]

# Bengali Bharati Braille Transliteration Scope & Limitations
BENGALI_BHARATI_SUPPORTED_CHARS: List[str] = [
    "অ", "আ", "ই", "ঈ", "উ", "ঊ", "এ", "ঐ", "ও", "ঔ",  # 10 basic vowels
    "ক", "খ", "গ", "ঘ", "ঙ", "চ", "ছ", "জ", "ঝ", "ঞ",  # Consonants 1-10
    "ট", "ঠ", "ড", "ঢ", "ণ", "ত", "থ", "দ", "ধ", "ন",  # Consonants 11-20
    "প", "ফ", "ব", "ভ", "ম", "য", "র", "ল", "শ", "ষ", "স", "হ",  # Consonants 21-32
    "।", ",", ";", ":", "?", "!"  # Punctuation
]

BENGALI_BHARATI_UNSUPPORTED_SEQUENCES: List[str] = [
    "Complex conjunct ligatures / Juktoborno (e.g., ক্ত, ক্ষ, জ্ঞ, ঙ্গ, ঞ্চ, ণ্ড, ত্ত, ত্র, দ্ধ, ন্ধ, ণ্ট)",
    "Contextual vowel sign diacritics / Kar-chinho (া, ি, ী, ু, ূ, ৃ, ে, ৈ, ো, ৌ) without explicit Bharati cell mapping",
    "Hasant / Virama (্) ligature rendering in camera OCR",
    "Nasalization Chandrabindu (ঁ), Anusvara (ং), Visarga (ঃ) in multi-cell OCR"
]


def vector_to_unicode(v: Tuple[int, ...]) -> str:
    """Converts 6-dot binary tuple into standard Unicode Braille symbol."""
    codepoint = DOT_TO_UNICODE_OFFSET + sum(bit << i for i, bit in enumerate(v))
    return chr(codepoint)


def unicode_to_vector(ch: str) -> Tuple[int, ...]:
    """Converts Unicode Braille symbol (U+2800..U+283F) into 6-dot binary tuple."""
    val = ord(ch) - DOT_TO_UNICODE_OFFSET
    if not (0 <= val <= 63):
        raise ValueError(f"Character {ch} (U+{ord(ch):04X}) is not in Unicode Braille range U+2800..U+283F")
    return tuple((val >> i) & 1 for i in range(6))


class UEBGrade1Decoder:
    """
    Deterministic State Machine parser for Unified English Braille (UEB) Grade 1.
    """

    def __init__(self, confidence_threshold: float = 0.65):
        self.confidence_threshold = confidence_threshold

    def decode_lines(self, lines: List[List[RecognizedCell]]) -> DecodedDocument:
        """Decodes multi-line structured Braille cells preserving paragraph structure."""
        all_cells = []
        for line in lines:
            all_cells.extend(line)

        total_cells = len(all_cells)
        if total_cells == 0:
            return DecodedDocument(
                raw_text="",
                clean_text="",
                total_cells=0,
                confidence_mean=1.0,
                uncertain_cells=[],
                grade2_warnings=[],
                line_transcriptions=[]
            )

        confidences = [c.confidence for c in all_cells if not c.is_space]
        mean_conf = sum(confidences) / max(len(confidences), 1)

        uncertain_cells = [
            {"cell_id": c.cell_id, "line": c.line_idx, "col": c.col_idx, "conf": c.confidence, "dots": c.dot_vector}
            for c in all_cells if not c.is_space and c.confidence < self.confidence_threshold
        ]

        decoded_lines = []
        all_warnings = []

        for line_idx, line_cells in enumerate(lines):
            line_str, warnings = self._decode_single_line(line_cells, line_idx)
            decoded_lines.append(line_str)
            all_warnings.extend(warnings)

        full_raw = "\n".join(decoded_lines)
        # Clean up text (normalize duplicate spaces, trim trailing spaces per line)
        clean_lines = [" ".join(line.split()) for line in decoded_lines]
        clean_text = "\n".join(clean_lines)

        return DecodedDocument(
            raw_text=full_raw,
            clean_text=clean_text,
            total_cells=total_cells,
            confidence_mean=float(mean_conf),
            uncertain_cells=uncertain_cells,
            grade2_warnings=all_warnings,
            line_transcriptions=decoded_lines
        )

    def decode_cells(self, cells: List[RecognizedCell]) -> DecodedDocument:
        """Decodes a flat list of recognized cells (assumed single line)."""
        return self.decode_lines([cells])

    def decode_unicode_string(self, braille_text: str) -> DecodedDocument:
        """Utility for decoding a string of Unicode Braille symbols (e.g. '⠠⠓⠑⠇⠇⠕')."""
        lines = braille_text.splitlines()
        structured_lines: List[List[RecognizedCell]] = []

        for line_idx, line_str in enumerate(lines):
            line_cells: List[RecognizedCell] = []
            for col_idx, ch in enumerate(line_str):
                if ch in (' ', '\t', '⠀'):
                    line_cells.append(RecognizedCell(
                        cell_id=f"L{line_idx}_C{col_idx}",
                        line_idx=line_idx,
                        col_idx=col_idx,
                        dot_vector=EMPTY_CELL,
                        unicode_char='⠀',
                        confidence=1.0,
                        is_space=True
                    ))
                else:
                    vec = unicode_to_vector(ch)
                    line_cells.append(RecognizedCell(
                        cell_id=f"L{line_idx}_C{col_idx}",
                        line_idx=line_idx,
                        col_idx=col_idx,
                        dot_vector=vec,
                        unicode_char=ch,
                        confidence=1.0,
                        is_space=False
                    ))
            structured_lines.append(line_cells)

        return self.decode_lines(structured_lines)

    def _decode_single_line(self, cells: List[RecognizedCell], line_idx: int) -> Tuple[str, List[str]]:
        """Parses a single line of cells through the FSA."""
        output_chars: List[str] = []
        warnings: List[str] = []

        # FSA State Variables
        state = "BASE"  # 'BASE', 'CAPITAL_NEXT', 'CAPITAL_WORD', 'NUMERIC'
        idx = 0
        n = len(cells)

        while idx < n:
            cell = cells[idx]
            vec = cell.dot_vector

            # Check for space cell
            if cell.is_space or vec == EMPTY_CELL:
                output_chars.append(" ")
                state = "BASE"  # Space terminates numeric and capital modes
                idx += 1
                continue

            # 1. Check for Grade 2 strong contractions
            if vec in GRADE2_STRONG_CONTRACTIONS:
                warnings.append(
                    f"Line {line_idx+1}, Col {cell.col_idx+1}: Possible Grade 2 contraction '{GRADE2_STRONG_CONTRACTIONS[vec]}' detected outside Grade 1 indicator."
                )

            # 2. State Machine Logic
            if state == "BASE":
                if vec == CAPITAL_INDICATOR:
                    # Check if next is also CAPITAL_INDICATOR (Capital Word)
                    if idx + 1 < n and cells[idx + 1].dot_vector == CAPITAL_INDICATOR:
                        state = "CAPITAL_WORD"
                        idx += 2
                        continue
                    else:
                        state = "CAPITAL_NEXT"
                        idx += 1
                        continue

                elif vec == NUMERIC_INDICATOR:
                    state = "NUMERIC"
                    idx += 1
                    continue

                elif vec == GRADE1_INDICATOR:
                    # Grade 1 symbol indicator: skip indicator, next cell remains base/grade 1
                    idx += 1
                    continue

                else:
                    char = self._map_cell(vec, numeric_mode=False)
                    output_chars.append(char)
                    idx += 1

            elif state == "CAPITAL_NEXT":
                if vec == CAPITAL_INDICATOR:
                    # Second dot 6 -> capital word
                    state = "CAPITAL_WORD"
                    idx += 1
                    continue
                else:
                    char = self._map_cell(vec, numeric_mode=False)
                    output_chars.append(char.upper())
                    state = "BASE"
                    idx += 1

            elif state == "CAPITAL_WORD":
                # Check for capital terminator: Dot 6 followed by Dot 3 (⠠⠄)
                if vec == CAPITAL_INDICATOR and (idx + 1 < n) and cells[idx + 1].dot_vector == CAPITAL_TERMINATOR_2ND:
                    state = "BASE"
                    idx += 2
                    continue

                char = self._map_cell(vec, numeric_mode=False)
                if char.isalpha():
                    output_chars.append(char.upper())
                else:
                    output_chars.append(char)
                    # Non-alpha (punctuation or symbol) terminates capital word in standard UEB
                    if char in ('.', '!', '?', ';', ':', '-', '"'):
                        state = "BASE"
                idx += 1

            elif state == "NUMERIC":
                if vec in NUMERIC_MAP:
                    digit = NUMERIC_MAP[vec]
                    output_chars.append(digit)
                    idx += 1
                elif vec == (0, 1, 0, 0, 0, 0):  # Dot 2 -> Comma separator in number
                    output_chars.append(",")
                    idx += 1
                elif vec in ((0, 1, 0, 0, 1, 1), (0, 0, 0, 1, 0, 1)):  # Dots 2-5-6 or Dots 4-6 -> Decimal point
                    output_chars.append(".")
                    idx += 1
                elif vec == (0, 0, 1, 0, 0, 1):  # Dots 3-6 -> Hyphen in number
                    output_chars.append("-")
                    idx += 1
                else:
                    # Non-numeric character terminates numeric mode
                    state = "BASE"
                    # Reprocess current cell in BASE state
                    continue

        return "".join(output_chars), warnings

    def _map_cell(self, vec: Tuple[int, ...], numeric_mode: bool = False) -> str:
        """Maps dot vector to English character or punctuation mark."""
        if numeric_mode and vec in NUMERIC_MAP:
            return NUMERIC_MAP[vec]

        if vec in ALPHABET_MAP:
            return ALPHABET_MAP[vec]

        if vec in PUNCTUATION_MAP:
            return PUNCTUATION_MAP[vec]

        # Unknown / unassigned configuration
        glyph = vector_to_unicode(vec)
        return f"[?{glyph}]"
