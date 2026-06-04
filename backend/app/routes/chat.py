from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
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
from app.services.gemini import get_gemini_response, get_gemini_streaming_response, generate_conversation_summary, SYSTEM_PROMPT

router = APIRouter(prefix="/api/chats", tags=["Chat"])


# --- Schemas ---

class ConversationResponse(BaseModel):
    id: int
    title: str
    model_used: str
    system_prompt: str | None = None
    summary: str | None = None
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
    edited_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EditMessageRequest(BaseModel):
    content: str


class SendMessageRequest(BaseModel):
    content: str
    message_type: str = "text"
    media_url: str | None = None


class CreateChatRequest(BaseModel):
    title: str = "New Chat"
    system_prompt: str | None = None


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
        system_prompt=request.system_prompt,
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
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages in a conversation with pagination."""
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
        .limit(limit)
        .offset(offset)
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
        media_url=request.media_url,
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
    image_path = None
    if request.media_url:
        # Map URL back to local path
        filename = request.media_url.split("/")[-1]
        image_path = os.path.join(settings.UPLOAD_DIR, filename)
    elif len(history) > 1:
        # Check if previous message was an image to provide context
        prev_msg = history[-2]
        if prev_msg.message_type == MessageType.image and prev_msg.media_url:
            filename = prev_msg.media_url.split("/")[-1]
            image_path = os.path.join(settings.UPLOAD_DIR, filename)

    ai_content = await get_gemini_response(list(history), image_path=image_path, system_prompt=conversation.system_prompt or SYSTEM_PROMPT)

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

    # Generate summary after first exchange if not set
    if conversation.summary is None and len(history) >= 2:
        all_messages = history + [user_message, assistant_message]
        summary = await generate_conversation_summary(all_messages)
        conversation.summary = summary
        await db.flush()

    return MessageResponse.model_validate(assistant_message)


@router.post("/{chat_id}/stream")
async def stream_message(
    chat_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get a streaming AI response."""
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
        media_url=request.media_url,
    )
    db.add(user_message)
    await db.flush()

    # Fetch history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == chat_id)
        .order_by(Message.created_at)
    )
    history = list(result.scalars().all())

    # Auto-title on first message
    if len(history) <= 1:
        title = request.content[:50] + ("..." if len(request.content) > 50 else "")
        conversation.title = title
        await db.flush()

    image_path = None
    if request.media_url:
        filename = request.media_url.split("/")[-1]
        image_path = os.path.join(settings.UPLOAD_DIR, filename)

    async def event_generator():
        full_response = ""
        async for chunk in get_gemini_streaming_response(history, image_path=image_path, system_prompt=conversation.system_prompt or SYSTEM_PROMPT):
            full_response += chunk
            yield chunk

        # Save assistant message at the end
        assistant_message = Message(
            conversation_id=chat_id,
            role=MessageRole.assistant,
            content=full_response,
            message_type=MessageType.text,
        )
        # Note: In a real streaming scenario with SQLAlchemy, 
        # we'd need a separate session or careful management because the generator 
        # outlives the route's DB session scope if not careful.
        # For now, we'll try to save it in the background or use a new session.
        from app.utils.database import SessionLocal
        async with SessionLocal() as background_db:
            background_db.add(assistant_message)
            await background_db.commit()

    return StreamingResponse(event_generator(), media_type="text/plain")


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


@router.get("/{chat_id}/export")
async def export_conversation(
    chat_id: int,
    format: str = "json",  # json or markdown
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export conversation in JSON or Markdown format."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == chat_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    if format == "markdown":
        md = f"# {conversation.title}\n\n"
        for msg in messages:
            role = "User" if msg.role.value == "user" else "Assistant"
            md += f"**{role}**: {msg.content}\n\n"
        return {"content": md, "filename": f"{conversation.title}.md"}
    else:
        data = {
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "edited_at": msg.edited_at.isoformat() if msg.edited_at else None,
                }
                for msg in messages
            ]
        }
        return data


@router.put("/{chat_id}/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    chat_id: int,
    message_id: int,
    request: EditMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit a message content."""
    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.conversation_id == chat_id,
            Message.role == MessageRole.user  # Only allow editing user messages
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found or not editable")

    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == chat_id, Conversation.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat not found")

    message.content = request.content
    message.edited_at = datetime.utcnow()
    await db.flush()
    await db.refresh(message)
    return MessageResponse.model_validate(message)
