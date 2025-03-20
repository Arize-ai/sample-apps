from setuptools import setup, find_packages

setup(
    name="llamaindex_app",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "llama-index-core>=0.12.0",
        "llama-index-llms-openai>=0.3.1",
        "llama-index-embeddings-openai>=0.1.6",
        "llama-index-readers-file>=0.1.3",
        "python-dotenv>=1.0.0",
        "pydantic-settings>=2.1.0",
        "openinference-instrumentation-llama_index>=0.1.0",
        "arize-phoenix>=0.0.7",
        "arize-otel>=0.0.1",  # Added Arize OTEL
    ],
    python_requires=">=3.9",
    "boto3>=1.28.0",
    "botocore>=1.31.0"
)
