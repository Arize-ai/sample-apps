#!/usr/bin/env python3
"""
Test script for the GuardRails server
"""
import requests
import json
import time
import sys
import os

# Server configuration
BASE_URL = "http://127.0.0.1:8000"

def test_server_health():
    """Test server health endpoint"""
    print("Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Root endpoint accessible")
            print(f"  Available guards: {data.get('available_guards', [])}")
            return True
        else:
            print(f"✗ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Root endpoint error: {e}")
        return False

def test_guards_list():
    """Test guards list endpoint"""
    print("\nTesting guards list endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/guards")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Guards list accessible")
            print(f"  Guards: {[g['name'] for g in data.get('guards', [])]}")
            return True
        else:
            print(f"✗ Guards list failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Guards list error: {e}")
        return False

def test_guard_endpoint(guard_name, test_message, expected_validation=None):
    """Test a specific guard endpoint"""
    print(f"\nTesting {guard_name} guard...")
    
    url = f"{BASE_URL}/guards/{guard_name}/openai/v1/chat/completions"
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": test_message
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            validation_passed = data.get('guardrails', {}).get('validation_passed')
            message_content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print(f"✓ {guard_name} guard responded")
            print(f"  Validation passed: {validation_passed}")
            print(f"  Response: {message_content[:100]}...")
            
            if expected_validation is not None:
                if validation_passed == expected_validation:
                    print(f"✓ Validation result matches expected: {expected_validation}")
                else:
                    print(f"✗ Validation result mismatch. Expected: {expected_validation}, Got: {validation_passed}")
            
            return True
        else:
            print(f"✗ {guard_name} guard failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ {guard_name} guard error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("GuardRails Server Test Suite")
    print("=" * 60)
    
    # Check if server is running
    if not test_server_health():
        print("\n❌ Server is not running or not accessible!")
        print("Please start the server first with: python run_server.py")
        sys.exit(1)
    
    # Test basic endpoints
    success_count = 0
    total_tests = 0
    
    total_tests += 1
    if test_root_endpoint():
        success_count += 1
        
    total_tests += 1
    if test_guards_list():
        success_count += 1
    
    # Test guard endpoints
    guard_tests = [
        ("gibberish_guard", "Explain machine learning in simple terms.", True),
        ("restrict_to_topic", "Explain the basics of stock market investing.", True),
        ("restrict_to_topic", "Give me a recipe for chocolate chip cookies.", False),
        ("dataset_embeddings_guard", "Explain data quality in machine learning.", None),
        ("pii_detection_guard", "Explain the importance of data privacy.", True),
        ("pii_detection_guard", "My email is john.doe@example.com", False),
    ]
    
    for guard_name, test_message, expected in guard_tests:
        total_tests += 1
        if test_guard_endpoint(guard_name, test_message, expected):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {success_count}/{total_tests} tests passed")
    print("=" * 60)
    
    if success_count == total_tests:
        print("🎉 All tests passed! The server is working correctly.")
    else:
        print(f"⚠️  {total_tests - success_count} tests failed. Please check the server configuration.")

if __name__ == "__main__":
    main() 