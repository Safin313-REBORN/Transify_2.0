"""
SignFrame AI — Neural Network Architectures and Label Definitions.
Supports both PyTorch SignLanguageCNN and a vectorized NumPy forward pass engine
trained on Sign Language MNIST (24 ASL fingerspelling classes).
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

# ASL Fingerspelling: 24 static letters (A-Y excluding J at idx 9 and Z at idx 25)
VALID_LABELS = [i for i in range(26) if i not in (9, 25)]
LABEL_TO_INDEX = {label: index for index, label in enumerate(VALID_LABELS)}
INDEX_TO_LETTER = {index: chr(ord("A") + label) for index, label in enumerate(VALID_LABELS)}

# Metadata for each class
SIGN_CLASSES: Dict[int, Dict[str, str]] = {
    idx: {
        "label": INDEX_TO_LETTER[idx],
        "display": f"Letter {INDEX_TO_LETTER[idx]}",
        "gloss": INDEX_TO_LETTER[idx],
        "desc": f"ASL fingerspelling letter {INDEX_TO_LETTER[idx]}"
    }
    for idx in range(len(VALID_LABELS))
}

LETTER_TO_INDEX = {INDEX_TO_LETTER[idx]: idx for idx in range(len(VALID_LABELS))}


try:
    import torch
    import torch.nn as nn

    class SignLanguageCNN(nn.Module):
        """
        PyTorch CNN Architecture from SignFrame AI:
          Conv2d(1, 32, 3, pad=1) -> ReLU -> MaxPool2d(2)
          Conv2d(32, 64, 3, pad=1) -> ReLU -> MaxPool2d(2)
          Flatten -> Linear(64*7*7, 128) -> ReLU -> Dropout(0.3) -> Linear(128, 24)
        """
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=2)
            )
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64 * 7 * 7, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 24)
            )

        def forward(self, x):
            x = self.features(x)
            x = self.classifier(x)
            return x

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    SignLanguageCNN = None


class NumpySignCNN:
    """
    Pure NumPy vectorized ConvNet executor for SignFrame AI.
    Runs in < 1ms on CPU with zero external C/CUDA dependencies.
    Provides identical mathematical predictions to PyTorch.
    """
    def __init__(self, npz_path: Union[str, Path]):
        data = np.load(npz_path)
        # Support both PyTorch state_dict keys and simplified keys
        self.conv1_w = data.get("conv1_w", data.get("features.0.weight"))
        self.conv1_b = data.get("conv1_b", data.get("features.0.bias"))
        self.conv2_w = data.get("conv2_w", data.get("features.3.weight"))
        self.conv2_b = data.get("conv2_b", data.get("features.3.bias"))
        self.fc1_w = data.get("fc1_w", data.get("classifier.1.weight"))
        self.fc1_b = data.get("fc1_b", data.get("classifier.1.bias"))
        self.fc2_w = data.get("fc2_w", data.get("classifier.4.weight"))
        self.fc2_b = data.get("fc2_b", data.get("classifier.4.bias"))

    @staticmethod
    def _im2col(x: np.ndarray, kh: int, kw: int, padding: int = 1) -> np.ndarray:
        N, C, H, W = x.shape
        out_h = H + 2 * padding - kh + 1
        out_w = W + 2 * padding - kw + 1
        x_padded = np.pad(x, ((0, 0), (0, 0), (padding, padding), (padding, padding)), mode='constant')
        cols = np.zeros((N, C, kh, kw, out_h, out_w), dtype=np.float32)
        for y in range(kh):
            for x_idx in range(kw):
                cols[:, :, y, x_idx, :, :] = x_padded[:, :, y:y + out_h, x_idx:x_idx + out_w]
        cols = cols.transpose(0, 4, 5, 1, 2, 3).reshape(N * out_h * out_w, C * kh * kw)
        return cols, out_h, out_w

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        x: (N, 1, 28, 28) normalized float32 [0, 1].
        Returns: logits (N, 24).
        """
        N = x.shape[0]

        # Conv1: (N, 1, 28, 28) -> (N, 32, 28, 28)
        cols1, out_h1, out_w1 = self._im2col(x, 3, 3, padding=1)
        w1_row = self.conv1_w.reshape(32, -1)
        out1 = (cols1 @ w1_row.T + self.conv1_b).reshape(N, out_h1, out_w1, 32).transpose(0, 3, 1, 2)
        out1 = np.maximum(0, out1)  # ReLU

        # MaxPool 2x2: (N, 32, 28, 28) -> (N, 32, 14, 14)
        pool1 = out1.reshape(N, 32, 14, 2, 14, 2).max(axis=(3, 5))

        # Conv2: (N, 32, 14, 14) -> (N, 64, 14, 14)
        cols2, out_h2, out_w2 = self._im2col(pool1, 3, 3, padding=1)
        w2_row = self.conv2_w.reshape(64, -1)
        out2 = (cols2 @ w2_row.T + self.conv2_b).reshape(N, out_h2, out_w2, 64).transpose(0, 3, 1, 2)
        out2 = np.maximum(0, out2)  # ReLU

        # MaxPool 2x2: (N, 64, 14, 14) -> (N, 64, 7, 7)
        pool2 = out2.reshape(N, 64, 7, 2, 7, 2).max(axis=(3, 5))

        # Flatten -> (N, 64 * 7 * 7 = 3136)
        flat = pool2.reshape(N, -1)

        # FC1: (N, 3136) -> (N, 128)
        fc1 = np.maximum(0, flat @ self.fc1_w.T + self.fc1_b)

        # FC2: (N, 128) -> (N, 24)
        logits = fc1 @ self.fc2_w.T + self.fc2_b
        return logits
