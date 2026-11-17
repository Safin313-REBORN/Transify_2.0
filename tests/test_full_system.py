"""
Comprehensive End-to-End System Test Suite for Transify Platform.
Tests all FastAPI endpoints, AI model adapters, database persistence,
audio synthesis, sample delivery, and accessible frontend rendering.
"""

import os
import sys
import unittest
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import Response

from src.api.server import (
    app,
    health_check,
    readiness_check,
    models_status,
    get_sign_classes,
    predict_sign_sequence,
    reset_sign_buffer,
    check_image_quality,
    translate_braille_file,
    synthesize_speech,
    list_history,
    delete_all_history,
    submit_feedback,
    read_preferences,
    set_preference,
    get_sign_sample,
    list_braille_samples,
    serve_landing_page,
    serve_login_page,
    serve_dashboard_page,
    serve_sign_page,
    serve_braille_page,
    SignPredictRequest,
    TTSRequest,
    PreferenceUpdateRequest,
    FeedbackRequest
)
from src.database.db import (
    log_translation,
    get_history,
    record_feedback,
    clear_history,
    get_preferences,
    update_preference
)
from src.api.sign_adapter import SignLanguageAdapter, BDSL_CLASSES
from src.api.braille_adapter import BrailleRecognitionAdapter
from src.api.tts_engine import TTSService


class TestSystemHealthAndMeta(unittest.TestCase):
    """Verifies system health, status, and model metadata."""

    def test_health_check(self):
        res = health_check()
        self.assertEqual(res["status"], "healthy")
        self.assertEqual(res["platform"], "Transify Assistive Platform")
        self.assertIn("timestamp", res)
        self.assertIn("python_version", res)

    def test_readiness_check(self):
        resp = Response()
        res = readiness_check(resp)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("subsystems", res)
        self.assertEqual(res["subsystems"]["database"], "connected")
        self.assertEqual(res["subsystems"]["sign_language"], "ready")
        self.assertEqual(res["subsystems"]["braille_ocr"], "ready")
        self.assertEqual(res["subsystems"]["tts"], "ready")

    def test_readiness_failure_simulation(self):
        from unittest.mock import patch
        resp = Response()
        with patch("src.api.server.get_connection", side_effect=Exception("DB Failure")):
            res = readiness_check(resp)
            self.assertEqual(res["status"], "degraded")
            self.assertEqual(resp.status_code, 503)
            self.assertEqual(res["subsystems"]["database"], "error")

    def test_model_status(self):
        res = models_status()
        # Verify four separate decomposed components
        self.assertIn("signframe_asl", res)
        self.assertEqual(res["signframe_asl"]["supported_classes"], 26)
        self.assertTrue(res["signframe_asl"]["ready"])

        self.assertIn("hagrid_gestures", res)
        self.assertEqual(res["hagrid_gestures"]["test_accuracy"], 0.8683)
        self.assertGreaterEqual(res["hagrid_gestures"]["supported_classes"], 20)
        self.assertTrue(res["hagrid_gestures"]["ready"])

        self.assertIn("mediapipe_landmarker", res)
        self.assertEqual(res["mediapipe_landmarker"]["keypoints"], 21)

        self.assertIn("braille_obr", res)
        self.assertEqual(res["braille_obr"]["test_cell_accuracy"], 1.0)
        self.assertEqual(res["braille_obr"]["metric_scope"], "cell-level")
        self.assertTrue(res["braille_obr"]["ready"])

        # Backward compatibility checks
        self.assertTrue(res["sign_language"]["ready"])
        self.assertEqual(res["sign_language"]["test_accuracy"], 0.8683)
        self.assertTrue(res["braille_ocr"]["ready"])
        self.assertEqual(res["braille_ocr"]["test_cell_accuracy"], 1.0)

    def test_cors_middleware_configuration(self):
        from fastapi.middleware.cors import CORSMiddleware
        cors_middlewares = [m for m in app.user_middleware if m.cls == CORSMiddleware]
        self.assertTrue(len(cors_middlewares) > 0)
        cors_options = cors_middlewares[0].kwargs
        self.assertIn("https://transify20-production.up.railway.app", cors_options["allow_origins"])
        self.assertNotIn("*", cors_options["allow_origins"])

    def test_sign_classes(self):
        res = get_sign_classes()
        self.assertEqual(res["vocabulary_count"], 10)
        labels = [c["label"] for c in res["classes"]]
        self.assertIn("HELLO", labels)
        self.assertIn("THANK_YOU", labels)
        self.assertIn("STOP", labels)
        self.assertIn("I_NEED_HELP", labels)


class TestDatabasePersistence(unittest.TestCase):
    """Verifies SQLite storage, feedback updates, and preferences."""

    def setUp(self):
        clear_history()

    def test_log_and_retrieve_history(self):
        rec_id = log_translation(
            module="sign",
            recognized_text="HELLO",
            confidence=0.98,
            status="CONFIRMED",
            input_meta={"signer": "test_user"}
        )
        self.assertIsInstance(rec_id, int)

        history = get_history(limit=5)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["recognized_text"], "HELLO")
        self.assertEqual(history[0]["confidence"], 0.98)

    def test_feedback_submission(self):
        rec_id = log_translation(
            module="braille",
            recognized_text="Hello world.",
            confidence=0.99,
            status="SUCCESS"
        )
        updated = record_feedback(rec_id, rating=5, comments="Accurate translation")
        self.assertTrue(updated)

        history = get_history(limit=1)
        self.assertEqual(history[0]["feedback_rating"], 5)
        self.assertEqual(history[0]["feedback_comments"], "Accurate translation")

    def test_preferences_update(self):
        update_preference("theme", "high-contrast")
        update_preference("font_size", "xlarge")
        prefs = get_preferences()
        self.assertEqual(prefs.get("theme"), "high-contrast")
        self.assertEqual(prefs.get("font_size"), "xlarge")


class TestSignLanguageRecognition(unittest.TestCase):
    """Tests the real-time BdSL adapter, temporal features, and unknown filter."""

    def setUp(self):
        self.adapter = SignLanguageAdapter()

    def test_idle_rejection(self):
        # 30 frames of flat zeros should be rejected as idle/low motion
        idle_seq = np.zeros((30, 162), dtype=float)
        res = self.adapter.predict_sequence(idle_seq)
        self.assertEqual(res["status"], "REJECTED")
        self.assertEqual(res["class_id"], -1)
        self.assertIn("idle", res["rejection_reason"].lower())

    def test_authentic_sample_prediction(self):
        # Load a genuine test sample from disk
        test_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../data/sign/processed/landmarks/BDSL_S001_HELLO_SES01_T01.npy")
        )
        self.assertTrue(os.path.exists(test_file), f"Test sample not found: {test_file}")

        seq = np.load(test_file)
        self.assertEqual(seq.shape, (30, 162))

        # Predict using adapter
        res = self.adapter.predict_sequence(seq)
        self.assertNotEqual(res["status"], "REJECTED", f"Legitimate sample was rejected: {res}")
        self.assertEqual(res["label"], "HELLO")
        self.assertGreater(res["confidence"], 0.70)
        self.assertTrue("Hello" in res["gloss"] or "Greetings" in res["gloss"])

    def test_predict_endpoint_contract(self):
        test_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../data/sign/processed/landmarks/BDSL_S001_HELLO_SES01_T01.npy")
        )
        seq = np.load(test_file).tolist()
        req = SignPredictRequest(sequence=seq, signer_id="test_suite", auto_log=True)
        res = predict_sign_sequence(req)
        self.assertFalse(res["rejected"])
        self.assertEqual(res["label"], "HELLO")
        self.assertIn("debounce_count", res)
        self.assertIn("debounce_target", res)

    def test_bdsl_vs_asl_language_modes(self):
        test_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../data/sign/processed/landmarks/BDSL_S001_HELLO_SES01_T01.npy")
        )
        seq = np.load(test_file)

        # 1. BdSL Mode
        res_bdsl = self.adapter.predict_sequence(seq, language_mode="bdsl")
        self.assertEqual(res_bdsl["language_mode"], "bdsl")
        self.assertEqual(res_bdsl["model_name"], "BdSL Recognition Model")
        self.assertIn("unified_translation", res_bdsl)
        self.assertEqual(res_bdsl["unified_translation"]["source_language"], "BDSL")
        self.assertTrue(res_bdsl["unified_translation"]["speech_ready"])

        # 2. ASL Mode
        res_asl = self.adapter.predict_sequence(seq, language_mode="asl")
        self.assertEqual(res_asl["language_mode"], "asl")
        self.assertIn("ASL", res_asl["model_name"])
        self.assertIn("unified_translation", res_asl)
        self.assertEqual(res_asl["unified_translation"]["source_language"], "ASL")
        self.assertTrue(res_asl["unified_translation"]["speech_ready"])

    def test_live_sign_processor_dual_modes(self):
        import cv2
        import base64
        from src.sign.live_frame_processor import LiveSignFrameProcessor
        processor = LiveSignFrameProcessor()

        # Create synthetic test frame with simulated skin hand shape
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(img, (160, 120), 40, (130, 150, 200), -1)
        _, buf = cv2.imencode(".jpg", img)
        b64_str = base64.b64encode(buf).decode("utf-8")

        # BdSL Mode Frame Processing
        res_bdsl = processor.process_frame(b64_str, mode="expressions", language_mode="bdsl")
        self.assertTrue(res_bdsl["success"])
        self.assertEqual(res_bdsl["language_mode"], "bdsl")
        self.assertEqual(res_bdsl["model_name"], "BdSL Recognition Model")
        self.assertIn("unified_translation", res_bdsl)
        self.assertEqual(res_bdsl["unified_translation"]["source_language"], "BdSL")

        # ASL Mode Frame Processing
        res_asl = processor.process_frame(b64_str, mode="expressions", language_mode="asl")
        self.assertTrue(res_asl["success"])
        self.assertEqual(res_asl["language_mode"], "asl")
        self.assertIn("ASL", res_asl["model_name"])
        self.assertIn("unified_translation", res_asl)
        self.assertEqual(res_asl["unified_translation"]["source_language"], "ASL")


class TestBrailleRecognitionAndIQA(unittest.TestCase):
    """Tests optical Braille recognition, IQA rejection, and UEB decoding."""

    def setUp(self):
        self.adapter = BrailleRecognitionAdapter()
        self.raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/braille/raw"))

    def test_iqa_acceptance_on_clear_image(self):
        p1_path = os.path.join(self.raw_dir, "DOC001_P1.png")
        if not os.path.exists(p1_path):
            p1_path = os.path.join(self.raw_dir, "DOC001_L1.png")
        self.assertTrue(os.path.exists(p1_path))

        with open(p1_path, "rb") as f:
            img_bytes = f.read()

        iqa = self.adapter.assess_quality(img_bytes)
        self.assertTrue(iqa["accepted"], f"High quality image failed IQA: {iqa}")
        self.assertGreaterEqual(iqa["metrics"]["blur_variance"], 30.0)

    def test_iqa_rejection_on_degraded_image(self):
        d1_path = os.path.join(self.raw_dir, "DOC001_D1.png")
        self.assertTrue(os.path.exists(d1_path))

        with open(d1_path, "rb") as f:
            img_bytes = f.read()

        iqa = self.adapter.assess_quality(img_bytes)
        self.assertFalse(iqa["accepted"])
        self.assertIn("blur", iqa["rejection_reason"].lower())
        self.assertIn("remediation_guidance", iqa)

    def test_end_to_end_braille_translation(self):
        l1_path = os.path.join(self.raw_dir, "DOC001_L1.png")
        self.assertTrue(os.path.exists(l1_path))

        with open(l1_path, "rb") as f:
            img_bytes = f.read()

        res = self.adapter.translate_image_bytes(img_bytes, filename="DOC001_L1.png")
        self.assertTrue(res["success"], f"Translation failed: {res}")
        data = res["data"]
        self.assertGreater(data["cell_count"], 0)
        self.assertGreater(data["line_count"], 0)
        self.assertGreater(data["mean_confidence"], 0.85)
        self.assertIn("quick brown fox", data["text"].lower())


class TestTTSEngine(unittest.TestCase):
    """Verifies audio synthesis and client utterance parameters."""

    def test_synthesize_text(self):
        engine = TTSService()
        res = engine.synthesize("Transify is breaking communication barriers.", speed=1.0)
        self.assertTrue(res["success"])
        self.assertIn("data:audio/wav;base64,", res["audio_uri"])
        self.assertEqual(res["client_utterance"]["text"], "Transify is breaking communication barriers.")
        self.assertEqual(res["client_utterance"]["rate"], 1.0)


class TestSampleEndpoints(unittest.TestCase):
    """Verifies interactive sample delivery endpoints."""

    def test_sign_sample_hello(self):
        res = get_sign_sample("HELLO")
        self.assertEqual(res["class_label"], "HELLO")
        self.assertEqual(res["frames"], 30)
        self.assertEqual(len(res["sequence"]), 30)
        self.assertEqual(len(res["sequence"][0]), 162)

    def test_braille_sample_list(self):
        res = list_braille_samples()
        self.assertIn("samples", res)
        self.assertGreaterEqual(len(res["samples"]), 1)
        self.assertIn("filename", res["samples"][0])


class TestFrontendServing(unittest.TestCase):
    """Verifies that static HTML pages serve properly with WCAG accessibility attributes."""

    def test_landing_page(self):
        html = serve_landing_page()
        self.assertIn("Breaking Communication Barriers", html)
        self.assertIn("skip-link", html)
        self.assertIn("sr-announcements", html)
        self.assertIn("slide-stt", html)
        self.assertIn("slide-tts", html)
        self.assertIn("btn-open-stt", html)
        self.assertIn("btn-open-tts", html)

    def test_login_page(self):
        html = serve_login_page()
        self.assertIn("Login", html)
        self.assertIn("Sign Up", html)
        self.assertIn("Welcome Back!", html)
        self.assertIn("transify-auth", html or "auth")

    def test_dashboard_page(self):
        html = serve_dashboard_page()
        self.assertIn("Assistive Control Dashboard", html)
        self.assertIn("history-records-list", html)

    def test_sign_page(self):
        html = serve_sign_page()
        self.assertIn("Live ASL & HaGRID Hand Gesture Translator", html)
        self.assertIn("sign-video", html)
        self.assertIn("debounce-progress-fill", html)

    def test_braille_page(self):
        html = serve_braille_page()
        self.assertIn("Braille Image Translator", html)
        self.assertIn("braille-dropzone", html)
        self.assertIn("braille-text-output", html)


class TestAssistiveExtensions(unittest.TestCase):
    """Tests Fingerspelling A-Z engine, AI Sentence Builder, and Expanded Categories."""

    def test_fingerspelling_word_assembler(self):
        from src.sign.fingerspelling import FingerspellingWordAssembler
        assembler = FingerspellingWordAssembler()
        assembler.add_direct_letter("H")
        assembler.add_direct_letter("E")
        assembler.add_direct_letter("L")
        assembler.add_direct_letter("P")
        state = assembler.get_state()
        self.assertEqual(state["current_word"], "HELP")
        self.assertEqual(state["full_text"], "HELP")

        # Test space to commit word
        assembler.add_direct_letter("SPACE")
        assembler.add_direct_letter("M")
        assembler.add_direct_letter("E")
        state2 = assembler.get_state()
        self.assertEqual(state2["committed_words"], ["HELP"])
        self.assertEqual(state2["current_word"], "ME")
        self.assertEqual(state2["full_text"], "HELP ME")

    def test_sentence_builder_smoothing(self):
        from src.sign.sentence_builder import SentenceBuilder
        sb = SentenceBuilder()
        res = sb.smooth_sentence(["HELLO", "I_NEED_HELP"])
        self.assertTrue(res["success"])
        self.assertIn("help", res["sentence"].lower())
        self.assertIn("hello", res["sentence"].lower())

    def test_sign_categories_registry(self):
        from src.sign.vocabulary_registry import get_all_categories
        cats = get_all_categories()
        self.assertGreaterEqual(cats["total_categories"], 4)
        self.assertGreaterEqual(cats["total_expressions"], 20)
        self.assertIn("emergency_medical", cats["categories"])

    def test_live_frame_processor_idle(self):
        import cv2
        import base64
        from src.sign.live_frame_processor import LiveSignFrameProcessor
        proc = LiveSignFrameProcessor()
        # Create blank 320x240 image
        blank = np.zeros((240, 320, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", blank)
        b64 = base64.b64encode(buf).decode("utf-8")
        res = proc.process_frame(b64, mode="expressions")
        self.assertTrue(res["success"])
        self.assertFalse(res["hand_detected"])
        self.assertEqual(res["label"], "IDLE")

    def test_live_frame_processor_skin_detection(self):
        import cv2
        import base64
        from src.sign.live_frame_processor import LiveSignFrameProcessor
        from src.api.server import process_webcam_frame, ProcessFrameRequest
        proc = LiveSignFrameProcessor()
        # Create synthetic hand region in skin color: BGR for typical skin (e.g. [120, 150, 200])
        synthetic_img = np.zeros((240, 320, 3), dtype=np.uint8)
        # Draw a round hand contour in the center
        cv2.circle(synthetic_img, (160, 120), 40, (140, 160, 215), -1)
        _, buf = cv2.imencode(".jpg", synthetic_img)
        b64 = base64.b64encode(buf).decode("utf-8")
        res = proc.process_frame(b64, mode="expressions")
        self.assertTrue(res["success"])
        self.assertTrue(res["hand_detected"])
        self.assertIsNotNone(res["hand_bbox"])

        # Also test via FastAPI endpoint
        req = ProcessFrameRequest(image_b64=b64, mode="expressions")
        api_res = process_webcam_frame(req)
        self.assertTrue(api_res["success"])
        self.assertTrue(api_res["hand_detected"])


class TestSignFrameAIEngine(unittest.TestCase):
    """Verifies SignFrame AI integration, CNN models, 98% gateway, stabilizer and composer."""

    def test_signframe_predictor_inference(self):
        from src.sign.signframe_pipeline import SignPredictor
        predictor = SignPredictor()
        # Random 1x1x28x28 normalized patch
        dummy = np.random.rand(1, 1, 28, 28).astype(np.float32)
        letter, conf, probs = predictor.predict(dummy)
        self.assertIsInstance(letter, str)
        self.assertEqual(len(letter), 1)
        self.assertTrue(letter.isalpha())
        self.assertGreater(conf, 0.0)
        self.assertEqual(len(probs), 24)

    def test_signframe_stabilizer_consensus(self):
        from src.sign.signframe_pipeline import PredictionStabilizer
        stabilizer = PredictionStabilizer(window_size=12, required_votes=9, confidence_threshold=0.65)
        # Feed 8 frames of 'A' -> should not be confirmed yet
        for _ in range(8):
            conf_letter, votes, req = stabilizer.update("A", 0.95)
            self.assertIsNone(conf_letter)
        # 9th frame of 'A' -> should reach consensus
        conf_letter, votes, req = stabilizer.update("A", 0.95)
        self.assertEqual(conf_letter, "A")
        self.assertEqual(votes, 9)

    def test_signframe_text_composer(self):
        from src.sign.signframe_pipeline import TextComposer
        composer = TextComposer()
        composer.append_letter("T")
        composer.append_letter("E")
        composer.append_letter("S")
        composer.append_letter("T")
        self.assertEqual(composer.text, "TEST")
        composer.add_space()
        composer.append_letter("O")
        composer.append_letter("K")
        self.assertEqual(composer.text, "TEST OK")
        composer.backspace()
        self.assertEqual(composer.text, "TEST O")
        composer.clear()
        self.assertEqual(composer.text, "")

    def test_decision_gateway_98_percent_rule(self):
        from src.sign.mcp_sign_resolver import MCPSignResolver
        resolver = MCPSignResolver(threshold=0.98)
        # Test 1: Confidence >= 0.98 -> should NOT be flagged as low confidence
        self.assertFalse(resolver.is_low_confidence(0.99))
        self.assertFalse(resolver.is_low_confidence(0.98))

        # Test 2: Confidence < 0.98 -> should be flagged as low confidence
        self.assertTrue(resolver.is_low_confidence(0.979))
        self.assertTrue(resolver.is_low_confidence(0.85))

        # Test 3: MCP resolver fallback resolution
        mcp_res = resolver.resolve(
            candidate_label="B",
            confidence=0.85,
            top_candidates=[{"label": "B", "confidence": 0.85}],
            motion_energy=0.05
        )
        self.assertTrue(mcp_res["success"])
        self.assertEqual(mcp_res["label"], "B")
        self.assertIsNone(mcp_res["confidence"])
        self.assertTrue(mcp_res["resolver_assisted"])
        self.assertTrue(mcp_res["is_fallback"])
        self.assertIn("MCP", mcp_res["badge"])

    def test_hagrid_recognizer_and_gestures(self):
        from src.sign.hagrid_recognizer import HaGRIDRecognizer, HAGRID_GESTURES, HAGRID_CLASS_NAMES
        from src.sign.train_hagrid_model import generate_base_hand
        recognizer = HaGRIDRecognizer()
        self.assertGreaterEqual(len(HAGRID_CLASS_NAMES), 20)
        self.assertGreaterEqual(len(HAGRID_GESTURES), 20)

        # Verify key gestures
        for g_name in ["LIKE", "DISLIKE", "CALL", "OK", "PEACE", "FIST", "STOP"]:
            landmarks = generate_base_hand(g_name)
            res = recognizer.classify(landmarks)
            self.assertIsNotNone(res, f"Failed to classify {g_name}")
            self.assertEqual(res["label"], g_name, f"Expected {g_name}, got {res['label']}")
            self.assertGreaterEqual(res["confidence"], 0.98)
            self.assertTrue(res["is_hagrid"])

    def test_hagrid_api_classes_endpoint(self):
        from src.api.server import get_hagrid_classes
        data = get_hagrid_classes()
        self.assertGreaterEqual(data["gesture_count"], 20)
        self.assertGreaterEqual(len(data["classes"]), 20)
        labels = [c["label"] for c in data["classes"]]
        for expected in ["CALL", "DISLIKE", "FIST", "LIKE", "OK", "PEACE", "STOP"]:
            self.assertIn(expected, labels)

    def test_hagrid_sentence_smoothing(self):
        from src.sign.sentence_builder import SentenceBuilder
        builder = SentenceBuilder()
        builder.add_token("LIKE")
        builder.add_token("CALL")
        res = builder.smooth_sentence()
        self.assertTrue(res["success"])
        self.assertIn("like", res["sentence"].lower())
        self.assertIn("call", res["sentence"].lower())


if __name__ == "__main__":
    unittest.main()
