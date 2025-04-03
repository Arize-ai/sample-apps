import streamlit as st
import uuid
import logging
import sys
import os

# Import directly from local modules without package references
# These imports assume this file is in the llamaindex_app directory
from classifier import QueryClassifier
from index_manager import IndexManager
from main import init_azure_openai_client, setup_instrumentation, process_interaction

logger = logging.getLogger(__name__)

def init_app():
    """Initialize everything just once using st.session_state."""
    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True
        
        # (1) instrumentation (if needed)
        tracer_provider = setup_instrumentation()
        st.session_state["tracer"] = tracer_provider.get_tracer("llamaindex_app")

        # (2) azure client
        azure_client = init_azure_openai_client()
        st.session_state["azure_client"] = azure_client

        # (3) index manager & query engine
        index_manager = IndexManager(openai_client=azure_client)
        query_engine = index_manager.get_query_engine()
        st.session_state["query_engine"] = query_engine

        # (4) classifier
        classifier = QueryClassifier(
            query_engine=query_engine,
            openai_client=azure_client,
            deployment=st.session_state["azure_client"].deployment
        )
        st.session_state["classifier"] = classifier

        st.session_state["chat_history"] = []  # store chat Q&A pairs

def main():
    """Main Streamlit app function."""
    st.set_page_config(page_title="Assurant 10-K Analysis & Risk Assessment App")

    st.title("Assurant 10-K Analysis & Risk Assessment App")

    # Ensure everything is initialized
    init_app()

    user_question = st.text_input("Enter your question:", key="user_input")
    submit = st.button("Ask")

    if submit and user_question.strip():
        # retrieve references from st.session_state
        query_engine = st.session_state["query_engine"]
        classifier = st.session_state["classifier"]
        tracer = st.session_state["tracer"]

        session_id = str(uuid.uuid4())

        response, error = process_interaction(
            query_engine,
            classifier,
            tracer,
            user_question,
            session_id
        )

        # Store in st.session_state so we can display entire conversation
        if error:
            st.session_state["chat_history"].append(("user", user_question))
            st.session_state["chat_history"].append(("assistant", f"Error: {error}"))
        else:
            st.session_state["chat_history"].append(("user", user_question))
            st.session_state["chat_history"].append(("assistant", response.response))

            # If there are any sources
            if getattr(response, "source_nodes", None):
                source_text = "\n".join(
                    f"- {node.metadata.get('file_name', 'Unknown source')}"
                    for node in response.source_nodes
                )
                st.session_state["chat_history"].append(("assistant_sources", source_text))

    # Display the chat history
    for role, content in st.session_state["chat_history"]:
        if role == "user":
            st.markdown(f"**User**: {content}")
        elif role == "assistant":
            st.markdown(f"**Assistant**: {content}")
        elif role == "assistant_sources":
            st.markdown(f"**Sources**:\n{content}")


if __name__ == "__main__":
    main()