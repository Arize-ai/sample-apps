# Arize AX Tracing for Pipecat Voice Agent

This pipecat voice agent now features **comprehensive session-based tracing** with proper async context propagation that sends all telemetry data to Arize AX for advanced observability and monitoring.

## 🚀 Setup Instructions

### 1. Install Dependencies

Install the updated requirements with Arize AX tracing support:

```bash
pip install -r requirements.txt
```

### 2. Configure Arize AX Credentials

You'll need to set up your Arize AX credentials. Copy `env.example` to `.env` and fill in your Arize credentials:

```bash
cp env.example .env
```

Update your `.env` file with your Arize AX credentials:

```bash
# Arize AX Tracing Configuration
ARIZE_SPACE_ID=your_actual_arize_space_id
ARIZE_API_KEY=your_actual_arize_api_key
ARIZE_PROJECT_NAME=pipecat-voice-agent

# Development Mode (enables immediate trace flushing and console logging)
DEVELOPMENT=true
```

### 3. Run the Voice Agent

#### Local Development:
```bash
LOCAL_RUN=true python bot.py
```

#### Production:
```bash
DAILY_ROOM_URL=your_room_url python bot.py
```

## 🏗️ **New Session-Based Tracing Architecture**

### **Unified Trace Tree**
The bot now creates a **main session span** that encompasses the entire voice agent lifecycle. All operations are properly connected as children of this main span, solving previous span propagation issues.

```
🌟 Main Session Span (pipecat_session_local_development)
├── 📱 Daily Room Configuration
├── 🚀 Transport Initialization
└── 🔄 Voice Pipeline Main
    ├── 🔊 TTS Service Init
    ├── 🧠 LLM Service Init  
    ├── 💭 Context Aggregator Init
    ├── ⚙️ Pipeline Creation
    └── ▶️ Pipeline Execution
        ├── 👤 Participant Joined Processing
        ├── 💬 LLM Interactions (auto-instrumented)
        ├── 🔊 Audio Processing Events
        └── 🚪 Participant Left Processing
```

### **Async Context Propagation**
Every async function now properly inherits the parent span context using:

- **`@with_context_propagation`** decorator for async functions
- **`create_child_span_with_context()`** for manual span creation
- **Automatic context capture and attachment** across async boundaries

### **Session Management**
```python
# Session-based tracing with proper lifecycle management
with SessionTracer(session_id, "local_development") as session:
    # All operations inherit this session context
    await main(transport)
    # Session automatically closed and flushed
```

## 📊 **What Gets Traced**

**Following OpenInference conventions for GenAI use cases**, this implementation uses only two span kinds:

### 🔗 **CHAIN Spans** (General Operations)
- **Session Management**: Session lifecycle, metadata, participant events
- **Pipeline Operations**: Service initialization, component assembly, execution 
- **Transport & Daily.co**: Room configuration, transport setup
- **Audio Processing**: TTS operations, voice activity, audio configuration
- **Event Handling**: Participant join/leave events, error handling

### 🔗 **CHAIN Spans** (All Operations including LLM Setup)
- **LLM Service Setup**: OpenAI LLM service initialization (now CHAIN)
- **Model Calls**: All OpenAI API calls remain auto-instrumented with proper span kinds
- **Input/Output**: Using OpenInference semantic conventions (INPUT_VALUE, OUTPUT_VALUE)
- **Token Usage**: Using OpenInference LLM attributes (LLM_TOKEN_COUNT_*)
- **Latency**: Response times and processing duration

### **Session-Level Metadata**
- **Session ID**: Unique identifier for each voice session
- **Environment**: local_development / production / pipecat_cloud
- **Agent Version**: 1.0.0
- **Transport Type**: daily
- **Room URL**: Daily.co room URL
- **Bot Configuration**: VAD, transcription settings

### **Error Handling**
- **Exception Recording**: Full stack traces captured
- **Error Context**: Session and operation context preserved
- **Status Tracking**: Success/failure states for all operations

## 🎯 **OpenInference Span Kind Strategy**

This implementation follows **pure OpenInference conventions for GenAI use cases**:

- **`CHAIN`**: ALL manual operations (pipeline, transport, audio, session management, LLM service setup)
- **Auto-instrumented spans**: Keep their appropriate kinds (ChatCompletion=LLM, TTS=proper GenAI attributes)

### **Why This Approach?**

1. **Pure OpenInference**: Uses only OpenInference semantic conventions, no OTEL-specific attributes
2. **Arize-Optimized**: Follows Arize guidance for GenAI applications  
3. **Simplified Manual Spans**: All manual spans use CHAIN, letting auto-instrumentation handle specialized kinds
4. **Trace Hierarchy**: Maintains proper parent-child relationships across async operations
5. **Consistent Attributes**: All custom attributes use SpanAttributes.METADATA for proper categorization

### **Span Kind Usage Examples**

```python
# ✅ Correct: ALL manual operations use CHAIN (following Arize guidance)
create_child_span_with_context("tts_service_init", "CHAIN")
create_child_span_with_context("pipeline_creation", "CHAIN") 
create_child_span_with_context("transport_init", "CHAIN")
create_child_span_with_context("llm_service_init", "CHAIN")  # Now CHAIN!

# ✅ Auto-instrumented spans keep their proper kinds:
# - ChatCompletion spans remain "LLM" (auto-instrumented by OpenAI)
# - TTS spans use proper GenAI attributes (auto-instrumented by Pipecat)

# ❌ Avoid: Manual spans with specialized kinds
# create_child_span_with_context("some_operation", "LLM")      # Only for auto-instrumentation
# create_child_span_with_context("some_operation", "TOOL")     # Don't use manually  
# create_child_span_with_context("some_operation", "RETRIEVER") # Don't use manually
```

## 🔧 **Advanced Features**

### **Development Mode Benefits**
When `DEVELOPMENT=true` or `LOCAL_RUN=true`:

- **Immediate Trace Export**: No batching, instant visibility
- **Console Logging**: See traces being created in real-time
- **Debug Information**: Enhanced logging for troubleshooting
- **Force Flush**: Aggressive trace delivery on critical operations

### **Context Propagation Utilities**
```python
# Manual context propagation for custom async operations
@with_context_propagation
async def custom_async_function():
    # Automatically inherits parent span context
    pass

# Create child spans with proper context inheritance
child_span = create_child_span_with_context(
    "custom_operation", 
    "CHAIN",  # Use "CHAIN" for general ops, "LLM" for LLM calls
    custom_attribute="value"
)
```

### **Session Metadata API**
```python
# Add custom metadata to the current session
add_session_metadata(
    user_id="user123",
    conversation_topic="technical_support",
    language="en-US"
)

# Trace custom pipeline events
trace_pipeline_event(
    "custom_event",
    event_type="user_action",
    action_details="button_click"
)
```

## 🐛 **Troubleshooting**

### **Common Issues & Solutions**

#### **"Traces not appearing in Arize"**
1. **Check credentials**: Ensure `ARIZE_SPACE_ID` and `ARIZE_API_KEY` are correct
2. **Enable development mode**: Set `DEVELOPMENT=true` for immediate export
3. **Check logs**: Look for tracing initialization messages
4. **Verify network**: Ensure connectivity to `otlp.arize.com`

#### **"Spans appear disconnected"**
✅ **SOLVED**: The new session-based architecture ensures all spans are properly connected under one main trace tree.

#### **"Missing context in async functions"**
✅ **SOLVED**: All async functions now use `@with_context_propagation` decorator for automatic context inheritance.

#### **"Performance impact"**
- **Development**: Immediate export may increase latency slightly
- **Production**: Batched export minimizes performance impact
- **Disable**: Remove tracing setup call to disable completely

### **Debug Commands**
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Test tracing connectivity  
python -c "from tracing_setup import setup_arize_tracing; setup_arize_tracing()"

# Check environment variables
env | grep ARIZE
```

## 📈 **Expected Traces in Arize AX**

### **Session Overview**
- **Main session span**: 5-30 minutes duration (voice session length)
- **Child spans**: 20-50 spans per session depending on interactions
- **Attributes**: 15-25 session and configuration attributes
- **Events**: 10-100 events depending on conversation length

### **Performance Metrics**
- **LLM Latency**: Response times for each model call
- **TTS Processing**: Text-to-speech generation times
- **Pipeline Throughput**: Audio processing and delivery metrics
- **Error Rates**: Success/failure ratios for all operations

### **Conversation Analysis**
- **Turn Duration**: Time per conversation turn
- **Interruption Handling**: User interruption events and recovery
- **Audio Quality**: VAD accuracy and audio processing metrics
- **User Engagement**: Participation patterns and session duration

## 🎯 **Next Steps**

1. **Run a test session**: Start the bot and have a voice conversation
2. **Check Arize dashboard**: Verify traces are appearing correctly
3. **Explore trace data**: Navigate the session hierarchy and span details
4. **Set up alerts**: Configure Arize alerts for error conditions
5. **Analyze patterns**: Use Arize's analysis tools to identify optimization opportunities

---

**🔍 Need Help?** Check the logs for detailed tracing information and ensure your Arize credentials are properly configured. The session-based architecture ensures comprehensive observability across your entire voice agent pipeline! 