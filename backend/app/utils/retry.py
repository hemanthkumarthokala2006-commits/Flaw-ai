import asyncio
import logging

logger = logging.getLogger(__name__)

async def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
    
    Returns:
        Result of the function
    
    Raises:
        Exception: If all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries + 1} attempts failed.")
    
    raise last_exception


def create_error_response(error: str, code: str = "unknown"):
    """Create a standardized error response."""
    return {
        "status": "error",
        "message": error,
        "code": code,
    }


def create_success_response(data: any):
    """Create a standardized success response."""
    return {
        "status": "success",
        "data": data,
    }
