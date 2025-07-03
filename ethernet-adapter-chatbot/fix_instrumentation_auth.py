"""
Quick fix for OpenTelemetry authentication issues with Arize.
This script tries different authentication methods to find what works.
"""

import os
import sys
import time
from src.llamaindex_app.flexible_instrumentation import (
    get_instrumentation_manager,
    TracerConfig,
)


def test_auth_method(method_name: str, config: TracerConfig):
    """Test an authentication method"""
    print(f"\nTesting {method_name}...")
    
    manager = get_instrumentation_manager()
    manager.shutdown()  # Clean up any previous config
    
    try:
        tracer_provider = manager.configure(config)
        tracer = tracer_provider.get_tracer("auth_test")
        
        # Create a test span
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.method", method_name)
            span.set_attribute("test.timestamp", time.time())
            print(f"  ✓ Span created successfully")
        
        # Give it a moment to export
        print(f"  Waiting for export...")
        time.sleep(2)
        
        print(f"  ✓ {method_name} completed - check Arize dashboard for traces")
        return True
        
    except Exception as e:
        print(f"  ✗ {method_name} failed: {e}")
        return False
    finally:
        manager.shutdown()


def main():
    """Test different authentication methods"""
    
    # Get credentials from environment
    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")
    model_id = os.getenv("ARIZE_MODEL_ID", "test_auth_model")
    
    if not space_id or not api_key:
        print("ERROR: ARIZE_SPACE_ID and ARIZE_API_KEY must be set")
        sys.exit(1)
    
    print("Testing OpenTelemetry Authentication Methods")
    print("=" * 50)
    print(f"Space ID: {space_id[:10]}...")
    print(f"API Key: {api_key[:10]}...")
    print(f"Model ID: {model_id}")
    print(f"Endpoint: https://otlp.arize.com/v1")
    
    # Method 1: Environment variable headers (like original)
    config1 = TracerConfig(
        space_id=space_id,
        api_key=api_key,
        model_id=model_id,
        use_env_headers=True  # Use environment variable approach
    )
    success1 = test_auth_method("Environment Variable Headers", config1)
    
    # Method 2: Direct headers (new approach)
    config2 = TracerConfig(
        space_id=space_id,
        api_key=api_key,
        model_id=model_id,
        use_env_headers=False  # Pass headers directly
    )
    success2 = test_auth_method("Direct Headers", config2)
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Environment Variable Headers: {'✓ Success' if success1 else '✗ Failed'}")
    print(f"  Direct Headers: {'✓ Success' if success2 else '✗ Failed'}")
    
    if success1 and not success2:
        print("\nRecommendation: Use environment variable headers")
        print("Set use_env_headers=True in your TracerConfig")
    elif success2 and not success1:
        print("\nRecommendation: Use direct headers")
        print("Set use_env_headers=False in your TracerConfig (default)")
    elif success1 and success2:
        print("\nBoth methods work! Use either approach.")
    else:
        print("\nBoth methods failed. Please check:")
        print("1. Your ARIZE_SPACE_ID and ARIZE_API_KEY are correct")
        print("2. Your network can reach https://otlp.arize.com/v1")
        print("3. Check the error messages above for more details")


if __name__ == "__main__":
    main() 