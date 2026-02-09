"""Chat API routes.

Endpoints for AI assistant chat functionality with streaming support.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str
    history: list[ChatMessage] = []


@router.post("")
async def chat(request: ChatRequest):
    """
    Chat with the AI assistant.
    
    Returns a streaming response with Server-Sent Events.
    """
    from app.application.services.chat_service import get_chat_service
    
    try:
        chat_service = get_chat_service()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Convert history to dict format
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]
    
    async def generate():
        """Generate SSE stream."""
        try:
            async for chunk in chat_service.chat_stream(request.message, history):
                # SSE format: data: <content>\n\n
                yield f"data: {chunk}\n\n"
            # Signal end of stream
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
