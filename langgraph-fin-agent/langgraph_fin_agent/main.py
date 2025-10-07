import argparse
import asyncio
import sys
from typing import Any, List, TypedDict

from langchain_core.messages import HumanMessage
# from relari_otel import Relari
# from relari_otel.specifications import Specifications

import json
import copy
import os
import dotenv

dotenv.load_dotenv()

from .graph import build_app


class ConversationState(TypedDict):
    messages: List # sensitive information
    question: str
    error: str | None
    ecode: str | None
    columns: list | None
    s3_path: str | None
    result: str | None # sensitive information
    df_status: str | None
    report_suggestion_result: str | None
    report_suggestion_result_json: str | None
    interpretation: str | None
    exec_retry_count: int
    final: bool | None
    
    
# Tracing setup
from arize.otel import BatchSpanProcessor, register
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span

# # Our custom span processor solution
# class FilteringSpanProcessor(BatchSpanProcessor):
#     def __init__(self, span_fields: list, output_mask_list: list, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.span_fields = span_fields
#         self.output_mask = output_mask_list

#     def _filter_condition(self, span: Span) -> bool:
#         # returns modified span with the filtered out fields
#         if hasattr(span, "attributes"):
#             for attr in span.attributes:
#                 if attr in self.span_fields:
#                     try:
#                         attr_dict = json.loads(span.attributes[attr])
#                         success = 1
#                     except Exception as e: # not important
#                         print("ECODE-ARIZE-FilteringSpanProcessor: String-to-dict parsing error:", e)
#                         success = 0

#                     if success:
#                         new_dict = copy.deepcopy(attr_dict)
#                         for k, v in attr_dict.items():
#                             if k in self.output_mask:
#                                 # new_dict.pop(k)
#                                 new_dict[k] = "[REDACTED]"

#                         new_span_str = json.dumps(new_dict)
#                         span._attributes._dict[attr] = new_span_str # new assignment;
#                         # didn't able to modify in other terms because it is read-only ReadableSpan object
#                     else:
#                         return span

#             return span


#     def on_start(self, span: Span, parent_context: Context) -> None:
#         pass

#     def on_end(self, span: ReadableSpan) -> None:
#         span = self._filter_condition(span)
#         super().on_end(span)

# custom_span_processor = FilteringSpanProcessor(
#     endpoint=os.getenv("PHOENIX_ENDPOINT"),
#     protocol="http/protobuf",
#     span_fields = ["input.value", "output.value"],
#     output_mask_list = ["messages", "result", "final_df", "final_html", "interpretation"]
#     )

tracer_provider = register(
    project_name=os.getenv("ARIZE_PROJECT_NAME"),
    api_key=os.getenv("ARIZE_API_KEY"),
    space_id=os.getenv("ARIZE_SPACE_ID"),
    # endpoint=os.getenv("PHOENIX_ENDPOINT"),
)

# tracer_provider.add_span_processor(custom_span_processor)

from openinference.instrumentation.langchain import LangChainInstrumentor
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

# Relari.init(project_name="langgraph-fin-agent", batch=False)


async def main_interactive():
    """Start an interactive session with the Finance Assistant."""
    print("Welcome to the Financial Assistant powered by LangGraph agents!")
    print("You can ask questions about stocks, companies, and financial data.")
    print(
        "The assistant has access to public company data and can browse the web for more information if needed."
    )
    print("Type 'exit' to end the session.")

    app = build_app()
    config = {"configurable": {"thread_id": "1"}}
    while True:
        query = input("\nYour question: ").strip()
        if query.lower() == "exit":
            print("Thank you for using the Finance Assistant. Goodbye!")
            break
        inputs = {"messages": [HumanMessage(content=query)]}
        async for chunk in app.astream(inputs, config, stream_mode="values"):
            chunk["messages"][-1].pretty_print()
        # with Relari.start_new_sample(scenario_id="interactive-query"):
        #     async for chunk in app.astream(inputs, config, stream_mode="values"):
        #         chunk["messages"][-1].pretty_print()
        #     Relari.set_output(chunk["messages"][-1].content)
        print("=" * 80)


async def main_eval():
    app = build_app()

    async def runnable(data: Any):
        inputs = {"messages": [HumanMessage(content=data)]}
        config = {"configurable": {"thread_id": "1"}}
        async for chunk in app.astream(inputs, config, stream_mode="values"):
            chunk["messages"][-1].pretty_print()
        return chunk["messages"][-1].content

    # specs = Specifications.load("specifications.json")
    # await Relari.eval_runner(specs=specs, runnable=runnable)


def main():
    parser = argparse.ArgumentParser(
        description="Financial Assistant powered by LangGraph agents"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--eval", "-e", action="store_true", help="Run evaluation mode")

    args = parser.parse_args()

    if args.interactive and args.eval:
        print("Error: Cannot specify both interactive and eval modes")
        sys.exit(1)
    elif args.interactive:
        asyncio.run(main_interactive())
    elif args.eval:
        asyncio.run(main_eval())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
