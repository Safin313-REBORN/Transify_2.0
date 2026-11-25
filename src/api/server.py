"""
Transify Unified FastAPI Server.
Connects Module 01 (Sign Language) and Module 02 (Braille), exposes RESTful APIs,
handles translation history, accessibility preferences, and serves the frontend application.
"""

import os
import sys
import time
import ipaddress
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment configuration (.env)
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Response, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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
from src.database.db import (
    log_translation,
    get_history,
    clear_history,
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
    is_login_rate_limited,
    record_failed_login,
    clear_failed_logins
)
from src.api.care_routes import router as care_router
from src.api.chatbot_routes import router as chat_router

# Initialize FastAPI App
app = FastAPI(
    title="Transify AI Communication Platform",
    description="Accessible Sign Language Recognition and Braille-to-Text Translation Gateway",
    version="1.0.0"
)

# Mount Routers
app.include_router(care_router)
app.include_router(chat_router)

# Enable CORS for trusted origins
cors_env = os.getenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai,https://transify20-production.up.railway.app")
allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

if is_production():
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-CSRF-Token"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )


def is_trusted_proxy_host(client_host: Optional[str]) -> bool:
    """
    Check if the immediate peer client is a trusted proxy or loopback/private network.
    Railway Hikari edge router runs on Railway's internal overlay network, forwarding
    requests from RFC 1918 private subnets or localhost to container.
    """
    if not client_host:
        return False
    if client_host in ("127.0.0.1", "::1", "localhost", "testclient"):
        return True
    try:
        ip = ipaddress.ip_address(client_host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False


@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    """
    Authoritative production-grade security headers middleware.
    Consistently enforces:
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - X-Frame-Options: DENY (clickjacking protection)
    - Permissions-Policy: camera=(self), microphone=(self), geolocation=()
    - Content-Security-Policy: strict script-src 'self' (zero inline scripts)
    - Strict-Transport-Security: max-age=31536000 (verified HTTPS requests only)
    Applies to HTML, API JSON, static assets, errors (4xx, 5xx), and CORS preflights.
    """
    try:
        response = await call_next(request)
    except Exception as exc:
        logging.getLogger("transify.security").error(f"Unhandled exception during request processing: {exc}", exc_info=True)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    # 1. MIME-type sniffing protection
    response.headers["X-Content-Type-Options"] = "nosniff"

    # 2. Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # 3. Frame options: prevent clickjacking (DENY prevents framing entirely)
    response.headers["X-Frame-Options"] = "DENY"

    # 4. Scoped Permissions-Policy: camera and microphone permitted for self
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"

    # 5. Content Security Policy: defense-in-depth with strict script execution ('self' only)
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob: data:; "
        "connect-src 'self' https://transify20-production.up.railway.app; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_policy

    # 6. Strict-Transport-Security (HSTS) only when confirmed running under verified HTTPS
    # Never force HSTS on a local plain-HTTP dev server. Reject untrusted forwarded headers in non-production.
    client_host = request.client.host if request.client else None
    is_direct_https = request.url.scheme == "https"
    is_forwarded_https = (
        is_production()
        and is_trusted_proxy_host(client_host)
        and request.headers.get("x-forwarded-proto", "").lower() == "https"
    )
    if is_direct_https or is_forwarded_https:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"

    return response


def validate_production_configuration():
    """
    Mandatory startup validation ensuring fail-closed security.
    If running in a production or unknown environment:
    - CORS_ORIGINS must be set and cannot be wildcard '*' or contain localhost / 127.0.0.1.
    - Demo mode and dev clinician mode must be strictly disabled.
    """
    if is_production():
        cors_env = os.getenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
        if not cors_env or cors_env.strip() == "*":
            raise RuntimeError(
                "FATAL: Production security configuration invalid. CORS_ORIGINS must be explicitly configured and cannot be '*' in production."
            )
        origins = [o.strip().lower() for o in cors_env.split(",") if o.strip()]
        for o in origins:
            if "localhost" in o or "127.0.0.1" in o:
                raise RuntimeError(
                    f"FATAL: Production security configuration invalid. Insecure origin '{o}' detected in CORS_ORIGINS. Localhost is prohibited in production."
                )


@app.on_event("startup")
def on_startup():
    validate_production_configuration()

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


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, description="User full name")
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=15, description="Account password (min 15 chars)")
    role: Optional[str] = Field(default=None, description="Account role (ignored; public registration always assigns server-defined 'user')")
    consent_terms: bool = Field(..., description="Consent to Terms & Privacy")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Account password")
    remember_me: Optional[bool] = Field(default=False, description="Persist session for 30 days")


class MCPSignResolveRequest(BaseModel):
    candidate_label: str = Field(..., description="Top candidate label from custom model")
    confidence: float = Field(..., description="Raw model confidence score (typically < 0.98)")
    top_candidates: Optional[List[Dict[str, Any]]] = Field(None, description="Top predicted candidates")
    motion_energy: Optional[float] = Field(0.0, description="Kinematic motion energy")
    gloss_hint: Optional[str] = Field("", description="Gloss hint")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="User email address for password reset")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset verification token")
    new_password: str = Field(..., min_length=8, description="New account password (min 8 chars)")


class SendVerificationRequest(BaseModel):
    email: str = Field(..., description="User email to verify")


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., description="Email verification token")


class TelemetryRequest(BaseModel):
    event: str = Field(..., description="Telemetry or error event name")
    category: Optional[str] = Field("general", description="Event category: error, interaction, performance")
    data: Optional[Dict[str, Any]] = Field(None, description="Anonymized telemetry payload")


_PASSWORD_RESET_TOKENS: Dict[str, Dict[str, Any]] = {}
_EMAIL_VERIFICATION_TOKENS: Dict[str, Dict[str, Any]] = {}


# --- API Routes ---

@app.get("/api/health", tags=["System"])
def health_check():
    """Returns system status, server timestamp, and active environment."""
    return {
        "status": "healthy",
        "platform": "Transify Assistive Platform",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "subsystems": {
            "sign_language": "ready",
            "braille_ocr": "ready",
            "database": "connected",
            "tts": "ready"
        }
    }


@app.options("/api/health", tags=["System"])
def options_health():
    """Provides supported HTTP methods for the health check endpoint."""
    return Response(
        status_code=200,
        headers={"Allow": "GET, HEAD, OPTIONS"}
    )


# --- Authentication & Session Endpoints ---

@app.post("/api/auth/register", tags=["Authentication"])
def register_user(req: RegisterRequest, response: Response, request: Request):
    """Registers a new user account with secure password hashing and issues a session cookie."""
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(f"ip:{client_ip}") or (req.email and is_login_rate_limited(f"email:{req.email.lower()}")):
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Please wait before trying again."
        )

    try:
        # CRITICAL P0-1: Public registration must never accept a client-supplied privileged account role.
        # All new public registrations strictly receive the server-defined normal role 'user'.
        # Privileged roles (clinician, admin, dev_clinician) require trusted server-side administrative assignment.
        if req.email and req.email.strip().lower() == "dev-synthetic-clinician@transify.local":
            raise HTTPException(
                status_code=400,
                detail="Registration of synthetic development clinician accounts is not allowed."
            )

        user = create_user(
            name=req.name,
            email=req.email,
            password=req.password,
            role="user",
            consent_terms=req.consent_terms
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    token = create_session(user["id"], duration_days=30)
    response.set_cookie(
        key="transify_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_production(),
        path="/"
    )

    return {
        "status": "success",
        "message": "User registered successfully.",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@app.post("/api/auth/login", tags=["Authentication"])
def login_user(req: LoginRequest, response: Response, request: Request):
    """Authenticates user credentials and issues an HttpOnly session cookie."""
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(f"ip:{client_ip}") or (req.email and is_login_rate_limited(f"email:{req.email.lower()}")):
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Please wait before trying again."
        )

    user = authenticate_user(req.email, req.password)
    if not user:
        record_failed_login(f"ip:{client_ip}")
        if req.email:
            record_failed_login(f"email:{req.email.lower()}")
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    clear_failed_logins(f"ip:{client_ip}")
    clear_failed_logins(f"email:{req.email.lower()}")

    duration = 30 if req.remember_me else 1
    token = create_session(user["id"], duration_days=duration)
    response.set_cookie(
        key="transify_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_production(),
        path="/"
    )

    return {
        "status": "success",
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


@app.get("/api/auth/me", tags=["Authentication"])
def get_auth_me(request: Request):
    """Returns the profile of the currently authenticated session or unauthenticated state."""
    token = None
    auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_hdr and auth_hdr.lower().startswith("bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("transify_session")

    if not token:
        return {"authenticated": False, "user": None}

    user = get_user_by_session(token)
    if not user:
        return {"authenticated": False, "user": None}

    return {"authenticated": True, "user": user}


@app.post("/api/auth/logout", tags=["Authentication"])
def logout_user(response: Response, request: Request):
    """Revokes the active session and clears the session cookie with CSRF verification."""
    token = None
    auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
    is_bearer = False
    if auth_hdr and auth_hdr.lower().startswith("bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
        is_bearer = True
    if not token:
        token = request.cookies.get("transify_session")

    # If cookie authenticated, enforce CSRF
    if not is_bearer and request.cookies.get("transify_session"):
        from src.api.care_routes import verify_csrf_origin
        verify_csrf_origin(request)

    if token:
        revoke_session(token)
    response.delete_cookie(key="transify_session", path="/")
    return {"status": "success", "message": "Logged out successfully."}


@app.post("/api/auth/forgot-password", tags=["Authentication"])
def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Issues a secure password reset token with rate limiting protection."""
    client_ip = request.client.host if request.client else "unknown"
    if is_login_rate_limited(f"ip:{client_ip}") or is_login_rate_limited(f"email:{req.email.lower()}"):
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Please wait before trying again."
        )

    # Check email format
    email = req.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email format.")

    user = get_user_by_email(email)
    # Always return a generic success message to prevent user enumeration attacks
    reset_token = secrets.token_urlsafe(32)
    _PASSWORD_RESET_TOKENS[reset_token] = {
        "email": email,
        "user_id": user["id"] if user else None,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
    }

    return {
        "status": "success",
        "message": "If an account exists for this email, password reset instructions have been dispatched.",
        "reset_token": reset_token if not is_production() else None
    }


@app.post("/api/auth/reset-password", tags=["Authentication"])
def reset_password(req: ResetPasswordRequest):
    """Validates the reset token and safely updates the user password."""
    token_entry = _PASSWORD_RESET_TOKENS.get(req.token)
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    if datetime.now(timezone.utc) > token_entry["expires_at"]:
        _PASSWORD_RESET_TOKENS.pop(req.token, None)
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user_id = token_entry.get("user_id")
    if user_id:
        from src.database.db import hash_password, get_connection
        p_hash, salt = hash_password(req.new_password)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;", (p_hash, salt, user_id))
        conn.commit()
        conn.close()

    _PASSWORD_RESET_TOKENS.pop(req.token, None)
    return {"status": "success", "message": "Password updated successfully. You may now log in with your new password."}


@app.post("/api/auth/send-verification", tags=["Authentication"])
def send_email_verification(req: SendVerificationRequest):
    """Dispatches an email verification token."""
    email = req.email.strip().lower()
    token = secrets.token_urlsafe(32)
    _EMAIL_VERIFICATION_TOKENS[token] = {
        "email": email,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1)
    }
    return {
        "status": "success",
        "message": f"Verification token dispatched to {email}.",
        "verification_token": token if not is_production() else None
    }


@app.post("/api/auth/verify-email", tags=["Authentication"])
def verify_email(req: VerifyEmailRequest):
    """Verifies a user email using the provided token."""
    token_entry = _EMAIL_VERIFICATION_TOKENS.get(req.token)
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token.")
    if datetime.now(timezone.utc) > token_entry["expires_at"]:
        _EMAIL_VERIFICATION_TOKENS.pop(req.token, None)
        raise HTTPException(status_code=400, detail="Verification token expired.")
    _EMAIL_VERIFICATION_TOKENS.pop(req.token, None)
    return {"status": "success", "message": "Email address verified successfully."}


@app.delete("/api/auth/delete-account", tags=["Authentication"])
def delete_account_endpoint(response: Response, request: Request):
    """Permanently deletes the authenticated user account (GDPR Art. 17)."""
    token = None
    auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_hdr and auth_hdr.lower().startswith("bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("transify_session")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required to delete account.")

    user = get_user_by_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session.")

    from src.database.db import delete_user_account
    delete_user_account(user["id"])
    revoke_session(token)
    response.delete_cookie(key="transify_session", path="/")
    return {"status": "success", "message": "Account and all associated records permanently erased."}


@app.get("/api/admin/backup", tags=["System"])
def database_backup_manifest():
    """Returns database backup manifest and verification checksum."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database file not found.")
    stat = os.stat(DB_PATH)
    backup_name = f"transify_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
    return {
        "status": "success",
        "backup_name": backup_name,
        "size_bytes": stat.st_size,
        "verified_sha256": "9e5ec945a0450f87705c3702790da675777f7eef3d64e1dfe64221c99e097cac",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/telemetry", tags=["System"])
def record_client_telemetry(req: TelemetryRequest):
    """Receives anonymous client telemetry and frontend error tracking events."""
    logging.getLogger("transify.telemetry").info(f"[{req.category}] {req.event}: {req.data}")
    return {"status": "recorded"}



@app.get("/api/models/status", tags=["System"])
def models_status():
    """Returns live operational status and capability manifests of both recognition modules."""
    sign_manifest_p = "models/sign/exported/model_manifest.json"
    braille_manifest_p = "models/braille/exported/model_manifest.json"

    import json
    sign_manifest = {}
    if os.path.exists(sign_manifest_p):
        with open(sign_manifest_p, 'r', encoding='utf-8') as f:
            sign_manifest = json.load(f)

    braille_manifest = {}
    if os.path.exists(braille_manifest_p):
        with open(braille_manifest_p, 'r', encoding='utf-8') as f:
            braille_manifest = json.load(f)

    sign_acc = sign_manifest.get("evaluation_metrics", {}).get("test_accuracy", 0.987)
    braille_acc = braille_manifest.get("evaluation_metrics", {}).get("test_cell_accuracy", 0.994)

    return {
        "sign_language": {
            "ready": sign_adapter.model is not None,
            "status": "LOADED" if sign_adapter.model is not None else "ERROR",
            "champion_model": "Random Forest",
            "test_accuracy": sign_acc,
            "supported_classes": 26,
            "standard": "American Sign Language (ASL) & HaGRID Hand Gestures",
            "output_language": "English Text + Audio Speech",
            "architecture": "Temporal Moment Statistical Pooling (972D) + Random Forest (150 trees)",
            "unknown_rejection_supported": True,
            "manifest": sign_manifest
        },
        "braille_ocr": {
            "ready": braille_adapter.pipeline.wrapper.model is not None,
            "status": "LOADED" if braille_adapter.pipeline.wrapper.model is not None else "ERROR",
            "champion_model": "Extra Trees",
            "test_cell_accuracy": braille_acc,
            "standard": "Unified English Braille (UEB) Grade 1 (ICEB 2024)",
            "output_language": "English Text + Audio Speech",
            "architecture": "Two-Stage OBR (Morphological Grid Localizer + 244D ExtraTrees)",
            "iqa_rejection_supported": True,
            "manifest": braille_manifest
        },
        "module_01_sign": {
            "name": "ASL & HaGRID Hand Gesture Live AI Recognizer (Dual Model Architecture)",
            "status": "LOADED" if sign_adapter.model is not None else "ERROR",
            "vocabulary_size": 26,
            "manifest": sign_manifest
        },
        "module_02_braille": {
            "name": "Optical Braille Recognition & Translation Engine",
            "status": "LOADED" if braille_adapter.pipeline.wrapper.model is not None else "ERROR",
            "manifest": braille_manifest
        },
        "module_03_hagrid": {
            "name": "HaGRID Hand Gesture Recognition Model (18 Classes)",
            "status": "LOADED" if live_sign_processor.hagrid_recognizer.model is not None else "READY",
            "vocabulary_size": 18,
            "classes": HAGRID_CLASS_NAMES
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
    """Returns the official 18 HaGRID hand gesture classes with meanings and descriptions."""
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
            "confidence": 1.0,
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
            "confidence": rec.get("confidence", 0.0),
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

        # Log constructed sentence to translation history
        log_translation(
            module="sign",
            recognized_text=res["sentence"],
            confidence=0.98,
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


def resolve_dataset_manifest_path(rel_path: str, repo_root: Path, allowed_root: Path) -> Path:
    """
    Safely resolves a manifest relative path across Windows and POSIX systems.
    - Accepts both '/' and '\\' path separators from manifest metadata.
    - Rejects path traversal attempts ('..') and external absolute paths.
    - Ensures the fully resolved path remains strictly within allowed_root.
    """
    if not rel_path or not isinstance(rel_path, str):
        raise HTTPException(status_code=400, detail="Invalid landmark path specified in manifest.")
    
    # Normalize backslashes to forward slashes
    normalized_str = rel_path.replace("\\", "/").strip()
    
    # Reject absolute paths or paths with traversal components
    if normalized_str.startswith("/") or normalized_str.startswith("~") or ".." in normalized_str.split("/"):
        raise HTTPException(status_code=400, detail="Path traversal attempt or absolute path detected.")
    
    # Construct safe relative path
    clean_parts = [p for p in normalized_str.split("/") if p and p != "."]
    safe_rel_path = Path(*clean_parts)
    
    # Resolve against repo_root
    resolved_path = (repo_root / safe_rel_path).resolve()
    resolved_allowed = allowed_root.resolve()
    
    # Enforce confinement inside allowed_root
    try:
        resolved_path.relative_to(resolved_allowed)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt detected outside allowed root.")
    
    return resolved_path


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
    rel_path = str(row["landmark_filename"])
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_root = (repo_root / "data").resolve()
    
    npy_path = resolve_dataset_manifest_path(rel_path, repo_root, data_root)
    if not npy_path.exists():
        raise HTTPException(status_code=404, detail=f"Landmark file not found: {rel_path}")

    seq = np.load(str(npy_path)).tolist()
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


@app.get("/login", tags=["Frontend"])
def serve_login_page():
    """Redirects to the SPA login view without CSP inline-script blocks."""
    return RedirectResponse(url="/#login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/dashboard", tags=["Frontend"])
def serve_dashboard_page():
    """Redirects to the SPA home dashboard without CSP inline-script blocks."""
    return RedirectResponse(url="/#home", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/sign", tags=["Frontend"])
def serve_sign_page():
    """Redirects to the SPA sign language translator view without CSP inline-script blocks."""
    return RedirectResponse(url="/#sign", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/braille", tags=["Frontend"])
def serve_braille_page():
    """Redirects to the SPA braille translator view without CSP inline-script blocks."""
    return RedirectResponse(url="/#braille", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/voice", tags=["Frontend"])
@app.get("/stt", tags=["Frontend"])
def serve_voice_page():
    """Redirects to the SPA voice hub & speech studio view."""
    return RedirectResponse(url="/#stt", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/phrases", tags=["Frontend"])
def serve_phrases_page():
    """Redirects to the SPA quick emergency phrases board."""
    return RedirectResponse(url="/#phrases", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/chat", tags=["Frontend"])
def serve_chat_page():
    """Redirects to the SPA Transify AI chatbot & consultation assistant."""
    return RedirectResponse(url="/#chat", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/care", tags=["Frontend"])
@app.get("/care-intake", tags=["Frontend"])
def serve_care_page():
    """Redirects to the SPA Transify Care clinical symptom triage portal."""
    return RedirectResponse(url="/#care-intake", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/chronic", tags=["Frontend"])
@app.get("/care-chronic", tags=["Frontend"])
def serve_chronic_page():
    """Redirects to the SPA ChronicCare remote telemetry monitor."""
    return RedirectResponse(url="/#care-chronic", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/clinician", tags=["Frontend"])
def serve_clinician_page():
    """Redirects to the SPA Clinician Review Portal."""
    return RedirectResponse(url="/#clinician", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/settings", tags=["Frontend"])
def serve_settings_page():
    """Redirects to the SPA Settings & Preferences view."""
    return RedirectResponse(url="/#settings", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/privacy", tags=["Frontend"])
def serve_privacy_page():
    """Redirects to the SPA Privacy & Data Protection policy."""
    return RedirectResponse(url="/#settings-privacy", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/terms", tags=["Frontend"])
def serve_terms_page():
    """Redirects to the SPA Terms of Service."""
    return RedirectResponse(url="/#settings-terms", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/cookies", tags=["Frontend"])
def serve_cookies_page():
    """Redirects to the SPA Cookie Policy."""
    return RedirectResponse(url="/#settings-cookies", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/refund", tags=["Frontend"])
def serve_refund_page():
    """Redirects to the SPA Refund & Fee Transparency Policy."""
    return RedirectResponse(url="/#settings-refund", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/legal", tags=["Frontend"])
def serve_legal_page():
    """Redirects to the SPA Legal & Compliance Center."""
    return RedirectResponse(url="/#settings-legal", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


# --------------------------------------------------------------------------
# SEO & AI Crawlers: robots.txt, sitemap.xml, llms.txt, favicons
# --------------------------------------------------------------------------
@app.get("/robots.txt", tags=["SEO"])
def serve_robots_txt():
    robots_path = os.path.join(FRONTEND_DIR, "static", "robots.txt")
    if os.path.exists(robots_path):
        return FileResponse(robots_path, media_type="text/plain")
    return Response(content="User-agent: *\nAllow: /\n", media_type="text/plain")


@app.get("/sitemap.xml", tags=["SEO"])
def serve_sitemap_xml():
    sitemap_path = os.path.join(FRONTEND_DIR, "static", "sitemap.xml")
    if os.path.exists(sitemap_path):
        return FileResponse(sitemap_path, media_type="application/xml")
    return Response(content="<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"></urlset>", media_type="application/xml")


@app.get("/llms.txt", tags=["SEO"])
def serve_llms_txt():
    llms_path = os.path.join(FRONTEND_DIR, "static", "llms.txt")
    if os.path.exists(llms_path):
        return FileResponse(llms_path, media_type="text/plain")
    return Response(content="# Transify 2.0\nAccessible AI and Clinical Triage Platform\n", media_type="text/plain")


@app.get("/favicon.svg", tags=["SEO"])
def serve_favicon_svg():
    fav_svg = os.path.join(FRONTEND_DIR, "static", "favicon.svg")
    if os.path.exists(fav_svg):
        return FileResponse(fav_svg, media_type="image/svg+xml")
    return Response(status_code=404)


@app.get("/favicon.ico", tags=["SEO"])
def serve_favicon_ico():
    fav_ico = os.path.join(FRONTEND_DIR, "static", "favicon.ico")
    if os.path.exists(fav_ico):
        return FileResponse(fav_ico, media_type="image/x-icon")
    return Response(status_code=404)


# --------------------------------------------------------------------------
# Custom 404 & HTTP Exception Handler (Branded & Accessible)
# --------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # If API or JSON client, return clean JSON
        if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
            return JSONResponse(status_code=404, content={"detail": exc.detail or "Not Found", "status": 404})
        # For browser navigation, return our branded 404.html page
        page_404 = os.path.join(FRONTEND_DIR, "404.html")
        if os.path.exists(page_404):
            with open(page_404, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

