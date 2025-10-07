"""
Example demonstrating how to use flexible instrumentation for runtime configuration
"""

from src.llamaindex_app.flexible_instrumentation import (
    get_instrumentation_manager,
    TracerConfig,
    setup_flexible_instrumentation
)
import time
import os


def example_basic_usage():
    """Basic usage of flexible instrumentation"""
    print("=== Basic Usage Example ===")
    
    # Method 1: Using environment variables
    # Assuming ARIZE_SPACE_ID and ARIZE_API_KEY are set in environment
    tracer_provider = setup_flexible_instrumentation()
    tracer = tracer_provider.get_tracer("example_app")
    
    # Create a span
    with tracer.start_as_current_span("example_operation") as span:
        span.set_attribute("example.attribute", "value")
        print("Span created with environment configuration")
        time.sleep(0.1)


def example_runtime_configuration():
    """Example of runtime configuration"""
    print("\n=== Runtime Configuration Example ===")
    
    # Method 2: Explicit configuration
    config = TracerConfig(
        space_id="your_space_id",
        api_key="your_api_key",
        model_id="custom_model_v1",
        additional_attributes={
            "environment": "production",
            "version": "1.0.0"
        }
    )
    
    manager = get_instrumentation_manager()
    tracer_provider = manager.configure(config)
    tracer = tracer_provider.get_tracer("configured_app")
    
    # Use the tracer
    with tracer.start_as_current_span("configured_operation") as span:
        span.set_attribute("config.type", "explicit")
        print("Span created with explicit configuration")
        time.sleep(0.1)


def example_reconfiguration():
    """Example of reconfiguring instrumentation at runtime"""
    print("\n=== Reconfiguration Example ===")
    
    manager = get_instrumentation_manager()
    
    # Initial configuration
    config1 = TracerConfig(
        space_id="space_1",
        api_key="key_1",
        model_id="model_v1"
    )
    manager.configure(config1)
    tracer = manager.get_tracer("reconfig_app")
    
    # Use with first configuration
    with tracer.start_as_current_span("operation_config1") as span:
        span.set_attribute("configuration", "first")
        print("Using first configuration")
        time.sleep(0.1)
    
    # Reconfigure with different settings
    config2 = TracerConfig(
        space_id="space_2",
        api_key="key_2",
        model_id="model_v2",
        additional_attributes={
            "experiment": "A/B_test_variant_B"
        }
    )
    manager.reconfigure(config2)
    tracer = manager.get_tracer("reconfig_app")
    
    # Use with second configuration
    with tracer.start_as_current_span("operation_config2") as span:
        span.set_attribute("configuration", "second")
        print("Using second configuration")
        time.sleep(0.1)


def example_temporary_configuration():
    """Example of temporary configuration for specific operations"""
    print("\n=== Temporary Configuration Example ===")
    
    manager = get_instrumentation_manager()
    
    # Set up base configuration
    base_config = TracerConfig(
        space_id="production_space",
        api_key="production_key",
        model_id="production_model"
    )
    manager.configure(base_config)
    
    # Use base configuration
    tracer = manager.get_tracer("temp_config_app")
    with tracer.start_as_current_span("base_operation") as span:
        span.set_attribute("config", "base")
        print("Using base configuration")
    
    # Temporarily use different configuration
    temp_config = TracerConfig(
        space_id="debug_space",
        api_key="debug_key",
        model_id="debug_model",
        additional_attributes={
            "debug_mode": True,
            "log_level": "verbose"
        }
    )
    
    with manager.temporary_config(temp_config) as temp_provider:
        temp_tracer = temp_provider.get_tracer("temp_config_app")
        with temp_tracer.start_as_current_span("debug_operation") as span:
            span.set_attribute("config", "temporary")
            print("Using temporary debug configuration")
    
    print("Temporary configuration ended - need to reconfigure")
    
    # Reconfigure back to base
    manager.configure(base_config)
    tracer = manager.get_tracer("temp_config_app")
    with tracer.start_as_current_span("base_operation_again") as span:
        span.set_attribute("config", "base_restored")
        print("Back to base configuration")


def example_conditional_configuration():
    """Example of conditional configuration based on environment"""
    print("\n=== Conditional Configuration Example ===")
    
    manager = get_instrumentation_manager()
    
    # Determine configuration based on environment
    env = os.getenv("APP_ENV", "development")
    
    if env == "production":
        config = TracerConfig(
            space_id=os.getenv("PROD_ARIZE_SPACE_ID"),
            api_key=os.getenv("PROD_ARIZE_API_KEY"),
            model_id="production_model",
            additional_attributes={
                "environment": "production",
                "sampling_rate": 0.1  # Sample 10% in production
            }
        )
    elif env == "staging":
        config = TracerConfig(
            space_id=os.getenv("STAGING_ARIZE_SPACE_ID"),
            api_key=os.getenv("STAGING_ARIZE_API_KEY"),
            model_id="staging_model",
            additional_attributes={
                "environment": "staging",
                "sampling_rate": 0.5  # Sample 50% in staging
            }
        )
    else:
        config = TracerConfig(
            space_id=os.getenv("DEV_ARIZE_SPACE_ID", "dev_space"),
            api_key=os.getenv("DEV_ARIZE_API_KEY", "dev_key"),
            model_id="development_model",
            additional_attributes={
                "environment": "development",
                "sampling_rate": 1.0,  # Sample 100% in development
                "debug": True
            }
        )
    
    manager.configure(config)
    print(f"Configured for {env} environment")


def example_safe_usage():
    """Example of safe usage with error handling"""
    print("\n=== Safe Usage Example ===")
    
    manager = get_instrumentation_manager()
    
    # Check if already configured
    if not manager.is_configured():
        print("Instrumentation not configured, setting up...")
        try:
            config = TracerConfig.from_env()
            manager.configure(config)
        except ValueError as e:
            print(f"Failed to configure: {e}")
            print("Running without telemetry")
            return
    
    # Safe tracer usage
    tracer = manager.get_tracer("safe_app")
    if tracer:
        with tracer.start_as_current_span("safe_operation") as span:
            span.set_attribute("safety", "checked")
            print("Operation with telemetry")
    else:
        print("Running operation without telemetry")


def example_cleanup():
    """Example of proper cleanup"""
    print("\n=== Cleanup Example ===")
    
    manager = get_instrumentation_manager()
    
    try:
        # Configure and use
        config = TracerConfig(
            space_id="cleanup_space",
            api_key="cleanup_key",
            model_id="cleanup_model"
        )
        manager.configure(config)
        
        tracer = manager.get_tracer("cleanup_app")
        with tracer.start_as_current_span("operation") as span:
            span.set_attribute("cleanup", "pending")
            print("Performing operation")
        
    finally:
        # Always clean up
        manager.shutdown()
        print("Instrumentation shut down properly")


if __name__ == "__main__":
    # Note: These examples use dummy credentials for demonstration
    # In real usage, ensure proper credentials are set
    
    print("Flexible Instrumentation Examples\n")
    
    # Uncomment the examples you want to run:
    
    # example_basic_usage()
    # example_runtime_configuration()
    # example_reconfiguration()
    # example_temporary_configuration()
    # example_conditional_configuration()
    # example_safe_usage()
    # example_cleanup()
    
    print("\nNote: Set proper ARIZE_SPACE_ID and ARIZE_API_KEY to run these examples") 