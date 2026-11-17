"""
Image Quality Assessment (IQA) for Optical Braille Recognition.
Evaluates blur, illumination, contrast, saturation, and resolution.
"""

from typing import Dict, Any, Tuple
import cv2
import numpy as np


class ImageQualityAssessment:
    """
    Evaluates input Braille image quality against physical and optical thresholds.
    """

    def __init__(
        self,
        min_blur_var: float = 25.0,
        min_brightness: float = 30.0,
        max_brightness: float = 250.0,
        min_contrast: float = 1.5,
        max_saturation_pct: float = 18.0,
        min_dimension: int = 64
    ):
        self.min_blur_var = min_blur_var
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast
        self.max_saturation_pct = max_saturation_pct
        self.min_dimension = min_dimension

    def assess(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Runs comprehensive image quality checks on BGR or Grayscale image.
        Returns a dictionary with metric scores, boolean status, and diagnostic flags.
        """
        if image is None or image.size == 0:
            return {
                "is_usable": False,
                "rejection_reason": "Image is null, empty, or unreadable.",
                "metrics": {}
            }

        h, w = image.shape[:2]

        # Convert to Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Blur Assessment via Laplacian Variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_variance = float(laplacian.var())

        # 2. Dynamic Range & Contrast Metrics
        min_val = float(np.min(gray))
        max_val = float(np.max(gray))
        dynamic_range = max_val - min_val
        mean_brightness = float(np.mean(gray))
        contrast_std = float(np.std(gray))

        # 3. Glare & Saturation Assessment
        saturated_pixels = np.count_nonzero(gray >= 250)
        saturation_pct = float((saturated_pixels / gray.size) * 100.0)

        # 4. Diagnostic Checks
        flags = []
        is_usable = True
        rejection_reasons = []

        # Resolution check (lowered to 64px to easily accommodate cropped words & snippets)
        if min(h, w) < self.min_dimension:
            is_usable = False
            rejection_reasons.append(
                f"Resolution too low ({w}x{h}). Minimum required dimension is {self.min_dimension}px."
            )
            flags.append("LOW_RESOLUTION")

        # Blur Check
        if blur_variance < self.min_blur_var:
            is_usable = False
            rejection_reasons.append(
                f"Image is too blurry (Laplacian variance {blur_variance:.1f} < threshold {self.min_blur_var}). Hold camera steady."
            )
            flags.append("BLURRY")

        # Illumination Assessment (Document-Aware: handles both dark and pure white backgrounds)
        if mean_brightness < self.min_brightness and max_val < 50:
            is_usable = False
            rejection_reasons.append(
                f"Image is severely underexposed (Brightness {mean_brightness:.1f} < {self.min_brightness}). Increase lighting."
            )
            flags.append("TOO_DARK")
        elif mean_brightness > 253.0 and dynamic_range < 12:
            is_usable = False
            rejection_reasons.append(
                f"Image is completely washed out (Solid blank page with no distinguishable dots). Avoid direct glare."
            )
            flags.append("TOO_BRIGHT")

        # Contrast Assessment (only reject if the image is a solid flat color)
        if dynamic_range < 10 and contrast_std < 0.8:
            is_usable = False
            flags.append("LOW_CONTRAST")
            rejection_reasons.append("Insufficient optical contrast to distinguish embossed dots.")
        elif contrast_std < self.min_contrast and dynamic_range < 20:
            flags.append("LOW_CONTRAST")

        # Glare Assessment (Only reject if real specular flare washed out the dots completely)
        if saturation_pct > 80.0 and dynamic_range < 15:
            is_usable = False
            flags.append("SEVERE_GLARE")
            rejection_reasons.append(f"Severe camera flash/glare washed out the dots ({saturation_pct:.1f}% saturated).")
        elif saturation_pct > 40.0 and dynamic_range < 30:
            flags.append("MODERATE_GLARE")

        metrics = {
            "resolution": f"{w}x{h}",
            "width": w,
            "height": h,
            "blur_variance": round(blur_variance, 2),
            "laplacian_variance": round(blur_variance, 2),
            "mean_brightness": round(mean_brightness, 2),
            "mean_intensity": round(mean_brightness, 2),
            "contrast_std": round(contrast_std, 2),
            "glare_pct": round(saturation_pct, 2),
            "quality_flags": flags
        }

        return {
            "is_usable": is_usable,
            "rejection_reason": "; ".join(rejection_reasons) if rejection_reasons else None,
            "metrics": metrics
        }
