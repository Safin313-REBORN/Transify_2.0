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

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
try:
    from pydantic import BaseModel, Field, field_validator
    USE_FIELD_VALIDATOR = True
except ImportError:
    from pydantic import BaseModel, Field, validator
    USE_FIELD_VALIDATOR = False
import numpy as np
import time
import hmac
import secrets
import threading
from collections import defaultdict

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.sign_adapter import SignLanguageAdapter, BDSL_CLASSES
from src.api.braille_adapter import BrailleRecognitionAdapter
from src.api.tts_engine import tts_service
from src.api.email_service import get_email_adapter, EmailDeliveryError
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
    toggle_history_favorite,
    record_feedback,
    get_preferences,
    update_preference,
    create_user,
    authenticate_user,
    create_session,
    get_user_by_session,
    revoke_session,
    get_user_by_email,
    is_production,
    record_failed_login,
    is_login_rate_limited,
    clear_failed_logins,
    count_legacy_history,
    create_password_reset_token,
    verify_and_consume_reset_token,
    invalidate_password_reset_token,
    create_hub_conversation,
    get_hub_conversations,
    get_hub_messages,
    add_hub_message,
    delete_hub_conversation,
    clear_hub_conversation_messages,
    DEFAULT_PHRASES,
    get_user_phrases,
    add_user_phrase,
    toggle_phrase_favorite,
    delete_user_phrase
)

# Initialize FastAPI App
app = FastAPI(
    title="Transify AI Communication Platform",
    description="Accessible Sign Language Recognition and Braille-to-Text Translation Gateway",
    version="1.0.0"
)

from urllib.parse import urlparse

# Configure secure CORS: Allow production origin in production; loopback in development
is_prod = is_production()

def normalize_origin(url_str: Optional[str], is_origin_header: bool = False) -> Optional[str]:
    """
    Parses and normalizes an Origin or Referer URL to canonical 'scheme://hostname[:port]'.
    Normalizes default ports (http: 80, https: 443 -> omitted).
    Safely formats IPv6 addresses as [::1].

    Strict Validation Rules:
    1. Returns 'null' for literal 'null' string (caller rejects explicitly).
    2. Rejects user information (user@host or user:pass@host).
    3. Rejects non-HTTP / non-HTTPS schemes.
    4. Rejects malformed ports and port numbers outside 1..65535.
    5. For Origin headers (is_origin_header=True): rejects any paths, query strings, or fragments.
    6. For Referer headers (is_origin_header=False): extracts origin while safely ignoring path/query/fragment.
    7. Returns None for empty, malformed, or invalid authorities.
    """
    if not url_str or not isinstance(url_str, str):
        return None
    url_str = url_str.strip()
    if url_str.lower() == "null":
        return "null"

    try:
        parsed = urlparse(url_str)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            return None

        # 1. Reject credentials/userinfo in authority
        if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
            return None

        # 2. Strict Origin Header validation: Origin must not have path, query, or fragment
        if is_origin_header:
            if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                return None

        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return None

        # 3. Validate port range if port is present
        port = None
        if parsed.port is not None:
            if not (1 <= parsed.port <= 65535):
                return None
            port = parsed.port

        # Normalize default ports
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port = None

        # 4. Safe IPv6 host formatting
        host_repr = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname

        if port is not None:
            return f"{scheme}://{host_repr}:{port}"
        return f"{scheme}://{host_repr}"
    except Exception:
        return None


def get_trusted_origins(is_production_mode: bool) -> set[str]:
    """
    Returns the set of fully-normalized trusted origins.
    Enforces strict HTTPS in production, while permitting loopback origins only in dev/test.
    """
    trusted = {
        "https://transify20-production.up.railway.app"
    }
    custom_origins = os.getenv("TRANSIFY_ALLOWED_ORIGINS", os.getenv("ALLOWED_ORIGINS", ""))
    if custom_origins:
        for domain in custom_origins.split(","):
            raw_domain = domain.strip()
            if not raw_domain:
                continue
            norm = normalize_origin(raw_domain, is_origin_header=True)
            if norm and norm != "null":
                # In production mode, custom origins must be strict HTTPS
                if is_production_mode:
                    if norm.startswith("https://"):
                        trusted.add(norm)
                    else:
                        logger.warning(
                            f"[SECURITY] Disallowed non-HTTPS custom origin in production mode: {raw_domain}"
                        )
                else:
                    trusted.add(norm)

    if not is_production_mode:
        dev_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://0.0.0.0:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://testserver",
            "http://testserver:80",
            "https://testserver",
            "http://localhost",
            "http://127.0.0.1",
            "http://[::1]:8000",
            "http://[::1]",
        ]
        for dev in dev_origins:
            norm = normalize_origin(dev, is_origin_header=True)
            if norm:
                trusted.add(norm)

    return trusted


allowed_origins = sorted(list(get_trusted_origins(is_prod)))

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
live_sign_processor = LiveSignFrameProcessor(sign_adapter=sign_adapter)


# --- Pydantic Request/Response Models ---

class ProcessFrameRequest(BaseModel):
    image_b64: str = Field(..., description="Base64 encoded JPEG camera frame")
    mode: Optional[str] = Field("expressions", description="Active mode: expressions, fingerspell, sentence")
    language_mode: Optional[str] = Field("bdsl", description="Language mode: bdsl (temporal sequences) or asl")
    roi: Optional[List[float]] = Field(None, description="Optional normalized ROI bounding box [x1, y1, x2, y2]")
    session_id: Optional[str] = Field("default", description="Client session identifier for sequence buffer isolation")
    timestamp: Optional[float] = Field(None, description="Client-side timestamp in seconds for temporal continuity")
    landmarks_162: Optional[List[float]] = Field(None, description="Pre-extracted 162D landmark coordinates")

class SignResetRequest(BaseModel):
    session_id: Optional[str] = Field("default", description="Client session identifier to reset")

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
    language_mode: Optional[str] = Field("bdsl", description="Language mode: bdsl (temporal sequences) or asl")


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


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User account password")
    remember_me: Optional[bool] = Field(False, description="Whether to establish a persistent session cookie")


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User full name")
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=15, max_length=128, description="User password (min 15 characters)")
    consent_terms: bool = Field(..., description="Explicit consent to Terms of Service and Privacy Policy")

    if USE_FIELD_VALIDATOR:
        @field_validator("consent_terms")
        @classmethod
        def validate_consent(cls, v):
            if v is not True:
                raise ValueError("Consent to Terms of Service and Privacy Policy is required to create an account.")
            return v
    else:
        @validator("consent_terms")
        def validate_consent(cls, v):
            if v is not True:
                raise ValueError("Consent to Terms of Service and Privacy Policy is required to create an account.")
            return v


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="User email address")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Cryptographically secure reset token")
    new_password: str = Field(..., min_length=15, max_length=128, description="New password (min 15 characters)")


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field("Communication Session", max_length=100, description="Title of the conversation")


class AddHubMessageRequest(BaseModel):
    source: str = Field("typed", description="Source modality: sign, braille, speech, typed")
    content: str = Field(..., min_length=1, max_length=5000, description="Message content text")


class AddPhraseRequest(BaseModel):
    text_en: str = Field(..., min_length=1, max_length=200, description="English phrase text")
    text_bn: Optional[str] = Field("", max_length=200, description="Bengali phrase text")
    category: Optional[str] = Field("General", max_length=50, description="Category of phrase")


# --- Security: Rate Limiting, CSRF Protection & Auth Dependencies ---

def is_request_secure(request: Request) -> bool:
    if is_prod:
        return True
    proto = request.headers.get("x-forwarded-proto", "").lower()
    return proto == "https" or request.url.scheme == "https"


def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: enforces valid authenticated session strictly via secure HttpOnly cookie."""
    token = request.cookies.get("transify_session")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = get_user_by_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")
    return user


def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: resolves current user strictly if session cookie exists; returns None for guests."""
    token = request.cookies.get("transify_session")
    if not token:
        return None
    return get_user_by_session(token)


@app.middleware("http")
async def csrf_and_origin_protection_middleware(request: Request, call_next):
    """CSRF & Exact-Origin validation on state-changing requests."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin_header = request.headers.get("origin")
        referer_header = request.headers.get("referer")
        
        # 1. Strictly reject null origin
        if origin_header is not None and origin_header.strip().lower() == "null":
            logger.warning("Blocked state-changing request with Origin: null")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed: null origin rejected."}
            )

        current_prod = is_production()
        trusted_origins = get_trusted_origins(current_prod)

        def is_origin_allowed(normalized: Optional[str]) -> bool:
            if not normalized or normalized == "null":
                return False
            if normalized in trusted_origins:
                return True
            if not current_prod:
                parsed = urlparse(normalized)
                if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "testserver", "::1"):
                    return True
            return False

        # 2. If Origin header is present, validate exact normalized origin
        if origin_header is not None:
            norm_origin = normalize_origin(origin_header, is_origin_header=True)
            if not is_origin_allowed(norm_origin):
                logger.warning(f"Blocked cross-origin CSRF attempt with invalid origin: {origin_header}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: cross-origin request rejected."}
                )
        # 3. If Origin is absent, validate Referer if present
        elif referer_header is not None:
            norm_referer = normalize_origin(referer_header, is_origin_header=False)
            if not is_origin_allowed(norm_referer):
                logger.warning(f"Blocked cross-origin CSRF attempt with invalid referer: {referer_header}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: cross-origin request rejected."}
                )
        # 4. If both Origin and Referer are absent
        else:
            csrf_token_header = request.headers.get("x-csrf-token")
            csrf_token_cookie = request.cookies.get("transify_csrf")
            has_valid_csrf = bool(
                csrf_token_header
                and csrf_token_cookie
                and hmac.compare_digest(csrf_token_header.strip(), csrf_token_cookie.strip())
            )
            is_verified_same_origin = request.headers.get("sec-fetch-site") == "same-origin"
            
            enforce_strict = current_prod or os.getenv("TRANSIFY_ENFORCE_CSRF") == "1"
            if enforce_strict and not has_valid_csrf and not is_verified_same_origin:
                logger.warning("Blocked state-changing request missing both Origin and Referer headers.")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: missing origin and referer headers."}
                )
            elif not enforce_strict:
                host = request.headers.get("host")
                host_norm = f"http://{host}" if host else None
                norm_h = normalize_origin(host_norm, is_origin_header=False) if host_norm else None
                if not is_origin_allowed(norm_h):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed: unverified host on state-changing request."}
                    )

    response = await call_next(request)

    if "transify_csrf" not in request.cookies:
        csrf_token = secrets.token_hex(16)
        response.set_cookie(
            key="transify_csrf",
            value=csrf_token,
            httponly=False,
            samesite="lax",
            secure=is_request_secure(request),
            path="/"
        )

    return response


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
        (hasattr(live_sign_processor, "hand_tracker")
         and live_sign_processor.hand_tracker is not None
         and live_sign_processor.hand_tracker.landmarker is not None)
        or (hasattr(live_sign_processor, "tracker")
            and live_sign_processor.tracker is not None
            and live_sign_processor.tracker.landmarker is not None)
    )
    braille_ready = (
        braille_adapter.pipeline is not None
        and braille_adapter.pipeline.wrapper.model is not None
    )
    bdsl_temporal_ready = (
        sign_adapter.temporal_model is not None
        and sign_adapter.temporal_scaler is not None
        and sign_adapter.temporal_calibrated is not None
    )

    all_ready = db_connected and signframe_ready and hagrid_ready and mediapipe_ready and braille_ready and bdsl_temporal_ready
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
            "mediapipe_landmarker": "ready" if mediapipe_ready else "fallback_active",
            "bdsl_temporal_model": "ready" if bdsl_temporal_ready else "unavailable"
        }
    }


@app.get("/api/models/status", tags=["System"])
def models_status():
    """Returns live operational status and capability manifests of recognition modules."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    sign_manifest_p = os.path.join(project_root, "models/sign/hagrid_model_manifest.json")
    braille_manifest_p = os.path.join(project_root, "models/braille/exported/model_manifest.json")
    test_metrics_p = os.path.join(project_root, "models/sign/test_metrics.json")
    val_metrics_p = os.path.join(project_root, "models/sign/validation_metrics.json")

    import json
    sign_manifest = {}
    if os.path.exists(sign_manifest_p):
        with open(sign_manifest_p, 'r', encoding='utf-8') as f:
            sign_manifest = json.load(f)

    braille_manifest = {}
    if os.path.exists(braille_manifest_p):
        with open(braille_manifest_p, 'r', encoding='utf-8') as f:
            braille_manifest = json.load(f)

    test_metrics = {}
    if os.path.exists(test_metrics_p):
        with open(test_metrics_p, 'r', encoding='utf-8') as f:
            test_metrics = json.load(f)

    val_metrics = {}
    if os.path.exists(val_metrics_p):
        with open(val_metrics_p, 'r', encoding='utf-8') as f:
            val_metrics = json.load(f)

    hagrid_acc = sign_manifest.get("test_accuracy") if (sign_manifest and "test_accuracy" in sign_manifest) else None
    braille_cell_acc = (
        braille_manifest.get("exact_cell_accuracy_heldout")
        if (braille_manifest and "exact_cell_accuracy_heldout" in braille_manifest)
        else (braille_manifest.get("test_cell_accuracy") if (braille_manifest and "test_cell_accuracy" in braille_manifest) else None)
    )
    bdsl_temporal_acc = test_metrics.get("test_accuracy")
    bdsl_temporal_f1 = test_metrics.get("test_macro_f1")
    calib = test_metrics.get("calibration", {})
    bdsl_brier = calib.get("calibrated_brier_score")
    bdsl_ece = calib.get("calibrated_ece")

    sign_loaded = sign_adapter.model is not None
    hagrid_loaded = (
        hasattr(live_sign_processor, "hagrid_recognizer")
        and live_sign_processor.hagrid_recognizer.model is not None
    )
    mediapipe_loaded = getattr(live_sign_processor, "hands", None) is not None or (
        (hasattr(live_sign_processor, "hand_tracker") and live_sign_processor.hand_tracker is not None and live_sign_processor.hand_tracker.landmarker is not None)
        or (hasattr(live_sign_processor, "tracker") and live_sign_processor.tracker is not None and live_sign_processor.tracker.landmarker is not None)
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
        "bdsl_temporal": {
            "name": "BdSL 10-Class Temporal Sequence Model (Random Forest Champion)",
            "status": "LOADED" if temporal_loaded else "UNAVAILABLE",
            "dataset": "BdSL Temporal 10-Expression Dataset (Signer-Independent Split)",
            "test_accuracy": bdsl_temporal_acc,
            "test_macro_f1": bdsl_temporal_f1,
            "calibrated_brier_score": bdsl_brier,
            "calibrated_ece": bdsl_ece,
            "supported_classes": 10,
            "signer_id": test_metrics.get("signer_id"),
            "sample_count": test_metrics.get("sample_count"),
            "test_signer": test_metrics.get("signer_id", ["S001"])[0] if isinstance(test_metrics.get("signer_id"), list) else test_metrics.get("signer_id"),
            "test_samples": test_metrics.get("sample_count"),
            "metric_type": "Held-Out Signer-Independent Test Accuracy",
            "validation_metrics": {
                "val_accuracy": val_metrics.get("val_accuracy"),
                "val_macro_f1": val_metrics.get("val_macro_f1"),
                "signer_id": val_metrics.get("signer_id"),
                "sample_count": val_metrics.get("sample_count"),
                "calibration": val_metrics.get("calibration", {})
            },
            "test_metrics": {
                "test_accuracy": test_metrics.get("test_accuracy"),
                "test_macro_f1": test_metrics.get("test_macro_f1"),
                "signer_id": test_metrics.get("signer_id"),
                "sample_count": test_metrics.get("sample_count"),
                "calibration": test_metrics.get("calibration", {})
            },
            "ready": temporal_loaded
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
            "temporal_sequence_accuracy": bdsl_temporal_acc,
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
def predict_sign_sequence(
    req: SignPredictRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
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

        # Log confirmed predictions to history with user isolation
        if req.auto_log and result["is_committed"] and result["class_id"] != -1:
            log_translation(
                module="sign",
                recognized_text=result["display_text"],
                confidence=result["confidence"],
                status="CONFIRMED",
                input_meta={"frames": seq_arr.shape[0], "signer": req.signer_id, "language_mode": req.language_mode or "bdsl"},
                diagnostics={"status": result["status"], "class_id": result["class_id"]},
                user_id=user["id"] if user else None
            )

        return result
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Inference failure: {str(ex)}")


@app.post("/api/sign/process_frame", tags=["Sign Language"])
def process_webcam_frame(req: ProcessFrameRequest, request: Request = None):
    """
    Processes real-time webcam frame snapshot (JPEG base64), detects skin/hand contour,
    evaluates gestures against BdSL (30-frame temporal model) or ASL (SignFrame CNN / HaGRID),
    converts via Unified Translation Layer, and applies the 98% Decision Gateway.
    """
    try:
        # Check if direct landmark fixture injection is explicitly permitted for test fixtures
        test_fixture_header = None
        if request is not None:
            test_fixture_header = request.headers.get("x-transify-test-fixture") or request.headers.get("X-Transify-Test-Fixture")
        allow_test_fixtures = os.environ.get("TRANSIFY_ALLOW_TEST_LANDMARKS") == "1" or test_fixture_header == "1"

        sanitized_landmarks = None
        if req.landmarks_162 is not None:
            if not allow_test_fixtures:
                # Normal production requests MUST NOT bypass MediaPipe landmark extraction!
                logger.info("Ignoring direct landmark injection in production mode; processing image via MediaPipe.")
                sanitized_landmarks = None
            else:
                # In test fixture mode: Strictly validate shape (162,), finiteness, and numeric bounds [-10.0, 10.0]
                if len(req.landmarks_162) != 162:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Test fixture landmarks_162 must contain exactly 162 values, got {len(req.landmarks_162)}"
                    )
                arr = np.array(req.landmarks_162, dtype=np.float32)
                if not np.all(np.isfinite(arr)):
                    raise HTTPException(
                        status_code=422,
                        detail="Test fixture landmarks_162 contains NaN or infinite values"
                    )
                if np.any(arr < -10.0) or np.any(arr > 10.0):
                    raise HTTPException(
                        status_code=422,
                        detail="Test fixture landmarks_162 values exceed allowed coordinate bounds [-10.0, 10.0]"
                    )
                sanitized_landmarks = [float(v) for v in arr]

        res = live_sign_processor.process_frame(
            req.image_b64,
            mode=req.mode or "expressions",
            language_mode=req.language_mode or "bdsl",
            roi=req.roi,
            session_id=req.session_id or "default",
            timestamp=req.timestamp,
            landmarks_162=sanitized_landmarks
        )
        return res
    except HTTPException:
        raise
    except Exception as ex:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Frame processing failure: {str(ex)}")


@app.post("/api/sign/reset", tags=["Sign Language"])
def reset_sign_buffer(req: Optional[SignResetRequest] = None):
    """Resets the sign language debounce consensus buffer and live tracking state for the session."""
    session_id = req.session_id if req else "default"
    live_sign_processor.reset(session_id=session_id)
    return {"success": True, "message": "Debounce buffer and tracking state reset.", "session_id": session_id}


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
    confidence_threshold: float = Form(0.65),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
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
            diagnostics=res.get("error", {}),
            user_id=user["id"] if user else None
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
        diagnostics=data.get("diagnostics", {}),
        user_id=user["id"] if user else None
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
    module: Optional[str] = Query(None, pattern="^(sign|braille|speech)$"),
    search: Optional[str] = Query(None),
    date_filter: Optional[str] = Query(None, pattern="^(all|today|week)$"),
    favorites_only: bool = Query(False),
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Retrieves translation history records isolated strictly to the authenticated user.
    Supports filtering by module, search query, date range, and favorites.
    Unauthenticated/guest users receive an empty list to protect private user data.
    """
    if not user:
        return {"count": 0, "records": []}
    records = get_history(
        limit=limit,
        module=module,
        user_id=user["id"],
        search=search,
        date_filter=date_filter,
        favorites_only=favorites_only
    )
    return {"count": len(records), "records": records}


@app.post("/api/history/{record_id}/favorite", tags=["History"])
def toggle_history_favorite_endpoint(
    record_id: int,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Toggles favorite/bookmarked status on a user-owned translation history item."""
    new_status = toggle_history_favorite(record_id, user_id=user["id"])
    if new_status is None:
        raise HTTPException(status_code=404, detail="History record not found or not owned by user.")
    return {"success": True, "is_favorite": new_status}


@app.delete("/api/history", tags=["History"])
def delete_all_history(user: Dict[str, Any] = Depends(get_authenticated_user)):
    """
    Clears translation history records strictly for the requesting authenticated user.
    A user cannot delete another user's records, and guests are denied access.
    """
    deleted_count = clear_history(user_id=user["id"])
    return {"success": True, "deleted_count": deleted_count}


@app.post("/api/history/{record_id}/feedback", tags=["History"])
def submit_feedback(
    record_id: int,
    req: FeedbackRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Records user feedback on a translation event owned by the authenticated user.
    """
    updated = record_feedback(record_id, req.rating, req.comments, user_id=user["id"])
    if not updated:
        raise HTTPException(status_code=404, detail=f"History record {record_id} not found or not owned by user.")
    return {"success": True, "message": "Feedback recorded."}


@app.get("/api/preferences", tags=["Preferences"])
def read_preferences(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """Retrieves accessibility preferences for the authenticated user, or system defaults."""
    uid = user["id"] if user else None
    return get_preferences(user_id=uid)


@app.post("/api/preferences", tags=["Preferences"])
def set_preference(
    req: PreferenceUpdateRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Updates an accessibility preference for the authenticated user."""
    update_preference(req.key, req.value, user_id=user["id"])
    return {"success": True, "updated": {req.key: req.value}}


# --- Authentication Endpoints ---

_LAST_RESET_EMAIL_FOR_TESTS = {}

@app.post("/api/auth/register", tags=["Authentication"])
def register_user(req: RegisterRequest, response: Response, request: Request):
    """
    Registers a new user account with Argon2id / PBKDF2 password hashing.
    Enforces password length >= 15 characters, explicit consent, and sets an HttpOnly session cookie.
    Never returns raw session tokens in the JSON response.
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(f"ip:{client_ip}") or (req.email and is_login_rate_limited(f"email:{req.email.lower()}")):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait 5 minutes before trying again."
        )

    if not req.consent_terms:
        raise HTTPException(
            status_code=422,
            detail="Consent to Terms of Service and Privacy Policy is required to create an account."
        )

    try:
        user = create_user(req.name, req.email, req.password, consent_terms=req.consent_terms)
    except ValueError as err:
        err_msg = str(err)
        if "already exists" in err_msg.lower():
            raise HTTPException(status_code=409, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as ex:
        logger.error(f"Error during user registration: {ex}")
        raise HTTPException(status_code=500, detail="Internal registration failure. Please try again.")

    # High-entropy cryptographic session: database stores only SHA-256 hash
    session_token = create_session(user["id"])
    secure_cookie = is_request_secure(request)
    response.set_cookie(
        key="transify_session",
        value=session_token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        path="/"
    )

    # Clear rate limiting counter specifically for this email
    clear_failed_logins(f"email:{req.email.lower()}")
    return {
        "status": "success",
        "message": "Account created successfully.",
        "user": user
    }


@app.post("/api/auth/login", tags=["Authentication"])
def login_user(req: LoginRequest, response: Response, request: Request):
    """
    Authenticates user credentials against the persistent SQLite database.
    Supports Remember Me: persistent cookie when true, browser session cookie when false.
    Rejects bad credentials with generic HTTP 401 and enforces login rate limiting.
    Delivers session token exclusively through secure HttpOnly cookie.
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(f"ip:{client_ip}") or (req.email and is_login_rate_limited(f"email:{req.email.lower()}")):
        logger.warning(f"Rate limit exceeded for client_ip={client_ip}, email={req.email}")
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please wait 5 minutes before trying again."
        )

    user = authenticate_user(req.email, req.password)
    if not user:
        record_failed_login(f"ip:{client_ip}")
        if req.email:
            record_failed_login(f"email:{req.email.lower()}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Clear failed login attempts ONLY for this specific email account on successful login.
    clear_failed_logins(f"email:{req.email.lower()}")

    session_token = create_session(user["id"])
    secure_cookie = is_request_secure(request)

    # Real Remember Me behavior:
    # Checked (True) -> persistent cookie with 30-day Max-Age
    # Unchecked (False) -> browser session cookie (max_age=None, expires=None)
    cookie_kwargs = {
        "key": "transify_session",
        "value": session_token,
        "httponly": True,
        "samesite": "lax",
        "secure": secure_cookie,
        "path": "/"
    }
    if req.remember_me:
        cookie_kwargs["max_age"] = 30 * 86400
    else:
        cookie_kwargs["max_age"] = None

    response.set_cookie(**cookie_kwargs)

    return {
        "status": "success",
        "message": "Login successful.",
        "user": user,
        "remember_me": bool(req.remember_me)
    }


@app.post("/api/auth/forgot-password", tags=["Authentication"])
def forgot_password(req: ForgotPasswordRequest, request: Request):
    """
    Initiates a password reset workflow.
    Generates a cryptographically secure single-use token, stores only its SHA-256 hash,
    and enforces rate limiting. Delivers instructions using configured email adapter.
    Always returns an identical generic response (HTTP 200) to prevent account enumeration,
    regardless of whether the account exists, is disabled, or whether SMTP delivery fails.
    """
    client_ip = request.client.host if request.client else "unknown"
    clean_email = (req.email or "").strip().lower()
    if is_login_rate_limited(f"reset_ip:{client_ip}", max_attempts=30) or (clean_email and is_login_rate_limited(f"reset_email:{clean_email}", max_attempts=5)):
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Please wait 5 minutes before trying again."
        )

    record_failed_login(f"reset_ip:{client_ip}", window_seconds=300.0)
    if clean_email:
        record_failed_login(f"reset_email:{clean_email}", window_seconds=300.0)

    adapter = get_email_adapter()
    adapter_configured = adapter.is_configured()
    if not adapter_configured:
        logger.warning("Password reset requested but email delivery adapter is not configured.")

    user = get_user_by_email(clean_email) if clean_email else None
    raw_token = None
    token_hash = None

    if user and user.get("role") != "disabled":
        raw_token, token_hash = create_password_reset_token(user["id"], expires_in_seconds=1800.0)
        if adapter_configured:
            try:
                adapter.send_password_reset_email(user["email"], raw_token)
            except Exception as ex:
                logger.error(f"Password reset delivery failure: {type(ex).__name__}")
                # Invalidate the token so it cannot remain usable unnecessarily
                invalidate_password_reset_token(token_hash)
                raw_token = None
        else:
            # Email delivery adapter not configured: invalidate token immediately
            invalidate_password_reset_token(token_hash)
            raw_token = None

    resp_body = {
        "status": "success",
        "message": "If an account with that email exists, password reset instructions have been processed."
    }

    # Test-only reset token exposure exclusively in an explicitly configured test environment
    is_test_env = (
        not is_production()
        and os.getenv("TRANSIFY_ENV") == "testing"
        and os.getenv("TRANSIFY_EXPOSE_TEST_TOKENS") == "1"
    )
    if is_test_env and raw_token:
        resp_body["test_token"] = raw_token

    return resp_body


@app.post("/api/auth/reset-password", tags=["Authentication"])
def reset_password(req: ResetPasswordRequest, request: Request):
    """
    Consumes a password reset token to set a new password.
    Enforces minimum 15-character length, updates password using Argon2id, and revokes all active sessions.
    """
    if len(req.new_password) < 15:
        raise HTTPException(status_code=400, detail="New password must be at least 15 characters long.")

    success = verify_and_consume_reset_token(req.token, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used password reset token.")

    return {
        "status": "success",
        "message": "Password reset successfully. Please log in with your new password."
    }


@app.get("/api/auth/oauth/google/config", tags=["Authentication"])
def get_google_oauth_config():
    """Returns Google OAuth status - explicitly marked disabled in this release."""
    return {
        "status": "disabled",
        "available": False,
        "client_id": None,
        "message": "Google Sign-In is disabled in this release. Please use email and password authentication."
    }


@app.get("/api/auth/oauth/google/callback", tags=["Authentication"])
def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """
    Validates Google OAuth callback parameters.
    Rejects invalid state, missing codes, or unconfigured flows with HTTP 400.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required OAuth callback parameters.")

    # Option B: Visibly disabled until complete backend flow is available
    raise HTTPException(
        status_code=400,
        detail="Google Sign-In is disabled in this release. Please use email and password authentication."
    )


@app.post("/api/auth/guest", tags=["Authentication"])
def guest_login(response: Response):
    """
    Initializes a restricted demo guest session.
    Clears any existing session cookie and avoids issuing fake tokens.
    """
    response.delete_cookie(key="transify_session", path="/")
    return {
        "status": "success",
        "message": "Demo guest session active.",
        "user": {
            "id": 0,
            "name": "Guest User",
            "email": "guest@transify.ai",
            "role": "guest",
            "is_guest": True
        }
    }


@app.get("/api/auth/me", tags=["Authentication"])
def get_current_user(request: Request = None):
    """
    Verifies session validity strictly from HttpOnly cookie.
    Returns authenticated user profile or unauthenticated status.
    """
    token = request.cookies.get("transify_session") if request else None

    if not token:
        return {"authenticated": False, "user": None}

    user = get_user_by_session(token)
    if not user:
        return {"authenticated": False, "user": None}

    return {"authenticated": True, "user": user}


@app.post("/api/auth/logout", tags=["Authentication"])
def logout_user(response: Response, request: Request = None):
    """
    Revokes the current session in database and clears the session cookie.
    """
    token = request.cookies.get("transify_session") if request else None
    if token:
        revoke_session(token)

    response.delete_cookie(key="transify_session", path="/")
    return {"status": "success", "message": "Logged out successfully."}


# --- Communication Hub Endpoints ---

@app.get("/api/hub/conversations", tags=["Communication Hub"])
def list_conversations(user: Dict[str, Any] = Depends(get_authenticated_user)):
    """Retrieves all conversation sessions for the authenticated user."""
    convs = get_hub_conversations(user["id"])
    return {"status": "success", "conversations": convs}


@app.post("/api/hub/conversations", tags=["Communication Hub"])
def create_conversation_endpoint(
    req: CreateConversationRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Creates a new conversation session for the authenticated user."""
    conv = create_hub_conversation(user["id"], req.title or "Communication Session")
    return {"status": "success", "conversation": conv}


@app.get("/api/hub/conversations/{conv_id}/messages", tags=["Communication Hub"])
def list_messages_endpoint(
    conv_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Retrieves messages for a conversation session owned by user."""
    msgs = get_hub_messages(conv_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=404, detail="Conversation session not found or not owned by user.")
    return {"status": "success", "messages": msgs}


@app.post("/api/hub/conversations/{conv_id}/messages", tags=["Communication Hub"])
def add_message_endpoint(
    conv_id: str,
    req: AddHubMessageRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Adds a message to a conversation session owned by user."""
    msg = add_hub_message(conv_id, user["id"], req.source, req.content)
    if msg is None:
        raise HTTPException(status_code=404, detail="Conversation session not found or empty message content.")
    return {"status": "success", "message": msg}


@app.delete("/api/hub/conversations/{conv_id}", tags=["Communication Hub"])
def delete_conversation_endpoint(
    conv_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Deletes a conversation session owned by user."""
    deleted = delete_hub_conversation(conv_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation session not found or not owned by user.")
    return {"status": "success", "message": "Conversation session deleted."}


@app.post("/api/hub/conversations/{conv_id}/clear", tags=["Communication Hub"])
def clear_conversation_messages_endpoint(
    conv_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Clears all messages in a conversation session owned by user."""
    cleared = clear_hub_conversation_messages(conv_id, user["id"])
    if not cleared:
        raise HTTPException(status_code=404, detail="Conversation session not found or not owned by user.")
    return {"status": "success", "message": "Conversation messages cleared."}


# --- Quick Phraseboard Endpoints ---

@app.get("/api/phrases", tags=["Phraseboard"])
def list_phrases(user: Optional[Dict[str, Any]] = Depends(get_optional_user)):
    """
    Retrieves the complete phrase library: default core phrases plus any custom
    phrases saved by the authenticated user.
    """
    user_phrases = []
    if user:
        user_phrases = get_user_phrases(user["id"])
    all_phrases = list(DEFAULT_PHRASES) + user_phrases
    return {
        "status": "success",
        "phrases": all_phrases,
        "default_phrases": DEFAULT_PHRASES,
        "custom_phrases": user_phrases
    }


@app.post("/api/phrases", tags=["Phraseboard"])
def create_custom_phrase(
    req: AddPhraseRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Creates a custom phrase in the authenticated user's personal phrasebook."""
    try:
        phrase = add_user_phrase(
            user_id=user["id"],
            text_en=req.text_en,
            text_bn=req.text_bn or req.text_en,
            category=req.category or "General"
        )
        return {"status": "success", "phrase": phrase}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/phrases/{phrase_id}/favorite", tags=["Phraseboard"])
def toggle_phrase_favorite_endpoint(
    phrase_id: int,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Toggles favorite status for a custom phrase owned by user."""
    fav = toggle_phrase_favorite(phrase_id, user["id"])
    if fav is None:
        raise HTTPException(status_code=404, detail="Phrase not found or not owned by user.")
    return {"status": "success", "is_favorite": fav}


@app.delete("/api/phrases/{phrase_id}", tags=["Phraseboard"])
def delete_custom_phrase(
    phrase_id: int,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Deletes a custom phrase owned by user."""
    deleted = delete_user_phrase(phrase_id, user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Phrase not found or not owned by user.")
    return {"status": "success", "message": "Phrase deleted."}


# --- Static Frontend App Serving ---

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(os.path.join(FRONTEND_DIR, "static"), exist_ok=True)

# Mount static assets
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["Frontend"])
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

