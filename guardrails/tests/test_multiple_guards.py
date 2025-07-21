import os

# Completely disable OpenTelemetry to avoid connection errors
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['OTEL_METRICS_EXPORTER'] = 'none'
os.environ['OTEL_TRACES_EXPORTER'] = 'none'
os.environ['OTEL_LOGS_EXPORTER'] = 'none'

from openai import OpenAI
import time

def test_topic_guard():
    """Test the restrict to topic guard"""
    print("=" * 50)
    print("Testing Restrict to Topic Guard")
    print("=" * 50)
    
    client = OpenAI(
        base_url='https://guardrails-533097539904.us-central1.run.app/guards/restrict_to_topic/openai/v1',
        # Will use OPENAI_API_KEY environment variable
    )
    
    # Test 1: Valid topic (should pass)
    print("\n1. Testing valid topic (finance):")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Explain the basics of stock market investing and portfolio management."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Invalid topic (should fail)
    print("\n2. Testing invalid topic (cooking):")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Give me a recipe for chocolate chip cookies."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"Off-topic detected - Exception: {e}")

def test_dataset_embeddings_guard():
    """Test the dataset embeddings guard"""
    print("=" * 50)
    print("Testing Dataset Embeddings Guard")
    print("=" * 50)
    
    client = OpenAI(
        base_url='https://guardrails-533097539904.us-central1.run.app/guards/dataset_embeddings_guard/openai/v1',
        # Will use OPENAI_API_KEY environment variable
    )
    
    # Test 1: Standard request
    print("\n1. Testing standard request:")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Explain the concept of data quality in machine learning."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Another request
    print("\n2. Testing another request:")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "What are the best practices for data preprocessing?"
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"Dataset embeddings validation failed - Exception: {e}")

def test_pii_detection_guard():
    """Test the PII detection guard"""
    print("=" * 50)
    print("Testing PII Detection Guard")
    print("=" * 50)
    
    client = OpenAI(
        base_url='https://guardrails-533097539904.us-central1.run.app/guards/pii_detection_guard/openai/v1',
        # Will use OPENAI_API_KEY environment variable
    )
    
    # Test 1: Safe request without PII (should pass)
    print("\n1. Testing safe request without PII:")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "Explain the importance of data privacy in machine learning applications."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Request containing PII (should fail)
    print("\n2. Testing request with PII (email address):")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "My email address is john.doe@example.com and I need help with my account."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"PII detected - Exception: {e}")
    
    # Test 3: Request with phone number (should fail)
    print("\n3. Testing request with PII (phone number):")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "You can reach me at 555-123-4567 for any questions."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"PII detected - Exception: {e}")
    
    # Test 4: Request with credit card number (should fail)
    print("\n4. Testing request with PII (credit card number):")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "My credit card number is 4532-1234-5678-9012 and it's not working."
            }]
        )
        print(f"Response: {response.choices[0].message.content}")
        print(f"Validation passed: {response.guardrails['validation_passed']}")
    except Exception as e:
        print(f"PII detected - Exception: {e}")

def main():
    print("Testing Multiple GuardRails Guards")
    print("Make sure the server is accessible at: https://guardrails-533097539904.us-central1.run.app")
    print("\nWaiting 2 seconds for connection to be ready...")
    time.sleep(2)
    
    # Test the three remaining guards
    test_topic_guard()
    test_dataset_embeddings_guard()
    test_pii_detection_guard()
    
    print("\n" + "=" * 50)
    print("Testing Complete!")
    print("=" * 50)

if __name__ == "__main__":
    main() 