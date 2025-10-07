package com.arize.openinference.examples;

import static com.arize.semconv.trace.SemanticResourceAttributes.SEMRESATTRS_PROJECT_NAME;

import com.arize.instrumentation.OITracer;
import com.arize.instrumentation.TraceConfig;
import com.arize.instrumentation.springAI.SpringAIInstrumentor;
import com.arize.semconv.trace.SemanticConventions;
import io.github.cdimascio.dotenv.Dotenv;
import io.micrometer.observation.ObservationRegistry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator;
import io.opentelemetry.context.Scope;
import io.opentelemetry.context.propagation.ContextPropagators;
import io.opentelemetry.exporter.logging.LoggingSpanExporter;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporter;
import io.opentelemetry.exporter.otlp.trace.OtlpGrpcSpanExporterBuilder;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.sdk.resources.Resource;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import io.opentelemetry.sdk.trace.export.SimpleSpanProcessor;
import java.time.Duration;
import java.util.Map;
import java.util.function.Function;
import java.util.List;
import java.util.function.Supplier;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.ai.openai.OpenAiChatOptions;
import org.springframework.ai.openai.api.OpenAiApi;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.function.FunctionToolCallback;

/**
 * Spring AI OpenInference Example
 * 
 * This example demonstrates hybrid OpenInference instrumentation with Spring AI:
 * - Automatic LLM instrumentation via Spring AI instrumentor
 * - Decorator like chain-level instrumentation for business logic
 */
public class SpringAI {
    private static final Logger logger = Logger.getLogger(SpringAI.class.getName());
    private static SdkTracerProvider tracerProvider;

    public enum Unit {
        C,
        F
    }

    public record WeatherRequest(String location, Unit unit) {}

    public record WeatherResponse(double temp, Unit unit) {}

    public record MusicRequest(String location) {}

    public record MusicResponse(String song, String description) {}

    // Clean chain operation record
    public record ChainOperation(Supplier<ChatResponse> methodCall, String prompt) {}

    static class WeatherService implements Function<WeatherRequest, WeatherResponse> {
        public WeatherResponse apply(WeatherRequest request) {
            return new WeatherResponse(30.0, Unit.C);
        }
    }

    static class MusicService implements Function<MusicRequest, MusicResponse> {
        public MusicResponse apply(MusicRequest request) {
            return new MusicResponse("hips dont lie.", "I dont deny.");
        }
    }

    /**
     * Process chain operations with a decorator like instrumentation
     * This creates a CHAIN span that wraps the LLM call
     */
    private static ChatResponse processObserveChain(Object service, ChainOperation operation) {
        Span chainSpan = tracerProvider
                .get("openinference-chain")
                .spanBuilder("chain-operation")
                .startSpan();

        try (Scope scope = chainSpan.makeCurrent()) {
            // Set span kind to CHAIN - ONLY CHAIN attributes
            chainSpan.setAttribute(
                    SemanticConventions.OPENINFERENCE_SPAN_KIND,
                    SemanticConventions.OpenInferenceSpanKind.CHAIN.getValue());

            // Capture input prompt - ONLY basic input/output for CHAIN
            if (operation.prompt != null && !operation.prompt.isEmpty()) {
                chainSpan.setAttribute(SemanticConventions.INPUT_VALUE, operation.prompt);
                chainSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "text/plain");
            }

            // Execute the method - Spring AI instrumentor will create LLM spans automatically
            ChatResponse result = operation.methodCall.get();

            // Set clean output - ONLY basic output for CHAIN
            if (result != null && result.getResult() != null && result.getResult().getOutput() != null) {
                String outputText = result.getResult().getOutput().getText();
                chainSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, outputText);
                chainSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "text/plain");
            }

            chainSpan.setStatus(StatusCode.OK);
            return result;

        } catch (Exception e) {
            chainSpan.recordException(e);
            chainSpan.setStatus(StatusCode.ERROR, e.getMessage());
            throw e;
        } finally {
            chainSpan.end();
        }
    }

    public static void main(String[] args) {
        // Load .env file for configuration
        Dotenv dotenv = Dotenv.configure()
                .directory("./")
                .filename(".env")
                .ignoreIfMalformed()
                .ignoreIfMissing()
                .load();

        String destination = dotenv.get("TRACE_DESTINATION", "phoenix");
        initializeOpenTelemetry(dotenv);

        String apiKey = dotenv.get("OPENAI_API_KEY");
        if (apiKey == null) {
            logger.log(Level.SEVERE, "Please set OPENAI_API_KEY in .env file or environment variable");
            System.exit(1);
        }

        ToolCallback weatherToolCallBack = FunctionToolCallback.builder("currentWeather", new WeatherService())
                .description("Get the weather in location")
                .inputType(WeatherRequest.class)
                .build();

        ToolCallback musicToolCallBack = FunctionToolCallback.builder("topSong", new MusicService())
                .description("Gets the stop song in a location")
                .inputType(MusicRequest.class)
                .build();

        OpenAiApi openAiApi = OpenAiApi.builder().apiKey(apiKey).build();
        OpenAiChatOptions openAiChatOptions = OpenAiChatOptions.builder()
                .model("gpt-4")
                .temperature(0.4)
                .maxTokens(200)
                .toolCallbacks(weatherToolCallBack, musicToolCallBack)
                .parallelToolCalls(true)
                .build();

        // Create OITracer using the initialized tracer provider
        OITracer tracer = new OITracer(tracerProvider.get("com.arize.spring-ai"), TraceConfig.getDefault());

        // Create observation registry with Spring AI instrumenter
        ObservationRegistry registry = ObservationRegistry.create();
        registry.observationConfig().observationHandler(new SpringAIInstrumentor(tracer));

        // Create Spring AI Chat Model with instrumentation
        OpenAiChatModel chatModel = OpenAiChatModel.builder()
                .openAiApi(openAiApi)
                .defaultOptions(openAiChatOptions)
                .observationRegistry(registry)
                .build();

        // Use the model - traces will be automatically created by Spring AI instrumenter
        // Parent spans will be created by decorator like manual chain instrumentation
        logger.info("Sending requests to OpenAI with Spring AI instrumenter...");

        // Create ChainService to demonstrate chain operations
        ChainService chainService = new ChainService(chatModel);

        // Define chain operations to demonstrate decorator like instrumentation
        List<ChainOperation> operations = List.of(
            new ChainOperation(() -> chainService.generatePirateNames(), "Generate the names of 5 famous pirates."),
            new ChainOperation(() -> chainService.getWeatherInfo("miami"), "What is the current weather in miami in Fahrenheit?"),
            new ChainOperation(() -> chainService.getMusicInfo("Miami"), "What's the current trending song in Miami?")
        );

        // Execute all chain operations with instrumentation
        for (int i = 0; i < operations.size(); i++) {
            ChainOperation operation = operations.get(i);
            logger.info("\\nExecuting operation " + (i + 1) + "...");
            
            // Create CHAIN span for business logic (this will also create LLM spans)
            ChatResponse response = processObserveChain(chainService, operation);
            
            logger.info("Response: " + response.getResult().getOutput().getText());
        }

        if (tracerProvider != null) {
            logger.info("Flushing and shutting down trace provider...");

            // Force flush all pending spans
            CompletableResultCode flushResult = tracerProvider.forceFlush();
            flushResult.join(10, java.util.concurrent.TimeUnit.SECONDS);

            if (flushResult.isSuccess()) {
                logger.info("Successfully flushed all traces");
            } else {
                logger.warning("Failed to flush all traces");
            }

            // Shutdown the trace provider
            CompletableResultCode shutdownResult = tracerProvider.shutdown();
            shutdownResult.join(10, java.util.concurrent.TimeUnit.SECONDS);

            if (!shutdownResult.isSuccess()) {
                logger.warning("Failed to shutdown trace provider cleanly");
            }
        }

        // Display appropriate message based on destination
        if ("arize".equals(destination)) {
            System.out.println("\\nTraces have been sent to Arize AX dashboard");
        } else {
            System.out.println("\\nTraces have been sent to Phoenix at http://localhost:6006");
        }
    }

    private static void initializeOpenTelemetry(Dotenv dotenv) {
        // Get configuration from .env file with fallback to environment variables
        String destination = dotenv.get("TRACE_DESTINATION", "phoenix");
        String phoenixApiKey = dotenv.get("PHOENIX_API_KEY");
        String phoenixProjectName = dotenv.get("PHOENIX_PROJECT_NAME", "spring-ai-project");
        String arizeSpaceId = dotenv.get("ARIZE_SPACE_ID");
        String arizeApiKey = dotenv.get("ARIZE_API_KEY");
        String arizeModelId = dotenv.get("ARIZE_MODEL_ID", "spring-ai-example");

        // Create resource attributes based on destination
        Attributes resourceAttributes;
        if ("arize".equals(destination)) {
            resourceAttributes = Attributes.of(
                    AttributeKey.stringKey("model_id"), arizeModelId
            );
        } else {
            resourceAttributes = Attributes.of(
                    AttributeKey.stringKey("service.name"), "spring-ai",
                    AttributeKey.stringKey("service.version"), "0.1.0",
                    AttributeKey.stringKey(SEMRESATTRS_PROJECT_NAME), phoenixProjectName
            );
        }

        Resource resource = Resource.getDefault()
                .merge(Resource.create(resourceAttributes));

        // Configure exporter based on destination
        OtlpGrpcSpanExporterBuilder otlpExporterBuilder = OtlpGrpcSpanExporter.builder()
                .setTimeout(Duration.ofSeconds(2));

        OtlpGrpcSpanExporter otlpExporter;
        if ("arize".equals(destination)) {
            // Validate Arize configuration
            if (arizeSpaceId == null || arizeApiKey == null) {
                throw new IllegalStateException("ARIZE_SPACE_ID and ARIZE_API_KEY must be set for Arize destination");
            }

            otlpExporter = otlpExporterBuilder
                    .setEndpoint("https://otlp.arize.com/v1")
                    .setHeaders(() -> Map.of(
                            "space_id", arizeSpaceId,
                            "api_key", arizeApiKey
                    ))
                    .build();
            logger.info("Configured to send traces to Arize AX");
        } else {
            // Phoenix configuration
            otlpExporter = otlpExporterBuilder
                    .setEndpoint("http://localhost:4317")
                    .build();
            
            if (phoenixApiKey != null && !phoenixApiKey.isEmpty()) {
                otlpExporter = otlpExporterBuilder
                        .setHeaders(() -> Map.of("Authorization", String.format("Bearer %s", phoenixApiKey)))
                        .build();
            } else {
                logger.log(Level.WARNING, "Please set PHOENIX_API_KEY environment variable if auth is enabled.");
            }
            logger.info("Configured to send traces to Phoenix");
        }

        // Create tracer provider with OTLP and console exporters
        tracerProvider = SdkTracerProvider.builder()
                .addSpanProcessor(BatchSpanProcessor.builder(otlpExporter)
                        .setScheduleDelay(Duration.ofSeconds(1))
                        .build())
                .addSpanProcessor(SimpleSpanProcessor.create(LoggingSpanExporter.create()))
                .setResource(resource)
                .build();

        // Build OpenTelemetry SDK
        OpenTelemetrySdk.builder()
                .setTracerProvider(tracerProvider)
                .setPropagators(ContextPropagators.create(W3CTraceContextPropagator.getInstance()))
                .buildAndRegisterGlobal();

        if ("arize".equals(destination)) {
            System.out.println("OpenTelemetry initialized. Traces will be sent to Arize AX");
        } else {
            System.out.println("OpenTelemetry initialized. Traces will be sent to Phoenix at http://localhost:6006");
        }
    }
}