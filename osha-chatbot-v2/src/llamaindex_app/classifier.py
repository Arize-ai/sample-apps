from enum import Enum
from typing import Tuple
import logging
from llama_index.core import Response
from pydantic import BaseModel, Field
from .tools import RiskScoringTools
from .config import Settings, CLASSIFICATION_PROMPT, RAG_PROMPT, TEMPLATE_VERSION
from opentelemetry.trace import Status, StatusCode
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes
from openinference.instrumentation import using_prompt_template
import json

logger = logging.getLogger(__name__)


class BedrockError(Exception):
    pass


class QueryType(BaseModel):
    category: str = Field(
        description="The category of the query: 'OSHA', 'risk_assessment', or 'out_of_scope'"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")


class QueryCategory(str, Enum):
    OSHA = "OSHA"
    RISK_ASSESSMENT = "risk_assessment"
    OUT_OF_SCOPE = "out_of_scope"


class QueryClassifier:
    def __init__(self, query_engine, bedrock_client, model):
        self.query_engine = query_engine
        self.bedrock_client = bedrock_client
        self.model = model
        self.risk_tools = RiskScoringTools.get_all_tools()
        self.settings = Settings()
        self.tracer = trace.get_tracer(__name__)

    def _parse_classification_response(self, response_text: str) -> QueryType:
        try:
            cleaned_text = response_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].strip()

            return QueryType(**json.loads(cleaned_text))
        except Exception as e:
            logger.error(f"Failed to parse classification response: {e}")
            raise

    def _call_bedrock(self, system_prompt: str, query: str, span=None) -> str:
        try:
            if span:
                span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE, system_prompt)

            response = self.bedrock_client.converse(
                modelId=self.model,
                messages=[{"role": "user", "content": [{"text": query}]}],
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": 0, "maxTokens": 4096},
            )

            output = (
                response.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
            )

            return output
        except Exception as e:
            if span:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
            raise BedrockError(f"Bedrock API error: {str(e)}")

    def classify_query(self, query: str, span=None) -> Tuple[QueryCategory, float]:
        TEMPLATE_VERSION = "1.0.0"
        template_vars = {"query": str(query)}

        with using_prompt_template(
            template=CLASSIFICATION_PROMPT,
            variables=template_vars,
            version=TEMPLATE_VERSION,
        ):
            formatted_prompt = CLASSIFICATION_PROMPT.format(**template_vars)
            output = self._call_bedrock(formatted_prompt, query)
            classification = self._parse_classification_response(output)

        if span:
            span.set_attribute("query.category", classification.category)
            span.set_attribute("query.confidence", classification.confidence)

        return QueryCategory(classification.category), classification.confidence

    def get_response(self, query: str, category: QueryCategory, span=None) -> Response:
        try:
            if category == QueryCategory.OSHA:
                try:
                    nodes = self.query_engine.retrieve(query)

                    # Create a dictionary of context variables, with empty strings as defaults
                    template_vars = {
                        "context_1": "",
                        "context_2": "",
                        "context_3": "",
                        "query": str(query),
                    }

                    # Fill in available contexts from nodes
                    for i, node in enumerate(nodes, start=1):
                        if i <= 3:  # Only use first 3 nodes
                            template_vars[f"context_{i}"] = str(node.text)

                    with using_prompt_template(
                        template=RAG_PROMPT,
                        variables=template_vars,
                        version=TEMPLATE_VERSION,
                    ):
                        formatted_prompt = RAG_PROMPT.format(**template_vars)
                        response_text = self._call_bedrock(formatted_prompt, query)

                    return Response(response=response_text, source_nodes=nodes)
                except Exception as e:
                    logger.error(f"Error in OSHA response generation: {str(e)}")
                    raise
            elif category == QueryCategory.RISK_ASSESSMENT:
                tool = next(
                    t
                    for t in self.risk_tools
                    if t.metadata.name == "calculate_risk_score"
                )
                result = tool()
                return Response(response=result)
            else:
                return Response(
                    response="I'm trained to help with OSHA-related questions and risk assessment inquiries. How can I assist you with either of these topics?"
                )
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            if span:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
            raise


# this is using llama abstraction
# class QueryClassifier:
#     def __init__(self, query_engine, bedrock_client, model):
#         self.query_engine = query_engine
#         self.bedrock_client = bedrock_client
#         self.model = model
#         self.risk_tools = RiskScoringTools.get_all_tools()

#     def _parse_classification_response(self, response_text: str) -> QueryType:
#         try:
#             cleaned_text = response_text.strip()
#             if "```json" in cleaned_text:
#                 cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
#             elif "```" in cleaned_text:
#                 cleaned_text = cleaned_text.split("```")[1].strip()

#             return QueryType(**json.loads(cleaned_text))
#         except Exception as e:
#             logger.error(f"Failed to parse classification response: {e}")
#             raise

#     def classify_query(self, query: str, span=None) -> Tuple[QueryCategory, float]:
#         try:
#             inference_config = {"temperature": 0, "maxTokens": 512}
#             classification_response = self.bedrock_client.converse(
#                 modelId=self.model,
#                 messages=[{"role": "user", "content": [{"text": query}]}],
#                 system=[{"text": CLASSIFICATION_PROMPT.format(query=query)}],
#                 inferenceConfig=inference_config,
#             )

#             output = (
#                 classification_response.get("output", {})
#                 .get("message", {})
#                 .get("content", [{}])[0]
#                 .get("text", "")
#             )
#             classification = self._parse_classification_response(output)

#             if span:
#                 span.set_attribute("query.category", classification.category)
#                 span.set_attribute("query.confidence", classification.confidence)

#             return QueryCategory(classification.category), classification.confidence

#         except AttributeError as e:
#             logger.error(f"Bedrock client error: {str(e)}")
#             raise
#         except Exception as e:
#             if span:
#                 span.set_status(Status(StatusCode.ERROR))
#                 span.record_exception(e)
#             raise

#     def get_response(self, query: str, category: QueryCategory, span=None) -> Response:
#         try:
#             if category == QueryCategory.OSHA:
#                 return self.query_engine.query(query)
#             elif category == QueryCategory.RISK_ASSESSMENT:
#                 tool = next(
#                     t
#                     for t in self.risk_tools
#                     if t.metadata.name == "calculate_risk_score"
#                 )
#                 result = tool()
#                 return Response(response=result)
#             else:
#                 return Response(
#                     response="I'm trained to help with OSHA-related questions and risk assessment inquiries. How can I assist you with either of these topics?"
#                 )
#         except Exception as e:
#             logger.error(f"Error getting response: {e}")
#             if span:
#                 span.set_status(Status(StatusCode.ERROR))
#                 span.record_exception(e)
#             raise
