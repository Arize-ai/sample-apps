from enum import Enum
from typing import Tuple
import logging
from llama_index.core import Response
from pydantic import BaseModel, Field
from src.llamaindex_app.tools import RiskScoringTools
from src.llamaindex_app.config import (
    Settings,
    CLASSIFICATION_PROMPT,
    RAG_PROMPT,
    TEMPLATE_VERSION,
)
from opentelemetry.trace import Status, StatusCode
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes
from openinference.instrumentation import using_prompt_template
import json

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    pass


class QueryType(BaseModel):
    category: str = Field(
        description="The category of the query: 'ford_mustang', or 'out_of_scope'"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")


class QueryCategory(str, Enum):
    FORD_MUSTANG = "ford_mustang"
    OUT_OF_SCOPE = "out_of_scope"


class QueryClassifier:
    def __init__(self, query_engine, openai_client):
        self.query_engine = query_engine
        self.openai_client = openai_client
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

    def _call_openai(self, system_prompt: str, query: str, span=None) -> str:
        try:
            if span:
                span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE, system_prompt)

            response = self.openai_client.chat.completions.create(
                model=self.settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=4096,
            )

            return response.choices[0].message.content
        except Exception as e:
            if span:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
            raise OpenAIError(f"OpenAI API error: {str(e)}")

    def classify_query(self, query: str, span=None) -> Tuple[QueryCategory, float]:
        template_vars = {"query": str(query)}

        with using_prompt_template(
            template=CLASSIFICATION_PROMPT,
            variables=template_vars,
            version=TEMPLATE_VERSION,
        ):
            formatted_prompt = CLASSIFICATION_PROMPT.format(**template_vars)
            output = self._call_openai(formatted_prompt, query, span)
            classification = self._parse_classification_response(output)

        if span:
            span.set_attribute("query.category", classification.category)
            span.set_attribute("query.confidence", classification.confidence)

        return QueryCategory(classification.category), classification.confidence

    def get_response(self, query: str, category: QueryCategory, span=None) -> Response:
        try:
            if category == QueryCategory.FORD_MUSTANG:
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
                        response_text = self._call_openai(formatted_prompt, query, span)

                    return Response(response=response_text, source_nodes=nodes)
                except Exception as e:
                    logger.error(
                        f"Error in Mustang Manual response generation: {str(e)}"
                    )
                    raise
            else:
                return Response(
                    response="I'm trained to help with questions about Ford's Mustang manuals. How can I assist you with this topic?"
                )
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            if span:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
            raise
