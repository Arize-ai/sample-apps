# Spring AI OpenInference Example

This example demonstrates how to instrument Spring AI applications with OpenInference, combining automatic LLM instrumentation with chain-level observability.

## Requirements

- Java 17+
- OpenAI API Key
- (Optional) Arize AX account or Phoenix running locally

## Step 1: Setup the Project

```bash
# Run the setup script
./setup.sh
```

This will:
- Check Java version
- Create `.env` file from template
- Make gradlew executable
- Test Gradle wrapper

## Step 2: Configure Environment Variables

Edit the `.env` file with your configuration:

```ini
# Required: OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Trace Destination (phoenix or arize)
TRACE_DESTINATION=phoenix

# Arize Configuration (if using arize destination)
ARIZE_SPACE_ID=your-arize-space-id
ARIZE_API_KEY=your-arize-api-key
ARIZE_MODEL_ID=spring-ai-example

# Phoenix Configuration (if using phoenix destination)
PHOENIX_API_KEY=your-phoenix-api-key
PHOENIX_PROJECT_NAME=spring-ai-project
```

## Step 3: Run the Application

```bash
# Execute the example
./run.sh
```

## Features

- **Automatic LLM Instrumentation**: Captures detailed LLM spans with token counts, model parameters, and tool calls
- **Chain Instrumentation**: Creates clean parent spans for business logic
- **Dual Destination Support**: Send traces to Phoenix (local) or Arize AX (cloud)
- **Tool Integration**: Demonstrates Spring AI function calling with weather and music tools

## Expected Output

When you run the example, you should see:
- Console logs showing span creation
- Three example operations: pirate names, weather info, music info
- Success message indicating traces were sent to your chosen destination

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `OPENAI_API_KEY` is set in `.env`
2. **Arize Connection**: Verify `ARIZE_SPACE_ID` and `ARIZE_API_KEY` for Arize destination
3. **Phoenix Connection**: Ensure Phoenix is running on `localhost:4317` for Phoenix destination

**Phoenix Setup:**
```bash
# Install Phoenix
pip install phoenix

# Start Phoenix
phoenix
```

The example includes console logging for all spans. Check the console output to verify traces are successfully exported.