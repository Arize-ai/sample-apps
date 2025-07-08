# Migration Guide: Flexible OpenTelemetry Instrumentation

This guide helps you migrate from the global OpenTelemetry instrumentation to the new flexible instrumentation system that allows runtime configuration.

## Why Migrate?

The old instrumentation approach uses `set_tracer_provider()` which sets the tracer globally. This has several limitations:
- Cannot reconfigure at runtime
- Difficult to use different configurations for different environments
- Global state makes testing harder
- Cannot temporarily change configuration

The new flexible instrumentation solves these issues by:
- Allowing runtime reconfiguration
- Supporting environment-specific configurations
- Enabling temporary configuration changes
- Avoiding global state

## Migration Steps

### 1. Update Imports

**Old:**
```python
from src.llamaindex_app.instrumentation import setup_instrumentation
```

**New:**
```python
from src.llamaindex_app.flexible_instrumentation import (
    get_instrumentation_manager,
    TracerConfig,
    setup_flexible_instrumentation
)
```

### 2. Basic Setup (Drop-in Replacement)

**Old:**
```python
tracer_provider = setup_instrumentation()
tracer = tracer_provider.get_tracer("llamaindex_app")
```

**New (Simple):**
```python
# Drop-in replacement - uses environment variables
tracer_provider = setup_flexible_instrumentation()
tracer = tracer_provider.get_tracer("llamaindex_app")
```

### 3. Runtime Configuration

**New (Advanced):**
```python
# Configure with explicit values
config = TracerConfig(
    space_id="your_space_id",
    api_key="your_api_key",
    model_id="custom_model",
    additional_attributes={
        "environment": "production",
        "version": "1.0.0"
    }
)

manager = get_instrumentation_manager()
tracer_provider = manager.configure(config)
tracer = tracer_provider.get_tracer("llamaindex_app")
```

### 4. Reconfiguration

```python
# Initial configuration
config1 = TracerConfig(space_id="space1", api_key="key1", model_id="model1")
manager = get_instrumentation_manager()
manager.configure(config1)

# Later, reconfigure with different settings
config2 = TracerConfig(space_id="space2", api_key="key2", model_id="model2")
manager.reconfigure(config2)
```

### 5. Environment-Based Configuration

```python
def get_environment_config():
    env = os.getenv("APP_ENV", "development")
    
    if env == "production":
        return TracerConfig(
            space_id=os.getenv("PROD_ARIZE_SPACE_ID"),
            api_key=os.getenv("PROD_ARIZE_API_KEY"),
            model_id="production_model"
        )
    else:
        return TracerConfig(
            space_id=os.getenv("DEV_ARIZE_SPACE_ID"),
            api_key=os.getenv("DEV_ARIZE_API_KEY"),
            model_id="development_model"
        )

config = get_environment_config()
manager = get_instrumentation_manager()
tracer_provider = manager.configure(config)
```

### 6. Temporary Configuration

```python
manager = get_instrumentation_manager()

# Use temporary configuration for debugging
debug_config = TracerConfig(
    space_id="debug_space",
    api_key="debug_key",
    model_id="debug_model",
    additional_attributes={"debug": True}
)

with manager.temporary_config(debug_config):
    # This code runs with debug configuration
    tracer = manager.get_tracer("app")
    with tracer.start_as_current_span("debug_operation"):
        # Debug operation
        pass
# Configuration automatically reverts after the context
```

### 7. Safe Usage Pattern

```python
def get_tracer_safely():
    manager = get_instrumentation_manager()
    
    # Check if configured
    if not manager.is_configured():
        try:
            config = TracerConfig.from_env()
            manager.configure(config)
        except ValueError as e:
            logger.warning(f"Failed to configure instrumentation: {e}")
            return None
    
    return manager.get_tracer("app")

# Use the tracer safely
tracer = get_tracer_safely()
if tracer:
    with tracer.start_as_current_span("operation"):
        # Operation with telemetry
        pass
else:
    # Operation without telemetry
    pass
```

## API Changes

### Functions

| Old Function | New Function | Notes |
|-------------|--------------|-------|
| `setup_instrumentation()` | `setup_flexible_instrumentation()` | Drop-in replacement |
| N/A | `get_instrumentation_manager()` | Access to manager instance |

### Classes

| New Class | Purpose |
|-----------|---------|
| `TracerConfig` | Configuration dataclass |
| `FlexibleInstrumentation` | Manager class (accessed via `get_instrumentation_manager()`) |

### Methods

| Method | Description |
|--------|-------------|
| `manager.configure(config)` | Configure instrumentation |
| `manager.reconfigure(config)` | Reconfigure (shutdown + configure) |
| `manager.get_tracer(name)` | Get a tracer instance |
| `manager.is_configured()` | Check if configured |
| `manager.shutdown()` | Clean shutdown |
| `manager.temporary_config(config)` | Context manager for temporary config |

## Common Patterns

### 1. FastAPI Integration

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = TracerConfig.from_env()
    manager = get_instrumentation_manager()
    manager.configure(config)
    yield
    # Shutdown
    manager.shutdown()

app = FastAPI(lifespan=lifespan)
```

### 2. Dynamic Configuration API

```python
@app.post("/admin/reconfigure-telemetry")
async def reconfigure_telemetry(
    space_id: str,
    api_key: str,
    model_id: str = "default"
):
    config = TracerConfig(
        space_id=space_id,
        api_key=api_key,
        model_id=model_id
    )
    manager = get_instrumentation_manager()
    manager.reconfigure(config)
    return {"status": "reconfigured"}
```

### 3. Testing

```python
def test_with_telemetry():
    test_config = TracerConfig(
        space_id="test_space",
        api_key="test_key",
        model_id="test_model"
    )
    
    manager = get_instrumentation_manager()
    with manager.temporary_config(test_config):
        # Run tests with test configuration
        pass
```

## Troubleshooting

### Issue: PERMISSION_DENIED error
If you see `StatusCode.PERMISSION_DENIED` when exporting traces:

1. **Use environment variable headers** (recommended):
   ```python
   config = TracerConfig(
       space_id="your_space_id",
       api_key="your_api_key",
       model_id="your_model",
       use_env_headers=True  # This uses the original authentication method
   )
   ```

2. **Run the authentication test script**:
   ```bash
   python fix_instrumentation_auth.py
   ```
   This will test both authentication methods and recommend which one works.

3. **Verify your credentials**:
   - Check that `ARIZE_SPACE_ID` and `ARIZE_API_KEY` are correct
   - Ensure there are no extra spaces or quotes in the values

### Issue: Instrumentation not sending data
- Check if `manager.is_configured()` returns `True`
- Verify credentials are correct
- Check logs for configuration errors
- Look for authentication errors in the logs

### Issue: Old configuration persists
- Call `manager.shutdown()` before reconfiguring
- Use `manager.reconfigure()` instead of `configure()`

### Issue: Memory leaks
- Always call `manager.shutdown()` on application shutdown
- Use context managers for temporary configurations

## Benefits

1. **Flexibility**: Change configuration without restarting
2. **Testing**: Easy to mock or use test configurations
3. **Multi-tenancy**: Different configurations per request/user
4. **Debugging**: Temporary verbose configurations
5. **Environment Management**: Easy environment-specific configs
6. **No Global State**: Better for containerized applications 