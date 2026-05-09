import asyncio
import google.generativeai as genai
from app.config import settings

SYSTEM_PROMPT = """You are Flaw AI, an advanced AI assistant created to be helpful, creative, and knowledgeable.
You provide clear, concise, and accurate responses. When asked about code, you provide well-structured examples.
You have a friendly yet professional personality. You use markdown formatting when appropriate.
Keep responses focused and avoid unnecessary verbosity."""


def _configure_genai():
    """Configure the Gemini API client."""
    genai.configure(api_key=settings.GEMINI_API_KEY)


async def get_gemini_response(messages: list) -> str:
    """Send conversation history to Gemini and return the response.

    Args:
        messages: List of Message ORM objects with .role and .content attributes.

    Returns:
        The AI-generated response text.
    """
    try:
        _configure_genai()

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )

        # Build Gemini-compatible history (exclude the last user message)
        history = []
        for msg in messages[:-1]:
            role_value = msg.role if isinstance(msg.role, str) else msg.role.value
            gemini_role = "user" if role_value == "user" else "model"
            history.append({"role": gemini_role, "parts": [msg.content]})

        chat = model.start_chat(history=history)

        # Send the latest message
        last_content = messages[-1].content if messages else "Hello"
        response = await asyncio.to_thread(chat.send_message, last_content)

        return response.text

    except Exception as e:
        return f"I encountered an error processing your request: {str(e)}"
