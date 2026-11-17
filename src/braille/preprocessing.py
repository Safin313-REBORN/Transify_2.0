"""
Image Preprocessing Pipeline for Optical Braille Recognition.
Handles illumination correction, CLAHE, noise reduction, deskewing, and dot enhancement.
"""

from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np


class BrailleImagePreprocessor:
    """
    Robust image preprocessing pipeline tailored for tactile embossed Braille.
    """

    def __init__(
        self,
        clahe_clip_limit: float = 2.5,
        clahe_tile_grid_size: Tuple[int, int] = (8, 8),
        denoise_diameter: int = 5,
        denoise_sigma_color: float = 50.0,
        denoise_sigma_space: float = 50.0,
        target_max_width: int = 1920
    ):
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit,
            tileGridSize=clahe_tile_grid_size
        )
        self.denoise_diameter = denoise_diameter
        self.denoise_sigma_color = denoise_sigma_color
        self.denoise_sigma_space = denoise_sigma_space
        self.target_max_width = target_max_width

    def process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Executes full preprocessing pipeline on input image.
        Returns:
            dict containing:
                'original': original BGR image
                'resized': resized image
                'gray': grayscale image
                'clahe_enhanced': shadow-compensated CLAHE image
                'denoised': edge-preserving filtered image
                'binary': adaptive thresholded dot mask
                'skew_angle': estimated skew angle in degrees
                'deskewed': rotation-corrected image
        """
        h, w = image.shape[:2]

        # 1. Resize if image is excessively large to optimize compute
        scale = 1.0
        if w > self.target_max_width:
            scale = self.target_max_width / float(w)
            target_h = int(h * scale)
            resized = cv2.resize(image, (self.target_max_width, target_h), interpolation=cv2.INTER_AREA)
        else:
            resized = image.copy()

        # 2. Grayscale Conversion & Canonical Polarity Standardization
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized.copy()

        # Canonical Polarity Normalization:
        # In a Braille document, the background occupies >80% of pixels.
        # If the median pixel intensity is dark (< 128), it is an inverted/dark-mode image.
        # We invert it so that background is always light and dots are always dark foreground.
        if float(np.median(gray)) < 128.0:
            gray = 255 - gray

        # 3. Uneven Illumination Estimation & Compensation (Background Division)
        max_k = min(gray.shape[:2]) - 1
        max_k = max_k if max_k % 2 == 1 else max_k - 1
        kernel_size = min(max(int(min(gray.shape) * 0.1) | 1, 15), max(max_k, 3))
        background = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
        # Divide gray by background and normalize to [0, 255]
        norm_illum = np.float32(gray) / (np.float32(background) + 1e-5)
        norm_illum = np.clip(norm_illum * 180.0, 0, 255).astype(np.uint8)

        # 4. Contrast Enhancement via CLAHE
        clahe_enhanced = self.clahe.apply(norm_illum)

        # 5. Edge-Preserving Denoising (Bilateral Filter)
        denoised = cv2.bilateralFilter(
            clahe_enhanced,
            d=self.denoise_diameter,
            sigmaColor=self.denoise_sigma_color,
            sigmaSpace=self.denoise_sigma_space
        )

        # 6. Skew Detection & Rotation Correction
        skew_angle = self.estimate_skew(denoised)
        if abs(skew_angle) > 0.4 and abs(skew_angle) < 45.0:
            deskewed_gray = self.rotate_image(denoised, skew_angle)
            deskewed_bgr = self.rotate_image(resized, skew_angle)
            deskewed_raw_gray = self.rotate_image(gray, skew_angle)
        else:
            deskewed_gray = denoised
            deskewed_bgr = resized
            deskewed_raw_gray = gray
            skew_angle = 0.0

        # 7. Dual-Mode Binarization
        # For high-contrast digital Braille graphics and crisp scans, Otsu's threshold
        # cleanly isolates compact dot contours without introducing local halo artifacts.
        _, binary_otsu = cv2.threshold(deskewed_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        otsu_ratio = float(np.count_nonzero(binary_otsu)) / float(binary_otsu.size)

        if 0.0005 <= otsu_ratio <= 0.20:
            binary = binary_otsu
        else:
            # Fall back to adaptive Gaussian thresholding for unevenly illuminated embossed paper
            binary = cv2.adaptiveThreshold(
                deskewed_gray,
                maxValue=255,
                adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                thresholdType=cv2.THRESH_BINARY_INV,
                blockSize=15,
                C=4
            )

        # Morphological opening to remove tiny isolated salt-and-pepper noise
        morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, morph_kernel)

        return {
            "original": image,
            "resized": resized,
            "gray": gray,
            "clahe_enhanced": clahe_enhanced,
            "denoised": denoised,
            "skew_angle": round(float(skew_angle), 2),
            "deskewed_gray": deskewed_gray,
            "deskewed_bgr": deskewed_bgr,
            "deskewed_raw_gray": deskewed_raw_gray,
            "binary": binary,
            "scale_factor": scale
        }

    def estimate_skew(self, gray: np.ndarray) -> float:
        """
        Estimates document skew angle using morphological horizontal line projection.
        """
        # Sobel horizontal gradient to detect horizontal alignment of Braille lines
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=15)

        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            line_flat = np.squeeze(line)
            if line_flat.shape == (4,):
                x1, y1, x2, y2 = line_flat
            else:
                continue
            dx = x2 - x1
            dy = y2 - y1
            if dx != 0:
                angle_deg = np.degrees(np.arctan2(dy, dx))
                # Only consider lines close to horizontal (-30 to +30 degrees)
                if abs(angle_deg) < 30.0:
                    angles.append(angle_deg)

        if len(angles) == 0:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    @staticmethod
    def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
        """Rotates image around its center by angle degrees with border replication."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, rot_mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return rotated
