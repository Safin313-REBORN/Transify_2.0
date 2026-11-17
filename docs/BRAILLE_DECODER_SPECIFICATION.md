# UEB Grade 1 Decoder Software Specification
## Deterministic State-Machine Parsing for Unified English Braille (2024 ICEB Standards)

---

## 1. System Overview

The **Transify UEB Grade 1 Decoder** is an isolated, deterministic parsing engine that translates a linear or multi-line stream of classified 6-dot Braille cells into grammatically correct English text.

In accordance with strict scientific guidelines:
- **No Large Language Model (LLM) Guessing:** The decoder does not perform hallucinated lexical completion or autoregressive token guessing.
- **Strict Decoupling:** Visual cell recognition errors are isolated from grammatical parsing errors.
- **Uncertainty Propagation:** Unclear cells, low-confidence predictions, and ambiguous dot patterns are explicitly tagged with confidence markers rather than silently converted into arbitrary English letters.

---

## 2. Input and Output Interfaces

### 2.1 Input Data Structure
The decoder accepts an ordered list of `RecognizedCell` structures, typically grouped into lines:

```python
class RecognizedCell:
    cell_id: str                      # Unique identifier, e.g. "DOC01_L01_C04"
    line_idx: int                     # 0-indexed line number in document
    col_idx: int                      # 0-indexed cell position along the line
    dot_vector: tuple[int, ...]       # 6 binary values (d1, d2, d3, d4, d5, d6) in {0, 1}
    unicode_char: str                 # Braille glyph from U+2800..U+283F
    confidence: float                 # Minimum posterior probability across 6 dots [0.0, 1.0]
    bbox: tuple[int, int, int, int]   # Bounding box (x_min, y_min, x_max, y_max)
    is_space: bool                    # True if cell represents an inter-word space
```

### 2.2 Output Data Structure
The decoder returns a structured `DecodedDocument` object:

```python
class DecodedDocument:
    raw_text: str                     # Plain English text with lines and spaces
    clean_text: str                   # Normalized English text
    total_cells: int                  # Total count of processed cells
    confidence_mean: float            # Mean confidence across all cells
    uncertain_cells: list[dict]       # List of flagged cells with confidence < threshold
    grade2_warnings: list[str]        # Warnings for possible Grade 2 contractions detected
    line_transcriptions: list[str]    # Line-by-line decoded text strings
```

---

## 3. Decoder State Machine Architecture

The decoder runs as a deterministic finite-state automaton (FSA) with memory:

```
[Cell Stream] ---> [Pre-Classifier / Space Detector]
                          │
                          ▼
                  [FSA Core Engine]
                  ├── State: BASE
                  ├── State: CAPITAL_NEXT
                  ├── State: CAPITAL_WORD
                  ├── State: NUMERIC_MODE
                  └── State: GRADE1_SYMBOL
                          │
                          ▼
             [Grade 2 Heuristic Auditor]
                          │
                          ▼
            [Text Reconstructor & Cleaner]
                          │
                          ▼
                 [Decoded Document]
```

### 3.1 Formal State Definitions

1. `STATE_BASE`: Default uncontracted state. 
   - Decade 1-3 letters produce lowercase characters `a`–`z`.
   - Punctuation cells produce their standard UEB Grade 1 punctuation symbols.
   - Space cells emit whitespace `' '`.
   - Capital indicator (`⠠`, Dot 6) transitions to `STATE_CAPITAL_NEXT`.
   - Numeric indicator (`⠼`, Dots 3-4-5-6) transitions to `STATE_NUMERIC_MODE`.
   - Grade 1 symbol indicator (`⠰`, Dots 5-6) transitions to `STATE_GRADE1_SYMBOL`.

2. `STATE_CAPITAL_NEXT`: Single capital letter active.
   - If next cell is another Capital indicator (`⠠`, Dot 6): transition to `STATE_CAPITAL_WORD`.
   - If next cell is an alphabet letter: output uppercase letter, transition back to `STATE_BASE`.
   - If next cell is punctuation or space: invalid indicator sequence; output `⠠` placeholder, transition to `STATE_BASE`.

3. `STATE_CAPITAL_WORD`: Capitalized word active (all subsequent letters capitalized).
   - If cell is alphabet letter: output uppercase letter, maintain `STATE_CAPITAL_WORD`.
   - If cell is Capital Terminator (`⠠⠄`, Dots 6, 3): consume terminator, transition to `STATE_BASE`.
   - If cell is whitespace (`' '`), hyphen (`-`), or line break: transition back to `STATE_BASE`.

4. `STATE_NUMERIC_MODE`: Numeric digits active.
   - Cells `a` through `j` map to digits `1` through `0`:
     - `a` (`⠁`) $\to$ `'1'`
     - `b` (`⠃`) $\to$ `'2'`
     - `c` (`⠉`) $\to$ `'3'`
     - `d` (`⠙`) $\to$ `'4'`
     - `e` (`⠑`) $\to$ `'5'`
     - `f` (`⠋`) $\to$ `'6'`
     - `g` (`⠛`) $\to$ `'7'`
     - `h` (`⠓`) $\to$ `'8'`
     - `i` (`⠊`) $\to$ `'9'`
     - `j` (`⠚`) $\to$ `'0'`
   - Comma (`⠂`, Dot 2) is emitted as thousands separator `','` and maintains `STATE_NUMERIC_MODE`.
   - Decimal point (`⠲`, Dots 2-5-6 or `⠨`, Dots 4-6) is emitted as `'.'` and maintains `STATE_NUMERIC_MODE`.
   - Hyphen (`⠤`, Dots 3-6) is emitted as `'-'` and maintains `STATE_NUMERIC_MODE`.
   - Whitespace (`' '`), any non-numeric symbol, or line break terminates numeric mode and transitions to `STATE_BASE`.

5. `STATE_GRADE1_SYMBOL`: Uncontracted symbol enforcement.
   - Suppresses contraction interpretation for the single immediately following cell and returns to `STATE_BASE`.

---

## 4. Full UEB Grade 1 Lookup Tables

### 4.1 Alphabet Table
```python
ALPHABET_MAP = {
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
```

### 4.2 Numeric Table
```python
NUMERIC_MAP = {
    (1, 0, 0, 0, 0, 0): '1',
    (1, 1, 0, 0, 0, 0): '2',
    (1, 0, 0, 1, 0, 0): '3',
    (1, 0, 0, 1, 1, 0): '4',
    (1, 0, 0, 0, 1, 0): '5',
    (1, 1, 0, 1, 0, 0): '6',
    (1, 1, 0, 1, 1, 0): '7',
    (1, 1, 0, 0, 1, 0): '8',
    (0, 1, 0, 1, 0, 0): '9',
    (0, 1, 0, 1, 1, 0): '0',
}
```

### 4.3 Punctuation Table
```python
PUNCTUATION_MAP = {
    (0, 1, 0, 0, 1, 1): '.',   # ⠲ Period / Full stop
    (0, 1, 0, 0, 0, 0): ',',   # ⠂ Comma
    (0, 1, 1, 0, 0, 0): ';',   # ⠆ Semicolon
    (0, 1, 0, 0, 1, 0): ':',   # ⠒ Colon
    (0, 1, 1, 0, 0, 1): '?',   # ⠦ Question mark (or open quote)
    (0, 1, 1, 0, 1, 0): '!',   # ⠖ Exclamation mark
    (0, 0, 1, 0, 0, 1): '-',   # ⠤ Hyphen
    (0, 0, 1, 0, 0, 0): "'",   # ⠄ Apostrophe
    (0, 0, 1, 0, 1, 1): '"',   # ⠴ Close double quote
}
```

---

## 5. Confidence Assessment and Uncertainty Reporting

When optical conditions are degraded (e.g. low-contrast embossing, camera tilt), individual dots may have low prediction probabilities.

### 5.1 Cell Confidence Computation
For a cell whose dot predictions have individual probabilities $p_i \in [0.0, 1.0]$:
$$\text{Confidence}(\text{cell}) = \prod_{i=1}^{6} \max(p_i, 1 - p_i)$$
or the conservative lower bound:
$$\text{Confidence}_{\min}(\text{cell}) = \min_{i=1..6} \max(p_i, 1 - p_i)$$

### 5.2 Uncertainty Thresholding
- **High Confidence ($\ge 0.85$):** Decoded normally without tags.
- **Moderate Confidence ($0.65 \le \text{Conf} < 0.85$):** Decoded normally, but registered in `uncertain_cells` for UI highlighting.
- **Low Confidence ($< 0.65$):** Emitted as unconfirmed character with bracket indicator `[?c]` where `c` is best-guess, allowing human-in-the-loop validation.

---

## 6. Verification Test Cases

The decoder implementation must strictly pass the following verified unit test vectors:

1. **Simple Word:** `⠓⠑⠇⠇⠕` $\to$ `"hello"`
2. **Capitalized Word:** `⠠⠓⠑⠇⠇⠕` $\to$ `"Hello"`
3. **All-Caps Word:** `⠠⠠⠓⠑⠇⠇⠕` $\to$ `"HELLO"`
4. **Sentence with Punctuation:** `⠠⠓⠑⠇⠇⠕⠂⠀⠺⠕⠗⠇⠙⠲` $\to$ `"Hello, world."`
5. **Number Sequence:** `⠼⠃⠚⠃⠑` $\to$ `"2025"`
6. **Alphanumeric Combination:** `⠠⠗⠕⠕⠍⠀⠼⠉⠚⠃` $\to$ `"Room 302"`
7. **Punctuation Sequence:** `⠠⠊⠎⠀⠊⠞⠀⠗⠑⠁⠙⠽⠦` $\to$ `"Is it ready?"`
8. **Grade 2 Warning:** Standalone `⠮` (dots 2-3-4-6) outside Grade 1 indicators triggers a Grade 2 notice.
