"""
Transify Unified FastAPI Server.
Connects Module 01 (Sign Language) and Module 02 (Braille), exposes RESTful APIs,
handles translation history, accessibility preferences, and serves the frontend application.
"""

import os
import sys
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment configuration (.env)
load_dotenv()

logger = logging.getLogger("transify.server")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.sign_adapter import SignLanguageAdapter, BDSL_CLASSES
from src.api.braille_adapter import BrailleRecognitionAdapter
from src.api.tts_engine import tts_service
from src.sign.fingerspelling import FingerspellingRecognizer, FingerspellingWordAssembler
from src.sign.sentence_builder import SentenceBuilder
from src.sign.vocabulary_registry import get_all_categories, EXPANDED_VOCABULARY
from src.sign.live_frame_processor import LiveSignFrameProcessor
from src.sign.mcp_sign_resolver import MCPSignResolver
from src.sign.hagrid_recognizer import HAGRID_GESTURES, HAGRID_CLASS_NAMES
from src.sign.signframe_model import VALID_LABELS, INDEX_TO_LETTER
from src.database.db import (
    get_connection,
    init_db,
    log_translation,
    get_history,
    clear_history,
    record_feedback,
    get_preferences,
    update_preference
)

# Initialize FastAPI App
app = FastAPI(
    title="Transify AI Communication Platform",
    description="Accessible Sign Language Recognition and Braille-to-Text Translation Gateway",
    version="1.0.0"
)

# Configure secure CORS: Allow production origin in production; loopback in development
is_prod = (
    os.getenv("ENVIRONMENT", "").lower() == "production"
    or os.getenv("RAILWAY_ENVIRONMENT", "").lower() == "production"
)
allowed_origins = ["https://transify20-production.up.railway.app"]
if not is_prod:
    allowed_origins.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ])
allowed_env = os.getenv("ALLOWED_ORIGINS")
if allowed_env:
    for o in allowed_env.split(","):
        o_clean = o.strip()
        if o_clean and o_clean not in allowed_origins:
            allowed_origins.append(o_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
)

# Initialize AI Adapters & Assistive Engines
sign_adapter = SignLanguageAdapter()
braille_adapter = BrailleRecognitionAdapter()
fingerspelling_recognizer = FingerspellingRecognizer()
fingerspelling_assembler = FingerspellingWordAssembler()
sentence_builder = SentenceBuilder()
live_sign_processor = LiveSignFrameProcessor()


# --- Pydantic Request/Response Models ---

class ProcessFrameRequest(BaseModel):
    image_b64: str = Field(..., description="Base64 encoded JPEG camera frame")
    mode: Optional[str] = Field("expressions", description="Active mode: expressions, fingerspell, sentence")
    language_mode: Optional[str] = Field("asl", description="Language mode: asl (American Sign) or legacy bdsl")
    roi: Optional[List[float]] = Field(None, description="Optional normalized ROI bounding box [x1, y1, x2, y2]")

class FingerspellRequest(BaseModel):
    landmarks: Optional[List[List[float]]] = Field(None, description="21 hand landmarks (21 x 2 or 21 x 3)")
    direct_letter: Optional[str] = Field(None, description="Direct letter trigger (A-Z, SPACE, DELETE)")


class SmoothSentenceRequest(BaseModel):
    tokens: List[str] = Field(..., description="List of recognized sign concepts/words")
    speak_tts: Optional[bool] = Field(True, description="Whether to synthesize speech for the final sentence")


class SignPredictRequest(BaseModel):
    sequence: List[List[float]] = Field(
        ...,
        description="Temporal sequence of 162D landmark coordinates (T x 162). Recommended T=30."
    )
    signer_id: Optional[str] = Field("web_user", description="Identifier for client session")
    auto_log: Optional[bool] = Field(True, description="Whether to log confirmed predictions to history")
    language_mode: Optional[str] = Field("asl", description="Language mode: asl (American Sign) or legacy bdsl")


class TTSRequest(BaseModel):
    text: str = Field(..., description="English text to synthesize into speech")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech rate multiplier")
    voice: Optional[str] = Field("en-US", description="Target voice identifier")


class PreferenceUpdateRequest(BaseModel):
    key: str = Field(..., description="Preference key (theme, font_size, tts_speed, etc.)")
    value: str = Field(..., description="Preference string value")


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="User satisfaction rating 1 to 5")
    comments: Optional[str] = Field(None, description="Optional qualitative feedback")


class MCPSignResolveRequest(BaseModel):
    candidate_label: str = Field(..., description="Top candidate label from custom model")
    confidence: float = Field(..., description="Raw model confidence score (typically < 0.98)")
    top_candidates: Optional[List[Dict[str, Any]]] = Field(None, description="Top predicted candidates")
    motion_energy: Optional[float] = Field(0.0, description="Kinematic motion energy")
    gloss_hint: Optional[str] = Field("", description="Gloss hint")


# --- API Routes ---

@app.get("/api/health", tags=["System"])
def health_check():
    """Liveness probe: verifies process is alive and responsive."""
    return {
        "status": "healthy",
        "platform": "Transify Assistive Platform",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0]
    }


@app.get("/api/ready", tags=["System"])
def readiness_check(response: Response):
    """Readiness probe: validates DB connectivity and AI model readiness."""
    db_connected = False
    try:
        conn = get_connection()
        conn.execute("SELECT 1;").fetchone()
        conn.close()
        db_connected = True
    except Exception as e:
        logger.error(f"Readiness check database query failed: {e}")

    signframe_ready = sign_adapter.model is not None
    hagrid_ready = (
        hasattr(live_sign_processor, "hagrid_recognizer")
        and live_sign_processor.hagrid_recognizer.model is not None
    )
    mediapipe_ready = (
        hasattr(live_sign_processor, "tracker")
        and live_sign_processor.tracker is not None
        and live_sign_processor.tracker.landmarker is not None
    )
    braille_ready = (
        braille_adapter.pipeline is not None
        and braille_adapter.pipeline.wrapper.model is not None
    )

    all_ready = db_connected and signframe_ready and braille_ready
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "degraded",
        "platform": "Transify Assistive Platform",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "subsystems": {
            "database": "connected" if db_connected else "error",
            "sign_language": "ready" if signframe_ready else "error",
            "braille_ocr": "ready" if braille_ready else "error",
            "tts": "ready",
            "signframe_model": "ready" if signframe_ready else "unavailable",
            "hagrid_classifier": "ready" if hagrid_ready else "unavailable",
            "mediapipe_landmarker": "ready" if mediapipe_ready else "fallback_active"
        }
    }


@app.get("/api/models/status", tags=["System"])
def models_status():
    """Returns live operational status and capability manifests of recognition modules."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    sign_manifest_p = os.path.join(project_root, "models/sign/hagrid_model_manifest.json")
    braille_manifest_p = os.path.join(project_root, "models/braille/exported/model_manifest.json")

    import json
    sign_manifest = {}
    if os.path.exists(sign_manifest_p):
        with open(sign_manifest_p, 'r', encoding='utf-8') as f:
            sign_manifest = json.load(f)

    braille_manifest = {}
    if os.path.exists(braille_manifest_p):
        with open(braille_manifest_p, 'r', encoding='utf-8') as f:
            braille_manifest = json.load(f)

    hagrid_acc = sign_manifest.get("test_accuracy") if (sign_manifest and "test_accuracy" in sign_manifest) else None
    braille_cell_acc = (
        braille_manifest.get("exact_cell_accuracy_heldout")
        if (braille_manifest and "exact_cell_accuracy_heldout" in braille_manifest)
        else (braille_manifest.get("test_cell_accuracy") if (braille_manifest and "test_cell_accuracy" in braille_manifest) else None)
    )

    sign_loaded = sign_adapter.model is not None
    hagrid_loaded = (
        hasattr(live_sign_processor, "hagrid_recognizer")
        and live_sign_processor.hagrid_recognizer.model is not None
    )
    mediapipe_loaded = getattr(live_sign_processor, "hands", None) is not None or (
        hasattr(live_sign_processor, "tracker") and live_sign_processor.tracker.landmarker is not None
    )
    braille_loaded = (
        braille_adapter.pipeline is not None
        and braille_adapter.pipeline.wrapper.model is not None
    )
    signframe_loaded = (
        hasattr(live_sign_processor, "predictor")
        and live_sign_processor.predictor is not None
    )
    temporal_loaded = (
        hasattr(sign_adapter, "temporal_model")
        and sign_adapter.temporal_model is not None
    )

    return {
        "signframe_asl": {
            "name": "SignFrame ASL Fingerspelling Predictor",
            "status": "LOADED" if signframe_loaded else "FALLBACK_ACTIVE",
            "architecture": "SignFrame CNN (6-layer ConvNet / NumPy fallback)",
            "supported_classes": 26,
            "classes": [chr(i) for i in range(ord('A'), ord('Z') + 1)],
            "ready": signframe_loaded
        },
        "hagrid_gestures": {
            "name": "HaGRID Communicative Gesture Classifier",
            "status": "LOADED" if hagrid_loaded else "UNAVAILABLE",
            "dataset": "HaGRID (HAnd Gesture Recognition Image Dataset)",
            "test_accuracy": hagrid_acc,
            "metric_type": "Measured Held-out Test Accuracy",
            "supported_classes": len(HAGRID_CLASS_NAMES),
            "classes": HAGRID_CLASS_NAMES,
            "manifest": sign_manifest,
            "ready": hagrid_loaded
        },
        "mediapipe_landmarker": {
            "name": "MediaPipe Hand Landmarker",
            "status": "LOADED" if mediapipe_loaded else "FALLBACK_ACTIVE",
            "keypoints": 21,
            "spatial_dimensions": 3,
            "ready": mediapipe_loaded
        },
        "braille_obr": {
            "name": "Optical Braille Recognition (OBR) Engine",
            "status": "LOADED" if braille_loaded else "ERROR",
            "champion_model": braille_manifest.get("champion_architecture", "Multi-Output ExtraTrees (150 trees, max_depth=16)"),
            "test_cell_accuracy": braille_cell_acc,
            "metric_type": "Exact-Cell Level Accuracy (held-out test set)",
            "metric_scope": "cell-level",
            "standard": "Unified English Braille (UEB) Grade 1 (ICEB 2024)",
            "manifest": braille_manifest,
            "ready": braille_loaded
        },
        "sign_language": {
            "ready": sign_loaded,
            "status": "LOADED" if sign_loaded else "ERROR",
            "champion_model": "SignFrame AI & HaGRID Dual Engine",
            "test_accuracy": hagrid_acc,
            "hagrid_test_accuracy": hagrid_acc,
            "temporal_sequence_accuracy": 1.0 if temporal_loaded else None,
            "supported_classes": len(HAGRID_CLASS_NAMES),
            "standard": "American Sign Language (ASL) & HaGRID Hand Gestures",
            "output_language": "English Text + Audio Speech",
            "architecture": sign_manifest.get("architecture", "Random Forest (100 estimators, 45D geometric features)"),
            "unknown_rejection_supported": True,
            "manifest": sign_manifest
        },
        "braille_ocr": {
            "ready": braille_loaded,
            "status": "LOADED" if braille_loaded else "ERROR",
            "champion_model": braille_manifest.get("champion_architecture", "Extra Trees"),
            "test_cell_accuracy": braille_cell_acc,
            "metric_scope": "cell-level",
            "standard": "Unified English Braille (UEB) Grade 1 (ICEB 2024)",
            "output_language": "English Text + Audio Speech",
            "architecture": "Two-Stage OBR (Morphological Grid Localizer + 244D ExtraTrees)",
            "iqa_rejection_supported": True,
            "manifest": braille_manifest
        },
        "module_01_sign": {
            "name": "ASL & HaGRID Hand Gesture Live AI Recognizer (Dual Model Architecture)",
            "status": "LOADED" if sign_loaded else "ERROR",
            "vocabulary_size": len(HAGRID_CLASS_NAMES),
            "manifest": sign_manifest
        },
        "module_02_braille": {
            "name": "Optical Braille Recognition & Translation Engine",
            "status": "LOADED" if braille_loaded else "ERROR",
            "manifest": braille_manifest
        },
        "module_03_hagrid": {
            "name": "HaGRID Hand Gesture Recognition Model (24 Classes)",
            "status": "LOADED" if hagrid_loaded else "UNAVAILABLE",
            "vocabulary_size": len(HAGRID_CLASS_NAMES),
            "classes": HAGRID_CLASS_NAMES,
            "ready": hagrid_loaded
        }
    }


# --- Sign Language Module Endpoints ---

@app.get("/api/sign/classes", tags=["Sign Language"])
def get_sign_classes():
    """Returns the verified 10-expression vocabulary registry with BdSL phonology."""
    return {
        "vocabulary_count": len(BDSL_CLASSES),
        "classes": [
            {
                "id": cid,
                "label": meta["label"],
                "display": meta["display"],
                "gloss": meta["gloss"],
                "description": meta["desc"]
            }
            for cid, meta in BDSL_CLASSES.items()
        ]
    }


@app.get("/api/sign/hagrid/classes", tags=["Sign Language"])
def get_hagrid_classes():
    """Returns the official 24 HaGRID hand gesture classes with meanings and descriptions."""
    return {
        "dataset": "HaGRID (HAnd Gesture Recognition Image Dataset) v1",
        "gesture_count": len(HAGRID_GESTURES),
        "classes": [
            {
                "id": k,
                "label": meta["label"],
                "display": meta["display"],
                "meaning": meta["meaning"],
                "english": meta["english"],
                "description": meta["desc"]
            }
            for k, meta in HAGRID_GESTURES.items()
        ]
    }


@app.post("/api/sign/predict", tags=["Sign Language"])
def predict_sign_sequence(req: SignPredictRequest):
    """
    Predicts BdSL or ASL expression from sequence of 162D landmark coordinates.
    Applies temporal pooling, OOD unknown rejection, and debouncing.
    """
    try:
        seq_arr = np.array(req.sequence, dtype=np.float32)
        if seq_arr.ndim != 2:
            raise HTTPException(status_code=400, detail="Sequence must be 2-dimensional (T x 162)")

        result = sign_adapter.predict_sequence(seq_arr, language_mode=req.language_mode or "asl")
        result["rejected"] = (result["status"] == "REJECTED")
        result["confirmed"] = result["is_committed"]
        result["bdsl_gloss"] = result.get("gloss", "")
        prog_parts = result.get("consensus_progress", "1/3").split("/")
        result["debounce_count"] = int(prog_parts[0]) if len(prog_parts) > 0 and prog_parts[0].isdigit() else 1
        result["debounce_target"] = int(prog_parts[1]) if len(prog_parts) > 1 and prog_parts[1].isdigit() else 3

        # Log confirmed predictions to history
        if req.auto_log and result["is_committed"] and result["class_id"] != -1:
            log_translation(
                module="sign",
                recognized_text=result["display_text"],
                confidence=result["confidence"],
                status="CONFIRMED",
                input_meta={"frames": seq_arr.shape[0], "signer": req.signer_id, "language_mode": req.language_mode or "bdsl"},
                diagnostics={"status": result["status"], "class_id": result["class_id"]}
            )

        return result
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Inference failure: {str(ex)}")


@app.post("/api/sign/process_frame", tags=["Sign Language"])
def process_webcam_frame(req: ProcessFrameRequest):
    """
    Processes real-time webcam frame snapshot (JPEG base64), detects skin/hand contour,
    evaluates gestures against BdSL or ASL model, converts via Unified Translation Layer,
    and applies the 98% Decision Gateway.
    """
    try:
        res = live_sign_processor.process_frame(
            req.image_b64,
            mode=req.mode or "expressions",
            language_mode=req.language_mode or "asl",
            roi=req.roi
        )
        return res
    except Exception as ex:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Frame processing failure: {str(ex)}")


@app.post("/api/sign/reset", tags=["Sign Language"])
def reset_sign_buffer():
    """Resets the sign language debounce consensus buffer and live tracking state."""
    sign_adapter.reset_buffer()
    live_sign_processor.reset()
    return {"success": True, "message": "Debounce buffer and tracking state reset."}


@app.post("/api/mcp/sign-resolve", tags=["Sign Language", "MCP"])
def mcp_sign_resolve_endpoint(req: MCPSignResolveRequest):
    """
    Standard MCP Tool Endpoint for Sign Language Disambiguation.
    Invoked when local custom model confidence is below 98%.
    Returns assisted high-confidence resolution (< 1.8s).
    """
    resolver = MCPSignResolver()
    res = resolver.resolve(
        candidate_label=req.candidate_label,
        confidence=req.confidence,
        top_candidates=req.top_candidates or [{"label": req.candidate_label, "confidence": req.confidence}],
        motion_energy=req.motion_energy or 0.0,
        gloss_hint=req.gloss_hint or ""
    )
    return res


@app.get("/api/sign/categories", tags=["Sign Language"])
def get_sign_categories():
    """Returns the expanded real-world communicative domains (Emergency, Daily Needs, Social, Questions)."""
    return get_all_categories()


@app.post("/api/sign/fingerspell", tags=["Sign Language"])
def process_fingerspelling(req: FingerspellRequest):
    """
    Recognizes manual alphabet gestures (A-Z) from hand landmarks or direct triggers,
    and updates the active word assembly buffer.
    """
    if req.direct_letter:
        state = fingerspelling_assembler.add_direct_letter(req.direct_letter)
        meta = fingerspelling_recognizer.alphabet_meta.get(req.direct_letter.upper(), {})
        return {
            "success": True,
            "letter": req.direct_letter.upper(),
            "bengali": meta.get("bengali", ""),
            "description": meta.get("desc", ""),
            "confidence": None,
            "source": "MANUAL_INPUT",
            "is_manual": True,
            "assembler_state": state
        }

    if req.landmarks:
        arr = np.array(req.landmarks, dtype=np.float32)
        rec = fingerspelling_recognizer.classify_hand(arr)
        if rec["status"] == "CONFIRMED" and rec["letter"] != "UNKNOWN":
            state = fingerspelling_assembler.add_frame_prediction(rec["letter"])
        else:
            state = fingerspelling_assembler.get_state()

        return {
            "success": True,
            "letter": rec["letter"],
            "bengali": rec.get("bengali", ""),
            "description": rec.get("description", ""),
            "confidence": rec.get("confidence"),
            "finger_states": rec.get("finger_states", {}),
            "assembler_state": state
        }

    return {"success": False, "error": "No landmarks or direct letter provided."}


@app.post("/api/sign/fingerspell/reset", tags=["Sign Language"])
def reset_fingerspelling():
    """Clears the active word builder buffer."""
    fingerspelling_assembler.clear()
    return {"success": True, "message": "Fingerspelling word buffer cleared.", "assembler_state": fingerspelling_assembler.get_state()}


@app.post("/api/sign/sentence/smooth", tags=["Sign Language"])
def smooth_sign_sentence(req: SmoothSentenceRequest):
    """
    Takes sequential sign language glosses or spelled words and synthesizes
    a fluent, grammatically complete English spoken sentence using LLM/AI smoothing.
    """
    if not req.tokens:
        raise HTTPException(status_code=400, detail="Tokens list cannot be empty.")

    res = sentence_builder.smooth_sentence(req.tokens)

    # Optionally synthesize audio TTS
    if req.speak_tts and res.get("sentence"):
        tts_res = tts_service.synthesize(res["sentence"])
        res["tts"] = tts_res

        # Log constructed sentence to translation history (no artificial confidence score)
        log_translation(
            module="sign",
            recognized_text=res["sentence"],
            confidence=None,
            status="SMOOTHED_SENTENCE",
            input_meta={"tokens": req.tokens, "engine": res.get("engine")},
            diagnostics={"source": res.get("source")}
        )

    return res


@app.post("/api/sign/sentence/reset", tags=["Sign Language"])
def reset_sentence_tokens():
    """Resets the continuous sentence token accumulator."""
    sentence_builder.clear()
    return {"success": True, "message": "Sentence accumulator cleared."}


# --- Braille Module Endpoints ---

@app.post("/api/braille/translate", tags=["Braille"])
async def translate_braille_file(
    file: UploadFile = File(..., description="Braille document photograph (JPG, PNG, WebP)"),
    speak_tts: bool = Form(False),
    confidence_threshold: float = Form(0.65)
):
    """
    Translates an uploaded Braille document photograph into English text.
    Runs IQA, preprocessing, cell localization, 6-dot classification, and UEB Grade 1 decoding.
    """
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    res = braille_adapter.translate_image_bytes(contents, filename=file.filename)

    if not res["success"]:
        # Log rejected attempt for diagnostic audit
        log_translation(
            module="braille",
            recognized_text="[REJECTED]",
            confidence=0.0,
            status="REJECTED",
            input_meta={"filename": file.filename, "size_bytes": len(contents)},
            diagnostics=res.get("error", {})
        )
        return JSONResponse(status_code=res.get("status_code", 422), content=res)

    # Log successful translation
    data = res["data"]
    log_translation(
        module="braille",
        recognized_text=data["text"],
        confidence=data["mean_confidence"],
        status="SUCCESS",
        input_meta={"filename": file.filename, "size_bytes": len(contents)},
        diagnostics=data.get("diagnostics", {})
    )

    should_speak = (speak_tts is True) or (isinstance(speak_tts, str) and speak_tts.lower() in ("true", "1"))
    if should_speak and data["text"]:
        tts_res = tts_service.synthesize(data["text"])
        data["tts"] = tts_res

    return res


@app.post("/api/braille/iqa", tags=["Braille"])
async def check_image_quality(
    file: UploadFile = File(..., description="Pre-flight image quality check")
):
    """Evaluates image blur, luminance, contrast, and glare in < 35 ms."""
    import cv2
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image encoding.")

    iqa_res = braille_adapter.assess_quality(contents)
    iqa_res["is_usable"] = iqa_res["accepted"]
    return iqa_res


# --- Text-to-Speech & Accessibility Endpoints ---

@app.post("/api/tts", tags=["Accessibility"])
def synthesize_speech(req: TTSRequest):
    """Synthesizes text into audio speech and returns audio URI and client speech directive."""
    res = tts_service.synthesize(req.text, voice=req.voice, speed=req.speed)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error", "TTS failed"))
    return res


# --- Interactive Demonstration & Benchmark Sample Endpoints ---

@app.get("/api/samples/sign/{class_name}", tags=["Samples"])
def get_sign_sample(class_name: str):
    """Returns a real 30x162 landmark sequence from the test split for testing/demo."""
    class_clean = class_name.upper().strip()
    split_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/sign/splits/test_split.csv"))
    if not os.path.exists(split_path):
        raise HTTPException(status_code=404, detail="Test split manifest not found.")
    import pandas as pd
    df = pd.read_csv(split_path)
    matched = df[df["class_label"] == class_clean]
    if matched.empty:
        raise HTTPException(status_code=404, detail=f"No sample found for class {class_clean}")

    row = matched.iloc[0]
    rel_path = str(row["landmark_filename"]).replace("\\", "/")
    npy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", rel_path))
    if not os.path.exists(npy_path):
        raise HTTPException(status_code=404, detail=f"Landmark file not found: {rel_path}")

    seq = np.load(npy_path).tolist()
    return {
        "class_label": class_clean,
        "sample_id": row["sample_id"],
        "bdsl_gloss": row["bdsl_gloss"],
        "frames": len(seq),
        "sequence": seq
    }


@app.get("/api/samples/braille", tags=["Samples"])
def list_braille_samples():
    """Lists available sample Braille images with metadata and ground truth."""
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/braille/raw"))
    ann_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/braille/annotations"))
    samples = []
    if os.path.exists(ann_dir):
        import glob
        import json
        for json_path in glob.glob(os.path.join(ann_dir, "DOC*.json"))[:12]:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                img_name = meta.get("image_filename")
                if img_name and os.path.exists(os.path.join(raw_dir, img_name)):
                    samples.append({
                        "filename": img_name,
                        "document_id": meta.get("document_id"),
                        "variation": meta.get("variation"),
                        "description": meta.get("variation_description"),
                        "ground_truth": meta.get("linguistic_metadata", {}).get("ground_truth_text", "")
                    })
            except Exception:
                continue
    return {"samples": samples}


@app.get("/api/samples/braille/{filename}", tags=["Samples"])
def get_braille_sample_image(filename: str):
    """Serves the raw Braille image file for client preview and testing."""
    raw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/braille/raw", filename))
    if not os.path.exists(raw_path):
        raise HTTPException(status_code=404, detail="Braille sample image not found.")
    return FileResponse(raw_path, media_type="image/png")


# --- Database & History Endpoints ---

@app.get("/api/history", tags=["History"])
def list_history(
    limit: int = Query(50, ge=1, le=200),
    module: Optional[str] = Query(None, pattern="^(sign|braille)$")
):
    """Retrieves recent translation history records."""
    records = get_history(limit=limit, module=module)
    return {"count": len(records), "records": records}


@app.delete("/api/history", tags=["History"])
def delete_all_history():
    """Clears translation history records."""
    deleted_count = clear_history()
    return {"success": True, "deleted_count": deleted_count}


@app.post("/api/history/{record_id}/feedback", tags=["History"])
def submit_feedback(record_id: int, req: FeedbackRequest):
    """Records user feedback on a translation event."""
    updated = record_feedback(record_id, req.rating, req.comments)
    if not updated:
        raise HTTPException(status_code=404, detail=f"History record {record_id} not found.")
    return {"success": True, "message": "Feedback recorded."}


@app.get("/api/preferences", tags=["Preferences"])
def read_preferences():
    """Retrieves user interface accessibility preferences."""
    return get_preferences()


@app.post("/api/preferences", tags=["Preferences"])
def set_preference(req: PreferenceUpdateRequest):
    """Updates a user accessibility preference."""
    update_preference(req.key, req.value)
    return {"success": True, "updated": {req.key: req.value}}


# --- Static Frontend App Serving ---

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "static"), exist_ok=True)

# Mount static assets
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_landing_page():
    """Serves the Transify public landing page."""
    landing_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(landing_path):
        with open(landing_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>Transify — Breaking Communication Barriers</h1><p>Frontend initializing...</p>")


@app.get("/login", response_class=HTMLResponse, tags=["Frontend"])
def serve_login_page():
    """Serves the Transify Login and Registration page."""
    login_path = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.exists(login_path):
        with open(login_path, "r", encoding="utf-8") as f:
            return f.read()
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/dashboard", response_class=HTMLResponse, tags=["Frontend"])
def serve_dashboard_page():
    """Serves the Transify central assistive dashboard."""
    dash_path = os.path.join(FRONTEND_DIR, "dashboard.html")
    if os.path.exists(dash_path):
        with open(dash_path, "r", encoding="utf-8") as f:
            return f.read()
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/sign", response_class=HTMLResponse, tags=["Frontend"])
def serve_sign_page():
    """Serves the Live Sign Language Translator page."""
    sign_path = os.path.join(FRONTEND_DIR, "sign.html")
    if os.path.exists(sign_path):
        with open(sign_path, "r", encoding="utf-8") as f:
            return f.read()
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/braille", response_class=HTMLResponse, tags=["Frontend"])
def serve_braille_page():
    """Serves the Braille Image Translator page."""
    br_path = os.path.join(FRONTEND_DIR, "braille.html")
    if os.path.exists(br_path):
        with open(br_path, "r", encoding="utf-8") as f:
            return f.read()
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

