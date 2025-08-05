import argparse
import asyncio
import os
import sys
from typing import Any, List, TypedDict

from arize.otel import register
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from openinference.instrumentation.langchain import LangChainInstrumentor

from .graph import build_app

load_dotenv()


class ConversationState(TypedDict):
    messages: List  # sensitive information
    question: str
    error: str | None
    ecode: str | None
    columns: list | None
    s3_path: str | None
    result: str | None  # sensitive information
    df_status: str | None
    report_suggestion_result: str | None
    report_suggestion_result_json: str | None
    interpretation: str | None
    exec_retry_count: int
    final: bool | None


tracer_provider = register(
    project_name=os.getenv("ARIZE_PROJECT_NAME"),
    api_key=os.getenv("ARIZE_API_KEY"),
    space_id=os.getenv("ARIZE_SPACE_ID"),
    # endpoint=os.getenv("PHOENIX_ENDPOINT"),
)

LangChainInstrumentor().instrument(tracer_provider=tracer_provider)


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
