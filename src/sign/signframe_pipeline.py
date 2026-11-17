"""
SignFrame AI — End-to-End Real-Time Hand Sign Processing Pipeline.
Integrates MediaPipe HandLandmarker, 25% square bounding-box cropping,
border replication padding, 28x28 grayscale normalization,
CNN letter prediction, temporal stabilization (12 frames / 9 votes),
TextComposer, and offline speech synthesis.
"""

import os
import platform
import shutil
import subprocess
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from src.sign.signframe_model import (
    INDEX_TO_LETTER,
    LETTER_TO_INDEX,
    SIGN_CLASSES,
    TORCH_AVAILABLE,
    VALID_LABELS,
    NumpySignCNN,
)

if TORCH_AVAILABLE:
    import torch
    from src.sign.signframe_model import SignLanguageCNN

IMAGE_SIZE = 28


def get_hand_bbox(landmarks, frame_shape: Tuple[int, int, Any], padding: float = 0.25) -> Tuple[int, int, int, int]:
    """
    Calculate a square bounding box around the detected hand with 25% padding.
    landmarks: list of landmarks with .x and .y attributes normalized to [0, 1].
    frame_shape: (height, width, ...)
    """
    height, width = frame_shape[:2]

    xs = np.array([point.x * width for point in landmarks], dtype=np.float32)
    ys = np.array([point.y * height for point in landmarks], dtype=np.float32)

    min_x, max_x = float(xs.min()), float(xs.max())
    min_y, max_y = float(ys.min()), float(ys.max())

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    hand_width = max_x - min_x
    hand_height = max_y - min_y

    box_size = max(hand_width, hand_height)
    box_size *= (1.0 + padding)
    box_size = max(int(round(box_size)), 80)

    x1 = int(round(center_x - box_size / 2))
    y1 = int(round(center_y - box_size / 2))
    x2 = x1 + box_size
    y2 = y1 + box_size

    return x1, y1, x2, y2


def preprocess_hand(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    Convert the hand region into the CNN's expected input:
      shape: (1, 1, 28, 28)
      dtype: float32
      values: [0, 1]
    Pads outside frame boundaries with border replication.
    """
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = map(int, bbox)

    if x2 <= x1 or y2 <= y1:
        return None

    pad_left = max(0, -x1)
    pad_top = max(0, -y1)
    pad_right = max(0, x2 - width)
    pad_bottom = max(0, y2 - height)

    if any((pad_left, pad_top, pad_right, pad_bottom)):
        padded_frame = cv2.copyMakeBorder(
            frame,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            borderType=cv2.BORDER_REPLICATE
        )
    else:
        padded_frame = frame

    x1 += pad_left
    x2 += pad_left
    y1 += pad_top
    y2 += pad_top

    crop = padded_frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    resized = cv2.resize(gray, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
    normalized = resized.astype(np.float32) / 255.0
    tensor = np.expand_dims(np.expand_dims(normalized, axis=0), axis=0)  # (1, 1, 28, 28)
    return tensor


class HandTracker:
    """
    Tracks hand using MediaPipe HandLandmarker.
    Automatically resolves model path across Transify roots.
    """
    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            # Check candidate locations
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            candidates = [
                Path(os.path.join(project_root, "models/sign/hand_landmarker.task")),
                Path("models/sign/hand_landmarker.task"),
                Path("assets/hand_landmarker.task"),
                Path("scratch/signframe-ai/assets/hand_landmarker.task"),
            ]
            for c in candidates:
                if c.exists():
                    model_path = str(c.resolve())
                    break

        self.landmarker = None
        if model_path and os.path.exists(model_path):
            try:
                import mediapipe as mp
                BaseOptions = mp.tasks.BaseOptions
                HandLandmarker = mp.tasks.vision.HandLandmarker
                HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
                VisionRunningMode = mp.tasks.vision.RunningMode

                options = HandLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=model_path),
                    running_mode=VisionRunningMode.IMAGE,
                    num_hands=2,
                    min_hand_detection_confidence=0.32,
                    min_hand_presence_confidence=0.32,
                    min_tracking_confidence=0.32,
                )
                self.landmarker = HandLandmarker.create_from_options(options)
            except Exception as e:
                print(f"[HandTracker] MediaPipe initialization error: {e}")

    def detect(self, frame: np.ndarray):
        if self.landmarker is None:
            return None
        import mediapipe as mp
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)
        if not result or not result.hand_landmarks:
            return None
        if len(result.hand_landmarks) == 1:
            return result.hand_landmarks[0]
        # Select active hand with largest bounding area
        best_hand = result.hand_landmarks[0]
        max_area = 0.0
        for hand in result.hand_landmarks:
            pts = np.array([[p.x, p.y] for p in hand])
            area = float(np.ptp(pts[:, 0]) * np.ptp(pts[:, 1]))
            if area > max_area:
                max_area = area
                best_hand = hand
        return best_hand

    def close(self):
        if self.landmarker is not None:
            try:
                self.landmarker.close()
            except Exception:
                pass


class SignPredictor:
    """
    SignFrame AI Prediction Engine.
    Prefers native PyTorch with `feedback_candidate.pth`,
    and seamlessly falls back to high-speed vectorized NumPy with `signframe_cnn.npz`.
    """
    def __init__(self, pth_path: Optional[str] = None, npz_path: Optional[str] = None):
        self.device = None
        self.torch_model = None
        self.numpy_model = None

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

        # Resolve PTH path
        if pth_path is None:
            pth_candidates = [
                Path(os.path.join(project_root, "models/sign/feedback_candidate.pth")),
                Path("models/sign/feedback_candidate.pth"),
                Path("models/feedback_candidate.pth"),
                Path("scratch/signframe-ai/models/feedback_candidate.pth"),
            ]
            for c in pth_candidates:
                if c.exists():
                    pth_path = str(c.resolve())
                    break

        # Resolve NPZ path
        if npz_path is None:
            npz_candidates = [
                Path(os.path.join(project_root, "models/sign/signframe_cnn.npz")),
                Path("models/sign/signframe_cnn.npz"),
                Path("models/signframe_cnn.npz"),
            ]
            for c in npz_candidates:
                if c.exists():
                    npz_path = str(c.resolve())
                    break

        # Try loading PyTorch model
        if TORCH_AVAILABLE and pth_path and os.path.exists(pth_path):
            try:
                self.device = torch.device(
                    "cuda" if torch.cuda.is_available() else "cpu"
                )
                self.torch_model = SignLanguageCNN().to(self.device)
                ckpt = torch.load(pth_path, map_location=self.device, weights_only=True)
                if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
                    ckpt = ckpt["model_state_dict"]
                self.torch_model.load_state_dict(ckpt)
                self.torch_model.eval()
            except Exception as e:
                print(f"[SignPredictor] PyTorch load warning: {e}, checking NumPy...")
                self.torch_model = None

        # Load NumPy vectorized engine as primary/backup
        if npz_path and os.path.exists(npz_path):
            try:
                self.numpy_model = NumpySignCNN(npz_path)
            except Exception as e:
                print(f"[SignPredictor] NumPy load warning: {e}")

        if self.torch_model is None and self.numpy_model is None:
            raise FileNotFoundError(f"Neither PyTorch nor NumPy SignFrame model could be loaded. PTH={pth_path}, NPZ={npz_path}")

    def predict(self, image_input: Union[np.ndarray, Any]) -> Tuple[str, float, Dict[str, float]]:
        """
        Runs inference on (1, 1, 28, 28) image array or tensor.
        Returns: (predicted_letter, confidence_float, all_probabilities_dict)
        """
        if image_input is None:
            return "UNKNOWN", 0.0, {}

        # 1. PyTorch inference if available
        if self.torch_model is not None:
            if isinstance(image_input, np.ndarray):
                tensor = torch.from_numpy(image_input).to(self.device)
            else:
                tensor = image_input.to(self.device)

            if tensor.ndim == 3:
                tensor = tensor.unsqueeze(0)

            with torch.inference_mode():
                logits = self.torch_model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        # 2. NumPy inference fallback
        elif self.numpy_model is not None:
            if not isinstance(image_input, np.ndarray):
                arr = image_input.cpu().numpy()
            else:
                arr = image_input
            if arr.ndim == 3:
                arr = np.expand_dims(arr, axis=0)

            logits = self.numpy_model.forward(arr)[0]
            # Numerically stable softmax
            shift = logits - np.max(logits)
            exp = np.exp(shift)
            probs = exp / np.sum(exp)
        else:
            return "UNKNOWN", 0.0, {}

        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        letter = INDEX_TO_LETTER.get(pred_idx, "A")

        all_probs = {
            INDEX_TO_LETTER[i]: round(float(p), 4)
            for i, p in enumerate(probs)
        }
        return letter, confidence, all_probs


class PredictionStabilizer:
    """
    SignFrame AI Prediction Stabilizer:
    12-frame rolling window with 9-vote debounce consensus.
    Requires frame confidence >= threshold (default 0.65).
    """
    def __init__(self, window_size: int = 12, required_votes: int = 9, confidence_threshold: float = 0.65):
        self.window_size = window_size
        self.required_votes = required_votes
        self.confidence_threshold = confidence_threshold
        self.history: deque = deque(maxlen=window_size)

    def update(self, letter: str, confidence: float) -> Tuple[Optional[str], int, int]:
        """
        Appends prediction to rolling window.
        Returns (confirmed_letter, current_votes, required_votes).
        """
        if confidence < self.confidence_threshold or not letter or letter == "UNKNOWN":
            self.history.append(None)
        else:
            self.history.append(letter)

        counts = Counter(item for item in self.history if item is not None)
        if not counts:
            return None, 0, self.required_votes

        best_letter, votes = counts.most_common(1)[0]
        if votes >= self.required_votes:
            return best_letter, votes, self.required_votes

        return None, votes, self.required_votes

    def reset(self):
        self.history.clear()


class TextComposer:
    """
    SignFrame AI Text Composer:
    Builds messages letter by letter with space, backspace, and clear operations.
    """
    def __init__(self):
        self.text = ""

    def append_letter(self, letter: str) -> str:
        if letter:
            self.text += letter
        return self.text

    def add_space(self) -> str:
        self.text += " "
        return self.text

    def backspace(self) -> str:
        self.text = self.text[:-1]
        return self.text

    def clear(self) -> str:
        self.text = ""
        return self.text


class SpeechEngine:
    """
    Offline speech engine bridging to Windows SAPI (System.Speech), macOS 'say', or espeak.
    """
    def __init__(self):
        self.process = None

    def speak(self, text: str) -> Tuple[bool, str]:
        message = text.strip()
        if not message:
            return False, "Compose a message before speaking."

        self.stop()
        system = platform.system()

        try:
            if system == "Darwin":
                command = ["say", message]
            elif system == "Windows":
                safe = message.replace("'", "''")
                script = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$speaker.Speak('{safe}')"
                )
                command = ["powershell", "-NoProfile", "-Command", script]
            elif shutil.which("spd-say"):
                command = ["spd-say", "-w", message]
            elif shutil.which("espeak"):
                command = ["espeak", message]
            else:
                return False, "No offline speech engine available."

            self.process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True, "Speaking message..."
        except Exception as error:
            return False, f"Speech unavailable: {error}"

    def stop(self):
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
            except Exception:
                pass
            self.process = None

    def close(self):
        self.stop()
