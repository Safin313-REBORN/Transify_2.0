"""
FastAPI Router for Transify AI Chatbot & Knowledge Training Hub.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.chatbot.ai_chatbot import ai_chatbot_engine

router = APIRouter(prefix="/api/chat", tags=["AI Chatbot"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User prompt or health inquiry")
    history: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages in conversation")
    language: Optional[str] = Field("en", description="Language preference (en or bn)")


class ChatMessageResponse(BaseModel):
    response: str
    domain: str
    confidence: float
    source: str
    citations: List[str]
    suggested_replies: List[str]
    is_emergency: bool = False


class CustomTrainingSample(BaseModel):
    id: str
    domain: str
    keywords: List[str]
    patterns: List[str]
    response: str
    citations: Optional[List[str]] = None
    suggested_replies: Optional[List[str]] = None


class ChatTrainRequest(BaseModel):
    epochs: Optional[int] = Field(10, ge=1, le=100, description="Training epochs (iterations)")
    learning_rate: Optional[float] = Field(0.02, ge=0.001, le=0.5, description="Gradient step size")
    custom_samples: Optional[List[Dict[str, Any]]] = Field(None, description="New Q&A patterns to train on")


@router.post("/message", response_model=ChatMessageResponse)
def send_chat_message(req: ChatMessageRequest):
    """
    Evaluates user prompt using trained clinical & assistive RAG model.
    Checks for red-flag emergencies, retrieves guideline citations, and formats responses.
    """
    try:
        res = ai_chatbot_engine.respond(req.message, req.history)
        return res
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Chatbot reasoning failure: {str(ex)}")


@router.get("/status")
def get_chatbot_status():
    """
    Returns deployment status, active model version, accuracy, and training diagnostics.
    """
    return ai_chatbot_engine.get_status()


@router.post("/train")
def train_chatbot_model(req: ChatTrainRequest):
    """
    Interactive training endpoint: trains / fine-tunes the AI model across specified epochs,
    incorporates any custom samples, computes loss curves, and persists updated model weights.
    """
    try:
        train_res = ai_chatbot_engine.train_model(
            epochs=req.epochs or 10,
            learning_rate=req.learning_rate or 0.02,
            custom_samples=req.custom_samples
        )
        return train_res
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Model training failure: {str(ex)}")


@router.post("/reset")
def reset_chat_conversation():
    """Resets dialog buffer and session context."""
    return {"success": True, "message": "Conversation session reset."}
