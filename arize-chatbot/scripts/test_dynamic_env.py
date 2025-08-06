#!/usr/bin/env python3
"""
Test script for dynamic environment variables in Arize Chatbot.

Usage:
    python test_dynamic_env.py --url YOUR_CLOUD_RUN_URL
"""

import argparse
import requests
import json
from typing import Dict, Optional


def send_chat_request(
    url: str,
    message: str,
    env_overrides: Optional[Dict[str, str]] = None,
    session_id: Optional[str] = None,
) -> Dict:
    """Send a chat request with optional environment overrides."""

    endpoint = f"{url}/api/chat"

    payload = {"message": message, "session_id": session_id}

    if env_overrides:
        payload["env_overrides"] = env_overrides

    print(f"\nSending request to: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Test dynamic environment variables")
    parser.add_argument(
        "--url",
        required=True,
        help="Cloud Run URL (e.g., https://your-service-abc123-uc.a.run.app)",
    )
    parser.add_argument("--message", default="What is Arize?", help="Message to send")

    # Optional environment overrides
    parser.add_argument("--arize-space-id", help="Override ARIZE_SPACE_ID")
    parser.add_argument("--arize-model-id", help="Override ARIZE_MODEL_ID")
    parser.add_argument("--arize-api-key", help="Override ARIZE_API_KEY")
    parser.add_argument("--openai-api-key", help="Override OPENAI_API_KEY")

    args = parser.parse_args()

    # Build environment overrides if provided
    env_overrides = {}
    if args.arize_space_id:
        env_overrides["ARIZE_SPACE_ID"] = args.arize_space_id
    if args.arize_model_id:
        env_overrides["ARIZE_MODEL_ID"] = args.arize_model_id
    if args.arize_api_key:
        env_overrides["ARIZE_API_KEY"] = args.arize_api_key
    if args.openai_api_key:
        env_overrides["OPENAI_API_KEY"] = args.openai_api_key

    print("=" * 50)
    print("Testing Arize Chatbot with Dynamic Environment Variables")
    print("=" * 50)

    # Test 1: Request with default environment (no overrides)
    print("\n1. Testing with default environment (no overrides)...")
    try:
        result = send_chat_request(args.url, args.message)
        print(f"\nResponse: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Failed: {e}")

    # Test 2: Request with environment overrides (if provided)
    if env_overrides:
        print("\n2. Testing with environment overrides...")
        try:
            result = send_chat_request(args.url, args.message, env_overrides)
            print(f"\nResponse: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Failed: {e}")

        # Test 3: Second request with same overrides (should use cache)
        print("\n3. Testing cache hit (same overrides)...")
        try:
            result = send_chat_request(
                args.url, "How do I set up monitoring?", env_overrides
            )
            print(f"\nResponse: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Failed: {e}")

    # Test health endpoint
    print("\n4. Testing health endpoint...")
    try:
        health_response = requests.get(f"{args.url}/health")
        health_response.raise_for_status()
        print(f"Health check: {health_response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    main()
