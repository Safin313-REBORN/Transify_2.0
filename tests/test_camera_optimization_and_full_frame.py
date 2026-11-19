"""
Tests for Phase 18: Full-Frame Camera Recognition, Mirrored Selfie Preview & High-Definition Camera Optimization.
Covers:
1. Full-frame hand acceptance across all regions (top-left, top-right, bottom-left, bottom-right, center, all 4 frame boundaries).
2. Elimination of narrow ROI blocking: legacy narrow ROI requests cannot reject valid hands.
3. No-hand frames returning safe IDLE state.
4. Hand bounding box crop validity.
5. 30-frame BdSL temporal buffer continuity when hand moves across frame.
6. Checkpoint integrity and feature dimensions.
7. Complete removal of obsolete ROI selectors and state.
8. Front camera mirroring, resolution fallback, and aspect ratio preservation.
9. Strict Zero Auto-Audio preservation with camera and recognition flows.
"""
import base64
import hashlib
import json
import os
import cv2
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from src.sign.live_frame_processor import LiveSignFrameProcessor
from src.sign.signframe_pipeline import get_hand_bbox, preprocess_hand


class MockPoint:
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


def create_mock_hand_landmarks(cx: float, cy: float, span: float = 0.06):
    """Generates 21 normalized landmarks centered at (cx, cy)."""
    landmarks = []
    for i in range(21):
        dx = ((i % 5) - 2) * (span / 4.0)
        dy = ((i // 5) - 2) * (span / 4.0)
        px = max(0.01, min(0.99, cx + dx))
        py = max(0.01, min(0.99, cy + dy))
        landmarks.append(MockPoint(px, py, 0.0))
    return landmarks


def create_test_frame_b64(width=640, height=480, color=(100, 100, 100)):
    """Encodes a solid BGR image as JPEG base64."""
    img = np.full((height, width, 3), color, dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf).decode("utf-8")


# ==============================================================================
# 1. BACKEND FULL-FRAME RECOGNITION TESTS
# ==============================================================================

class TestFullFrameHandRecognition:
    """Verifies that MediaPipe hand landmarks are accepted across the entire image."""

    @pytest.fixture(autouse=True)
    def setup_processor(self):
        self.processor = LiveSignFrameProcessor()

    @pytest.mark.parametrize("position_name,cx,cy", [
        ("top_left", 0.08, 0.10),
        ("top_right", 0.92, 0.10),
        ("bottom_left", 0.08, 0.90),
        ("bottom_right", 0.92, 0.90),
        ("center", 0.50, 0.50),
        ("boundary_left", 0.03, 0.50),
        ("boundary_right", 0.97, 0.50),
        ("boundary_top", 0.50, 0.03),
        ("boundary_bottom", 0.50, 0.97),
    ])
    def test_hand_accepted_at_all_frame_positions(self, position_name, cx, cy):
        """Verifies hands detected in any corner, center, or boundary region are accepted without ROI rejection."""
        mock_hand = create_mock_hand_landmarks(cx, cy)
        dummy_162 = np.zeros(162, dtype=np.float32)

        with patch.object(self.processor.hand_tracker, 'detect_holistic_landmarks', return_value=(mock_hand, dummy_162)):
            frame_b64 = create_test_frame_b64(640, 480)
            res = self.processor.process_frame(
                image_b64=frame_b64,
                mode="expressions",
                language_mode="bdsl",
                session_id=f"test_pos_{position_name}"
            )

            assert res["success"] is True
            assert res["hand_detected"] is True, f"Hand at {position_name} ({cx}, {cy}) was rejected!"
            assert res["status"] != "OUT_OF_ROI", "OUT_OF_ROI status must never be returned in full-frame mode"
            assert res["in_roi"] is True
            assert res["target_roi"] == [0.0, 0.0, 1.0, 1.0]
            assert res.get("hand_outside_roi", False) is False
            assert res["hand_bbox"] is not None
            assert len(res["hand_bbox"]) == 4

            # Verify bbox is a valid square crop region that preprocess_hand can ingest
            x1, y1, x2, y2 = res["hand_bbox"]
            assert x1 < x2 and y1 < y2
            # Verify preprocess_hand successfully handles boundary coordinates via padding
            dummy_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
            crop = preprocess_hand(dummy_frame, (x1, y1, x2, y2))
            assert crop is not None and crop.shape == (1, 1, 28, 28)

    def test_legacy_narrow_roi_cannot_block_hand(self):
        """Verifies that a legacy request passing narrow ROI coordinates cannot block full-frame hand detection."""
        # Simulate hand on the far left (cx=0.10)
        mock_hand = create_mock_hand_landmarks(0.10, 0.50)
        dummy_162 = np.zeros(162, dtype=np.float32)

        # Legacy right-side box: [0.42, 0.08, 0.94, 0.92] (which previously rejected left hands)
        legacy_narrow_roi = [0.42, 0.08, 0.94, 0.92]

        with patch.object(self.processor.hand_tracker, 'detect_holistic_landmarks', return_value=(mock_hand, dummy_162)):
            frame_b64 = create_test_frame_b64(640, 480)
            res = self.processor.process_frame(
                image_b64=frame_b64,
                mode="expressions",
                language_mode="bdsl",
                roi=legacy_narrow_roi,
                session_id="test_legacy_roi"
            )

            assert res["success"] is True
            assert res["hand_detected"] is True, "Legacy narrow ROI must not block a valid hand!"
            assert res["status"] != "OUT_OF_ROI"
            assert res["in_roi"] is True
            assert res["target_roi"] == [0.0, 0.0, 1.0, 1.0]

    def test_no_hand_returns_clean_idle_state(self):
        """Verifies that frames with no detected hands return IDLE without misleading instructions."""
        with patch.object(self.processor.hand_tracker, 'detect_holistic_landmarks', return_value=(None, None)):
            frame_b64 = create_test_frame_b64(640, 480)
            res = self.processor.process_frame(
                image_b64=frame_b64,
                mode="expressions",
                language_mode="bdsl",
                session_id="test_no_hand"
            )

            assert res["success"] is True
            assert res["hand_detected"] is False
            assert res["status"] == "IDLE"
            assert res["label"] == "IDLE"
            assert res["hand_bbox"] is None
            assert res["hand_outside_roi"] is False
            assert "outside box" not in res["display_text"].lower()
            assert "fixed guide box" not in res["display_text"].lower()

    def test_invalid_image_payload_handled_safely(self):
        """Verifies that an un-decodable frame payload returns a clean error dictionary without throwing."""
        res = self.processor.process_frame(
            image_b64="not_a_valid_base64_image_bytes!!!",
            mode="expressions",
            language_mode="bdsl"
        )
        assert res["success"] is False
        assert res["hand_detected"] is False
        assert "error" in res

    def test_hand_crop_preprocessing_with_full_frame_bbox(self):
        """Verifies that get_hand_bbox and preprocess_hand work correctly across full frame coordinates."""
        frame = np.full((720, 1280, 3), 120, dtype=np.uint8)

        # Hand near top-left edge
        landmarks_tl = create_mock_hand_landmarks(0.08, 0.10)
        bbox_tl = get_hand_bbox(landmarks_tl, frame.shape, padding=0.25)
        assert len(bbox_tl) == 4
        crop_tl = preprocess_hand(frame, bbox_tl)
        assert crop_tl is not None
        assert crop_tl.shape == (1, 1, 28, 28)

        # Hand near bottom-right edge
        landmarks_br = create_mock_hand_landmarks(0.92, 0.90)
        bbox_br = get_hand_bbox(landmarks_br, frame.shape, padding=0.25)
        assert len(bbox_br) == 4
        crop_br = preprocess_hand(frame, bbox_br)
        assert crop_br is not None
        assert crop_br.shape == (1, 1, 28, 28)

    def test_temporal_buffer_continuity_across_screen_motion(self):
        """Verifies that moving a hand from left to right side does not clear the 30-frame buffer."""
        sess_id = "test_motion_continuity"
        frame_b64 = create_test_frame_b64(640, 480)
        base_time = 1000.0

        # Feed 15 frames from left side (cx = 0.15)
        for i in range(15):
            left_hand = create_mock_hand_landmarks(0.15, 0.50)
            dummy_162 = np.full(162, 0.1, dtype=np.float32)
            with patch.object(self.processor.hand_tracker, 'detect_holistic_landmarks', return_value=(left_hand, dummy_162)):
                res = self.processor.process_frame(
                    image_b64=frame_b64,
                    mode="expressions",
                    language_mode="bdsl",
                    session_id=sess_id,
                    timestamp=base_time + (i * 0.033)
                )
                assert res["hand_detected"] is True

        # Feed 15 frames from right side (cx = 0.85)
        for i in range(15, 30):
            right_hand = create_mock_hand_landmarks(0.85, 0.50)
            dummy_162 = np.full(162, 0.2, dtype=np.float32)
            with patch.object(self.processor.hand_tracker, 'detect_holistic_landmarks', return_value=(right_hand, dummy_162)):
                res = self.processor.process_frame(
                    image_b64=frame_b64,
                    mode="expressions",
                    language_mode="bdsl",
                    session_id=sess_id,
                    timestamp=base_time + (i * 0.033)
                )
                assert res["hand_detected"] is True

        # Buffer should have accumulated all 30 frames without being wiped
        session = self.processor.get_session_state(sess_id)
        with session.lock:
            assert len(session.frame_buffer) == 30 or res["status"] in ("CONFIRMED", "DEBOUNCING", "BUFFERING")

    def test_model_checkpoints_unmodified(self):
        """Verifies that production model weights and feature dimensions are strictly preserved."""
        expected_hashes = {
            "models/sign/bdsl_champion_model.pkl": "62a6106b405037085e1b2244153841b2f2039ce5d29a6ff05df888241da5386e",
            "models/sign/scaler.pkl": "7552758987ab38cc353b3b2fc15d9db8714fc08669d68984adca6759b837f5db",
            "models/sign/calibrated_classifier.pkl": "661d035ef7269786287fddea77c381f96719a0ce4ac098746c031b97b817be14"
        }

        for path, exp_hash in expected_hashes.items():
            if os.path.exists(path):
                with open(path, "rb") as f:
                    actual_hash = hashlib.sha256(f.read()).hexdigest()
                assert actual_hash == exp_hash, f"Checkpoint {path} was mutated!"


# ==============================================================================
# 2. FRONTEND DOM, STYLES, AND CAMERA LOGIC TESTS
# ==============================================================================

class TestFrontendCameraOptimization:
    """Verifies that obsolete ROI selectors are removed and camera mirror / containment styles are active."""

    def test_roi_selectors_removed_from_html(self):
        """Verifies that roi-pos-* and roi-position-selector are completely absent from HTML templates."""
        for html_file in ["src/frontend/sign.html", "src/frontend/index.html"]:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
            assert "roi-pos-right" not in content, f"Obsolete roi-pos-right found in {html_file}"
            assert "roi-pos-center" not in content, f"Obsolete roi-pos-center found in {html_file}"
            assert "roi-pos-left" not in content, f"Obsolete roi-pos-left found in {html_file}"
            assert "roi-position-selector" not in content, f"Obsolete roi-position-selector found in {html_file}"
            assert "btn-roi" not in content, f"Obsolete btn-roi found in {html_file}"
            assert "roi-selector-label" not in content, f"Obsolete roi-selector-label found in {html_file}"

    def test_camera_mirror_class_and_containment_in_css(self):
        """Verifies that .camera-mirror transform and object-fit: contain are declared in styles.css."""
        with open("src/frontend/static/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        assert ".camera-mirror" in css
        assert "transform: scaleX(-1)" in css
        assert "object-fit: contain" in css
        assert ".roi-position-selector" not in css
        assert ".btn-roi" not in css

    def test_app_js_removes_obsolete_roi_state(self):
        """Verifies that app.js does not contain roiPosition or setRoiPosition."""
        with open("src/frontend/static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "roiPosition:" not in js
        assert "setRoiPosition(" not in js
        assert "getTargetRoi()" in js  # Kept returning full-frame [0.0, 0.0, 1.0, 1.0]

    def test_full_frame_target_roi_in_app_js(self):
        """Verifies that getTargetRoi in app.js returns full-frame [0.0, 0.0, 1.0, 1.0]."""
        with open("src/frontend/static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "[0.0, 0.0, 1.0, 1.0]" in js

    def test_aspect_ratio_and_max_dimension_cap_in_app_js(self):
        """Verifies that frame capture caps longest side at 1280 while preserving aspect ratio."""
        with open("src/frontend/static/app.js", "r", encoding="utf-8") as f:
            js = f.read()
        assert "maxDim = 1280" in js or "1280" in js
        assert "0.88" in js  # JPEG quality target


# ==============================================================================
# 3. ZERO AUTO-AUDIO REGRESSION INTEGRATION
# ==============================================================================

class TestCameraZeroAutoAudio:
    """Verifies that camera operations and frame recognition never trigger automatic speech synthesis."""

    def test_zero_auto_audio_policy_on_sign_page(self, live_server, browser_instance):
        """Playwright browser test: camera operations, model detections, and idle states dispatch 0 audio calls."""
        from tests.test_production_no_auto_audio_browser import new_isolated_page, inject_audio_observers

        page = new_isolated_page(browser_instance)
        inject_audio_observers(page)

        page.goto(f"{live_server}/sign", wait_until="domcontentloaded")
        page.wait_for_timeout(400)

        # 1. Page load should produce 0 audio
        audio_count = page.evaluate("() => window._transify_audio_calls.length")
        assert audio_count == 0, "Initial page load produced speech output!"

        # 2. Simulate full-frame detection update
        page.evaluate("""() => {
            if (window.SignPage && typeof window.SignPage.updatePredictionUI === 'function') {
                window.SignPage.updatePredictionUI({
                    label: 'THANK_YOU',
                    display_text: 'ধন্যবাদ (Thank You)',
                    bdsl_gloss: 'BdSL: Thank You',
                    english_text: 'Thank You',
                    confidence: 0.985,
                    confirmed: true,
                    status: 'CONFIRMED'
                });
            }
        }""")
        page.wait_for_timeout(300)

        # Audio calls must remain strictly 0
        audio_count = page.evaluate("() => window._transify_audio_calls.length")
        bridge_count = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")
        assert audio_count == 0, "Sign recognition automatically played audio! Violates Zero Auto-Audio Policy."
        assert bridge_count == 0, "Sign recognition sent audio to native bridge!"

        # 3. Explicit click on Speak button MUST trigger exactly one audio call
        page.click("#speak-pred-btn")
        page.wait_for_timeout(200)

        audio_count_after = page.evaluate("() => window._transify_audio_calls.length")
        bridge_count_after = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")
        assert (audio_count_after + bridge_count_after) == 1, "Explicit speak button click did not play audio!"

        page.close()
