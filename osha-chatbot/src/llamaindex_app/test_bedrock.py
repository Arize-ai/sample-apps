import logging
import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()


def generate_conversation(bedrock_client, model_id, system_prompts, messages):
    """
    Sends messages to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON) : The system prompts for the model to use.
        messages (JSON) : The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.
    """
    logger.info("Generating message with model %s", model_id)

    temperature = 0.5
    top_k = 200

    inference_config = {"temperature": temperature}
    additional_model_fields = {"top_k": top_k}

    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields,
    )

    token_usage = response["usage"]
    logger.info("Input tokens: %s", token_usage["inputTokens"])
    logger.info("Output tokens: %s", token_usage["outputTokens"])
    logger.info("Total tokens: %s", token_usage["totalTokens"])
    logger.info("Stop reason: %s", response["stopReason"])

    return response


def main():
    """
    Entrypoint for Anthropic Claude 3 Sonnet example.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

    system_prompts = [
        {
            "text": "You are an app that creates playlists for a radio station that plays rock and pop music."
            "Only return song names and the artist."
        }
    ]
    message_1 = {"role": "user", "content": [{"text": "Create a list of 3 pop songs."}]}
    message_2 = {
        "role": "user",
        "content": [
            {"text": "Make sure the songs are by artists from the United Kingdom."}
        ],
    }
    messages = []

    try:
        # Create bedrock client with credentials from environment
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        )

        # Start conversation with 1st message
        messages.append(message_1)
        response = generate_conversation(
            bedrock_client, model_id, system_prompts, messages
        )

        output_message = response["output"]["message"]
        messages.append(output_message)

        # Continue with 2nd message
        messages.append(message_2)
        response = generate_conversation(
            bedrock_client, model_id, system_prompts, messages
        )

        output_message = response["output"]["message"]
        messages.append(output_message)

        # Show conversation
        for message in messages:
            print(f"Role: {message['role']}")
            for content in message["content"]:
                print(f"Text: {content['text']}")
            print()

    except ClientError as err:
        message = err.response["Error"]["Message"]
        logger.error("A client error occurred: %s", message)
        print(f"A client error occured: {message}")

    else:
        print(f"Finished generating text with model {model_id}.")


if __name__ == "__main__":
    main()
