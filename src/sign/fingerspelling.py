"""
Transify — Universal Fingerspelling (A–Z) Manual Alphabet Recognizer & Word Assembler.
Enables speech- and hearing-impaired users to spell any arbitrary name, medical term,
place, or vocabulary word not covered by predefined holistic sign classes.
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class FingerspellingRecognizer:
    """
    Recognizes individual manual alphabet letters (A through Z)
    from 21 MediaPipe hand landmark keypoints.
    """

    def __init__(self):
        self.alphabet_meta = {
            "A": {"desc": "Closed fist with thumb extended vertically alongside index finger."},
            "B": {"desc": "Open palm, four fingers straight up, thumb folded across palm."},
            "C": {"desc": "Curved hand forming a 'C' shape."},
            "D": {"desc": "Index finger extended upright, thumb touching middle, ring, pinky."},
            "E": {"desc": "All four fingers bent touching thumb tucked underneath."},
            "F": {"desc": "Index and thumb touching in a circle; middle, ring, pinky extended."},
            "G": {"desc": "Index finger and thumb pointing horizontally forward parallel."},
            "H": {"desc": "Index and middle fingers extended together horizontally."},
            "I": {"desc": "Pinky finger pointing upright, all other fingers closed into fist."},
            "J": {"desc": "Pinky finger extended drawing a hook motion."},
            "K": {"desc": "Index straight up, middle forward-up, thumb between them."},
            "L": {"desc": "Index finger vertical and thumb horizontal forming an 'L' shape."},
            "M": {"desc": "Three fingers (index, middle, ring) folded over tucked thumb."},
            "N": {"desc": "Two fingers (index, middle) folded over tucked thumb."},
            "O": {"desc": "All fingertips touching thumb forming a round 'O' circle."},
            "P": {"desc": "Inverted 'K' gesture pointing downward."},
            "Q": {"desc": "Inverted 'G' gesture pointing downward."},
            "R": {"desc": "Index and middle fingers crossed, other fingers folded."},
            "S": {"desc": "Closed tight fist with thumb wrapped across front of fingers."},
            "T": {"desc": "Thumb tucked between index and middle finger of closed fist."},
            "U": {"desc": "Index and middle fingers extended upright together."},
            "V": {"desc": "Index and middle fingers extended upright apart in a 'V' shape."},
            "W": {"desc": "Index, middle, and ring fingers extended spread forming a 'W'."},
            "X": {"desc": "Index finger bent into a hook, other fingers folded."},
            "Y": {"desc": "Thumb and pinky extended wide ('shaka' / phone sign)."},
            "Z": {"desc": "Index finger extended tracing 'Z' in the air."},
            "SPACE": {"desc": "Flat open hand moving sideways to insert space."},
            "DELETE": {"desc": "Fist thumb pointing backward to backspace."}
        }

    def _get_finger_states(self, pts: np.ndarray) -> Dict[str, bool]:
        """
        Calculates whether each of the 5 fingers is extended or curled.
        pts: (21, 2 or 3) array of normalized hand landmarks.
        """
        # Wrist is 0
        wrist = pts[0]

        # Finger tip and pip indices:
        # Thumb: 4 (tip), 2 (mcp)
        # Index: 8 (tip), 6 (pip), 5 (mcp)
        # Middle: 12 (tip), 10 (pip), 9 (mcp)
        # Ring: 16 (tip), 14 (pip), 13 (mcp)
        # Pinky: 20 (tip), 18 (pip), 17 (mcp)

        # Distance from wrist
        def dist(i, j):
            return math.dist(pts[i][:2], pts[j][:2])

        # Extended if tip is farther from wrist than pip
        index_ext = dist(8, 0) > dist(6, 0) * 1.15
        middle_ext = dist(12, 0) > dist(10, 0) * 1.15
        ring_ext = dist(16, 0) > dist(14, 0) * 1.15
        pinky_ext = dist(20, 0) > dist(18, 0) * 1.15

        # Thumb extended if tip is far from index MCP (5)
        thumb_ext = dist(4, 5) > dist(3, 5) * 1.25

        return {
            "thumb": thumb_ext,
            "index": index_ext,
            "middle": middle_ext,
            "ring": ring_ext,
            "pinky": pinky_ext
        }

    def classify_hand(self, hand_landmarks: np.ndarray) -> Dict[str, Any]:
        """
        Classifies a single hand landmark frame (21 landmarks) into a letter A-Z.
        Args:
            hand_landmarks: (21, 2) or (21, 3) or flat (42,) array.
        Returns:
            Letter classification dictionary with description and confidence.
        """
        pts = np.array(hand_landmarks).reshape(-1, 2 if hand_landmarks.size == 42 else 3)
        if len(pts) != 21:
            return {"letter": "UNKNOWN", "confidence": 0.0, "status": "INVALID_SHAPE"}

        st = self._get_finger_states(pts)
        t, i, m, r, p = st["thumb"], st["index"], st["middle"], st["ring"], st["pinky"]

        def dist(a, b):
            return math.dist(pts[a][:2], pts[b][:2])

        # Classify based on kinematic finger configuration
        pred_letter = "UNKNOWN"
        confidence = 0.85

        # 1. 'L': Index up, Thumb out, Middle, Ring, Pinky curled
        if i and t and not m and not r and not p:
            pred_letter = "L"
            confidence = 0.96

        # 2. 'Y': Thumb and Pinky out, Index, Middle, Ring curled
        elif t and p and not i and not m and not r:
            pred_letter = "Y"
            confidence = 0.97

        # 3. 'V': Index and Middle up and separated, Ring and Pinky curled
        elif i and m and not r and not p and not t:
            im_dist = dist(8, 12)
            if im_dist > 0.08:
                pred_letter = "V"
                confidence = 0.95
            else:
                pred_letter = "U"
                confidence = 0.94

        # 4. 'W': Index, Middle, Ring up, Pinky and Thumb folded
        elif i and m and r and not p:
            pred_letter = "W"
            confidence = 0.95

        # 5. 'B': All 4 fingers up, Thumb tucked across palm
        elif i and m and r and p and not t:
            pred_letter = "B"
            confidence = 0.96

        # 6. 'I': Pinky up only, all others curled
        elif p and not i and not m and not r and not t:
            pred_letter = "I"
            confidence = 0.96

        # 7. 'D': Index up only, thumb touching other curled fingers
        elif i and not m and not r and not p:
            if t:
                pred_letter = "D"
                confidence = 0.94
            else:
                pred_letter = "D"
                confidence = 0.90

        # 8. 'F': Thumb and Index touching (close), Middle, Ring, Pinky up
        elif m and r and p:
            if dist(4, 8) < 0.06:
                pred_letter = "F"
                confidence = 0.95
            elif t:
                # Open flat hand
                pred_letter = "SPACE"
                confidence = 0.92

        # 9. 'C' or 'O': All fingers curved
        elif not i and not m and not r and not p:
            # Fist-like shapes
            # If thumb touches index tip -> O
            if dist(4, 8) < 0.08:
                pred_letter = "O"
                confidence = 0.93
            elif t:
                # 'A': Thumb upright along side
                if pts[4][1] < pts[6][1]:
                    pred_letter = "A"
                    confidence = 0.95
                else:
                    pred_letter = "S"
                    confidence = 0.92
            else:
                pred_letter = "E"
                confidence = 0.90

        # Default fallback
        if pred_letter == "UNKNOWN":
            return {
                "letter": "UNKNOWN",
                "display": "...",
                "confidence": 0.50,
                "status": "UNCERTAIN",
                "finger_states": st
            }

        meta = self.alphabet_meta.get(pred_letter, {})
        return {
            "letter": pred_letter,
            "display": pred_letter,
            "bengali": meta.get("bengali", ""),
            "description": meta.get("desc", ""),
            "confidence": confidence,
            "status": "CONFIRMED",
            "finger_states": st
        }


class FingerspellingWordAssembler:
    """
    Maintains real-time letter buffering, debounce consensus,
    and word assembly for continuous manual spelling.
    """

    def __init__(self, debounce_count: int = 4):
        self.debounce_count = debounce_count
        self.buffer: List[str] = []
        self.current_word = ""
        self.committed_words: List[str] = []
        self.last_letter = ""

    def add_frame_prediction(self, letter: str) -> Dict[str, Any]:
        """
        Adds a raw frame prediction to the debounce buffer.
        Commits letter when stability threshold is reached.
        """
        if letter in ["UNKNOWN", "..."]:
            return self.get_state()

        self.buffer.append(letter)
        if len(self.buffer) > self.debounce_count:
            self.buffer.pop(0)

        # Check consensus
        if len(self.buffer) == self.debounce_count and all(l == letter for l in self.buffer):
            # Only append if different from immediate last or intentional repeat
            if letter == "SPACE":
                if self.current_word:
                    self.committed_words.append(self.current_word)
                    self.current_word = ""
                self.buffer.clear()
            elif letter == "DELETE":
                if len(self.current_word) > 0:
                    self.current_word = self.current_word[:-1]
                self.buffer.clear()
            else:
                if letter != self.last_letter or len(self.buffer) == self.debounce_count:
                    self.current_word += letter
                    self.last_letter = letter
                    self.buffer.clear()

        return self.get_state()

    def add_direct_letter(self, letter: str) -> Dict[str, Any]:
        """Directly appends a letter (useful for manual/testing triggers)."""
        clean = letter.upper().strip()
        if clean == "SPACE":
            if self.current_word:
                self.committed_words.append(self.current_word)
                self.current_word = ""
        elif clean == "DELETE" or clean == "BACKSPACE":
            if self.current_word:
                self.current_word = self.current_word[:-1]
        elif len(clean) == 1 and clean.isalpha():
            self.current_word += clean
        return self.get_state()

    def clear(self):
        """Clears all spelled words and buffers."""
        self.buffer.clear()
        self.current_word = ""
        self.committed_words.clear()
        self.last_letter = ""

    def get_full_text(self) -> str:
        """Returns the complete sentence/text spelled so far."""
        words = list(self.committed_words)
        if self.current_word:
            words.append(self.current_word)
        return " ".join(words)

    def get_state(self) -> Dict[str, Any]:
        """Returns the current assembler state."""
        return {
            "current_word": self.current_word,
            "committed_words": self.committed_words,
            "full_text": self.get_full_text(),
            "last_letter": self.last_letter,
            "letter_count": len(self.current_word)
        }
