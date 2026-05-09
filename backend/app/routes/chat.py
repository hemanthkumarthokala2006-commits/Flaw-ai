from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
import aiofiles
from app.config import settings
from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.chat import Conversation, Message, MessageRole, MessageType
from app.services.gemini import get_gemini_response

router = APIRouter(prefix="/api/chats", tags=["Chat"])


# --- Schemas ---

class ConversationResponse(BaseModel):
    id: int
    title: str
    model_used: str
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    message_type: str
    media_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    content: str
    message_type: str = "text"


class CreateChatRequest(BaseModel):
    title: str = "New Chat"


# --- Endpoints ---

@router.get("", response_model=list[ConversationResponse])
async def list_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user, newest first."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
    )
    return [ConversationResponse.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_chat(
    request: CreateChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=current_user.id,
        title=request.title,
        model_used=current_user.preferred_llm or "gemini",
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return ConversationResponse.model_validate(conversation)


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.delete(conversation)


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == chat_id)
        .order_by(Message.created_at)
    )
    return [MessageResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get an AI response."""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save user message
    user_message = Message(
        conversation_id=chat_id,
        role=MessageRole.user,
        content=request.content,
        message_type=MessageType(request.message_type),
    )
    db.add(user_message)
    await db.flush()

    # Fetch full history for AI context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == chat_id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()

    # Get AI response
    ai_content = await get_gemini_response(list(history))

    # Save assistant message
    assistant_message = Message(
        conversation_id=chat_id,
        role=MessageRole.assistant,
        content=ai_content,
        message_type=MessageType.text,
    )
    db.add(assistant_message)
    await db.flush()
    await db.refresh(assistant_message)

    # Auto-title on first message
    if len(history) <= 1:
        title = request.content[:50] + ("..." if len(request.content) > 50 else "")
        conversation.title = title
        await db.flush()

    return MessageResponse.model_validate(assistant_message)


@router.post("/{chat_id}/upload", response_model=MessageResponse)
async def upload_media(
    chat_id: int,
    message_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an attachment, image, or voice note and save it as a chat message."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")

    file_id = uuid.uuid4().hex
    filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    media_url = f"{settings.BACKEND_URL}/uploads/{filename}"
    message = Message(
        conversation_id=chat_id,
        role=MessageRole.user,
        content=file.filename,
        message_type=MessageType(message_type),
        media_url=media_url,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    return MessageResponse.model_validate(message)
