"""
Transify — AI/LLM Continuous Sentence Builder & Grammar Smoother.
Accumulates sequential sign language tokens and transforms them into fluent,
grammatically complete, and polite English sentences for speech playback.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger("Transify.SentenceBuilder")


class SentenceBuilder:
    """
    Transforms sequential sign language glosses (e.g. ['HELLO', 'I_NEED_HELP', 'WATER'])
    into natural spoken sentences (e.g. 'Hello, I need some help getting water, please.')
    """

    def __init__(self):
        self.tokens: List[str] = []
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.chatgpt_model = os.getenv("CHATGPT_MODEL", "gpt-4o-mini").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def add_token(self, token: str) -> List[str]:
        """Appends a new recognized sign or spelled word to the active sentence buffer."""
        clean = token.strip()
        if clean and (not self.tokens or self.tokens[-1] != clean):
            self.tokens.append(clean)
        return self.tokens

    def clear(self):
        """Resets the token buffer."""
        self.tokens.clear()

    def get_tokens(self) -> List[str]:
        return list(self.tokens)

    def smooth_sentence(self, tokens: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Synthesizes a natural, fluent English sentence from accumulated sign tokens.
        """
        target_tokens = tokens if tokens is not None else self.tokens
        if not target_tokens:
            return {
                "success": False,
                "sentence": "",
                "raw_tokens": [],
                "engine": "NONE",
                "notes": "No sign tokens available to smooth."
            }

        # Check for live cloud LLM (ChatGPT / Gemini)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

        # 1. Try ChatGPT if OPENAI_API_KEY is configured
        if self.openai_api_key:
            res = self._smooth_with_chatgpt(target_tokens)
            if res and res.get("success"):
                return res

        # 2. Try Gemini if GEMINI_API_KEY is configured
        if self.gemini_api_key:
            res = self._smooth_with_gemini(target_tokens)
            if res and res.get("success"):
                return res

        # 3. Deterministic Local Linguistic Synthesizer (Zero-Latency / Offline)
        return self._smooth_with_local_grammar(target_tokens)

    def _smooth_with_chatgpt(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Uses OpenAI ChatGPT to construct a natural sentence from sign glosses."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            tokens_str = ", ".join(f"'{t}'" for t in tokens)
            system_prompt = (
                "You are an assistive communication translator for a speech-impaired individual using Sign Language. "
                f"The person communicated the following sequential sign concepts: [{tokens_str}].\n\n"
                "Task: Construct a natural, grammatically correct, fluent English sentence expressing their complete thought "
                "in first-person ('I'), suitable for text-to-speech audio playback to a hearing listener.\n"
                "Rules:\n"
                "- Output ONLY the final spoken sentence.\n"
                "- Keep it concise, natural, polite, and directly expressing the signed concepts.\n"
                "- Do not include explanations, quotes, or conversational preamble."
            )

            payload = {
                "model": self.chatgpt_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Convert sign concepts [{tokens_str}] to a natural spoken sentence."}
                ],
                "temperature": 0.2,
                "max_tokens": 128
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                sentence = data["choices"][0]["message"]["content"].strip().strip('"\'')
                return {
                    "success": True,
                    "sentence": sentence,
                    "raw_tokens": tokens,
                    "engine": "CHATGPT_SMOOTHER",
                    "source": f"ChatGPT ({self.chatgpt_model}) Sentence Builder",
                    "notes": "Synthesized with cloud conversational AI."
                }
            return None
        except Exception as ex:
            logger.error(f"Error calling ChatGPT sentence smoother: {ex}")
            return None

    def _smooth_with_gemini(self, tokens: List[str]) -> Optional[Dict[str, Any]]:
        """Uses Google Gemini to smooth sign glosses into speech."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            headers = {"Content-Type": "application/json"}
            tokens_str = ", ".join(tokens)
            prompt = (
                f"Convert these sign language keywords into one natural spoken English sentence: [{tokens_str}]. "
                f"Return ONLY the sentence."
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                sentence = data["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"\'')
                return {
                    "success": True,
                    "sentence": sentence,
                    "raw_tokens": tokens,
                    "engine": "GEMINI_SMOOTHER",
                    "source": "Gemini 1.5 Flash Sentence Builder",
                    "notes": "Synthesized with Gemini multimodal AI."
                }
            return None
        except Exception as ex:
            logger.error(f"Error calling Gemini sentence smoother: {ex}")
            return None

    def _smooth_with_local_grammar(self, tokens: List[str]) -> Dict[str, Any]:
        """
        High-precision rule-based local grammar synthesizer.
        Combines common conversational, medical, and emergency sign sequences smoothly.
        """
        token_map = {
            "HELLO": "Hello",
            "THANK_YOU": "Thank you",
            "YOURE_WELCOME": "You are welcome",
            "PLEASE": "please",
            "I_NEED_HELP": "I need help",
            "YES": "Yes",
            "NO": "No",
            "OKAY": "Okay",
            "OK": "Okay",
            "STOP": "Please stop",
            "LIKE": "I like this",
            "DISLIKE": "I do not like this",
            "CALL": "Please call me",
            "PEACE": "Peace and victory",
            "PEACE_INVERTED": "Peace",
            "PALM": "Hello",
            "FIST": "I stand strong",
            "ROCK": "Rock on",
            "MUTE": "Please be quiet",
            "ONE": "One",
            "TWO_UP": "Two",
            "THREE": "Three",
            "THREE2": "Three",
            "FOUR": "Four",
            "I_DONT_UNDERSTAND": "I do not understand",
            "WATER": "some water",
            "FOOD": "food",
            "DOCTOR": "a doctor",
            "HOSPITAL": "the hospital",
            "PAIN": "I am in pain",
            "RESTROOM": "the restroom",
            "WHERE": "Where is",
            "MY_NAME": "My name is"
        }

        # Human-readable phrases
        phrases = [token_map.get(t.upper(), t.capitalize()) for t in tokens]

        # Case 1: Single token
        if len(phrases) == 1:
            sentence = phrases[0]
            if not sentence.endswith((".", "!", "?")):
                sentence += "."
            return {
                "success": True,
                "sentence": sentence,
                "raw_tokens": tokens,
                "engine": "LOCAL_GRAMMAR",
                "source": "Local Linguistic Synthesizer",
                "notes": "Local deterministic rule synthesizer."
            }

        # Case 2: Greeting + Request / Questions
        lower_tokens = [t.upper() for t in tokens]

        if "HELLO" in lower_tokens and "I_NEED_HELP" in lower_tokens and "WATER" in lower_tokens:
            sentence = "Hello, I urgently need help getting some water, please."
        elif "HELLO" in lower_tokens and "I_NEED_HELP" in lower_tokens:
            sentence = "Hello, I urgently need help."
        elif "PLEASE" in lower_tokens and any(item in lower_tokens for item in ["WATER", "FOOD"]):
            item = "some water" if "WATER" in lower_tokens else "some food"
            sentence = f"Could you please give me {item}?"
        elif "WHERE" in lower_tokens and any(place in lower_tokens for place in ["DOCTOR", "HOSPITAL", "RESTROOM"]):
            place = "the restroom" if "RESTROOM" in lower_tokens else ("the hospital" if "HOSPITAL" in lower_tokens else "a doctor")
            sentence = f"Excuse me, where can I find {place}?"
        elif "PAIN" in lower_tokens and "DOCTOR" in lower_tokens:
            sentence = "I am experiencing pain and need to see a doctor."
        elif "THANK_YOU" in lower_tokens:
            other = [p for p in phrases if "Thank you" not in p]
            if other:
                sentence = f"Thank you, {' '.join(other).lower()}."
            else:
                sentence = "Thank you very much."
        elif all(" " not in t and "_" not in t for t in tokens):
            # Sequence of spelled words (e.g. ['MY', 'NAME', 'IS', 'SARAH'])
            word_list = []
            for i, p in enumerate(phrases):
                if i == 0 and p in ["Hello", "Please", "Thank you", "Yes", "No"]:
                    word_list.append(p + ",")
                elif i > 0 and p not in ["I", "I'm"]:
                    word_list.append(p.lower())
                else:
                    word_list.append(p)
            sentence = " ".join(word_list)
            if not sentence.endswith((".", "!", "?")):
                sentence += "."
        else:
            # Hybrid concepts and words
            parts = []
            for i, p in enumerate(phrases):
                if i == 0 and p in ["Hello", "Please", "Thank you", "Yes", "No"]:
                    parts.append(p + ",")
                elif i > 0 and p not in ["I", "I'm", "I need help"]:
                    parts.append(p.lower())
                else:
                    parts.append(p)
            sentence = " ".join(parts)
            if not sentence.endswith((".", "!", "?")):
                sentence += "."

        # Capitalize first letter
        if sentence:
            sentence = sentence[0].upper() + sentence[1:]

        return {
            "success": True,
            "sentence": sentence,
            "raw_tokens": tokens,
            "engine": "LOCAL_GRAMMAR",
            "source": "Local Linguistic Synthesizer (Set OPENAI_API_KEY in .env for Live AI Smoothing)",
            "notes": "Generated by local grammar rule engine."
        }
