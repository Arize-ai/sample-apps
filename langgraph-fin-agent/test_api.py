#!/usr/bin/env python3
"""
Test script for the LangGraph Finance Agent API.
"""

import requests
import sys


def test_api(base_url="http://localhost:8080"):
    """Test the API endpoints."""
    print(f"Testing API at: {base_url}")

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
        return False

    # Test status endpoint
    print("\n2. Testing status endpoint...")
    try:
        response = requests.get(f"{base_url}/api/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # Test chat endpoint
    print("\n3. Testing chat endpoint...")
    try:
        chat_request = {
            "message": "What is Apple's current stock symbol?",
            "session_id": "test-session-123",
        }
        response = requests.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json=chat_request,
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result['response'][:100]}...")
            print(f"Session ID: {result['session_id']}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test chat endpoint with environment overrides
    print("\n3a. Testing chat endpoint with environment overrides...")
    try:
        chat_request = {
            "message": "What is Tesla's stock symbol?",
            "session_id": "test-session-456",
            "env_overrides": {"ARIZE_MODEL_ID": "test-model"},
        }
        response = requests.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json=chat_request,
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result['response'][:100]}...")
            print(f"Session ID: {result['session_id']}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test finance query endpoint
    print("\n4. Testing finance query endpoint...")
    try:
        query_request = {
            "query": "What is the market cap of Tesla?",
            "thread_id": "test-thread-456",
        }
        response = requests.post(
            f"{base_url}/api/finance-query",
            headers={"Content-Type": "application/json"},
            json=query_request,
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Thread ID: {result['thread_id']}")
            print("Result structure received successfully")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test debug config endpoint
    print("\n5. Testing debug config endpoint...")
    try:
        response = requests.get(f"{base_url}/debug/config")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(
                f"Environment vars configured: {list(result.get('environment_vars', {}).keys())}"
            )
            print(f"Cache info: {result.get('cache_info', {})}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nAPI testing completed!")
    return True


if __name__ == "__main__":
    # Allow custom URL as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    test_api(base_url)
