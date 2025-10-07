package com.arize.openinference.examples;

import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.openai.OpenAiChatModel;

/**
 * Service class demonstrating chain operations for AI calls.
 * Instrumentation is handled at the call site using ChainOperation method references.
 *
 * Note: This is a simple example - in practice you'd inject this as a Spring component.
 */
public class ChainService {

    private final OpenAiChatModel chatModel;

    public ChainService(OpenAiChatModel chatModel) {
        this.chatModel = chatModel;
    }

    public ChatResponse generatePirateNames() {
        return chatModel.call(new Prompt("Generate the names of 5 famous pirates."));
    }

    public ChatResponse getWeatherInfo(String location) {
        return chatModel.call(new Prompt("What is the current weather in " + location + " in Fahrenheit?"));
    }

    public ChatResponse getMusicInfo(String location) {
        return chatModel.call(new Prompt("What's the current trending song in " + location + "?"));
    }
}
