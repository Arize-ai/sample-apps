import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from openai import OpenAI
import time

# Import the guards from config
from config import topic_guard, embeddings_guard, pii_guard

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GuardRails Server",
    description="A server that provides guardrails validation for LLM responses",
    version="1.0.0",
)

# OpenAI client for upstream requests
openai_client = OpenAI()

# Guard registry
GUARDS = {
    "restrict_to_topic": topic_guard,
    "dataset_embeddings_guard": embeddings_guard,
    "pii_detection_guard": pii_guard,
}


# Pydantic models for OpenAI API compatibility
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int]
    guardrails: Dict[str, Any]


@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "GuardRails Server",
        "version": "1.0.0",
        "available_guards": list(GUARDS.keys()),
        "endpoints": [
            f"/guards/{guard_name}/openai/v1/chat/completions"
            for guard_name in GUARDS.keys()
        ],
    }


@app.get("/guards")
async def list_guards():
    """List all available guards"""
    return {
        "guards": [
            {"name": name, "endpoint": f"/guards/{name}/openai/v1/chat/completions"}
            for name in GUARDS.keys()
        ]
    }


@app.post("/guards/{guard_name}/openai/v1/chat/completions")
async def chat_completions(guard_name: str, request: ChatCompletionRequest):
    """
    Handle chat completions with guardrails validation
    """
    if guard_name not in GUARDS:
        raise HTTPException(
            status_code=404,
            detail=f"Guard '{guard_name}' not found. Available guards: {list(GUARDS.keys())}",
        )

    selected_guard = GUARDS[guard_name]

    try:
        # Convert messages to OpenAI format
        messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # Make request to OpenAI
        logger.info(f"Making OpenAI request with guard: {guard_name}")

        openai_response = openai_client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop,
        )

        # Extract the content from OpenAI response
        response_content = openai_response.choices[0].message.content

        # Apply guardrails validation
        logger.info(f"Applying guardrails validation with guard: {guard_name}")

        # Check if we need to validate input (for PII detection)
        if guard_name == "pii_detection_guard":
            # For PII detection, validate the input messages
            input_text = " ".join([msg.content for msg in request.messages])
            try:
                selected_guard.validate(input_text)
                validation_passed = True
                validation_error = None
            except Exception as e:
                validation_passed = False
                validation_error = str(e)
                # Return failure message instead of the original response
                response_content = "Sorry, I can't help with that."
        else:
            # For other guards, validate the output
            try:
                selected_guard.validate(response_content)
                validation_passed = True
                validation_error = None
            except Exception as e:
                validation_passed = False
                validation_error = str(e)
                # Return failure message instead of the original response
                response_content = "Sorry, I can't help with that."

        # Create response in OpenAI format
        response = ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop",
                )
            ],
            usage={
                "prompt_tokens": openai_response.usage.prompt_tokens,
                "completion_tokens": openai_response.usage.completion_tokens,
                "total_tokens": openai_response.usage.total_tokens,
            },
            guardrails={
                "guard_name": guard_name,
                "validation_passed": validation_passed,
                "validation_error": validation_error,
            },
        )

        return response

    except Exception as e:
        logger.error(f"Error processing request with guard {guard_name}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500, content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    logger.info(f"Starting GuardRails server on {host}:{port}")
    logger.info(f"Available guards: {list(GUARDS.keys())}")

    uvicorn.run(app, host=host, port=port, log_level="info")
