# OSHA & Risk Assessment Assistant

An intelligent assistant application that handles OSHA-related queries and business risk assessments using LLM-powered classification and response generation. The application leverages AWS Bedrock for LLM capabilities and integrates with Arize for experiment tracking and monitoring.

## Features

- Query classification between OSHA regulations and risk assessment queries
- RAG (Retrieval Augmented Generation) for OSHA-related questions
- Risk scoring tools for business risk assessment
- Arize + OpenInference instrumentation for monitoring and tracking of all relevant spans
- Integration with Arize for experiment management and evaluation

## Prerequisites

- Python 3.11+
- AWS credentials with Bedrock access
- Arize account and API credentials

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_SESSION_TOKEN=your_aws_session_token
AWS_REGION=your_aws_region
MODEL=Bedrock Model
ARIZE_API_KEY=your_arize_api_key
ARIZE_DEVELOPER_KEY=your_arize_developer_key
ARIZE_SPACE_ID=your_arize_space_id
ARIZE_MODEL_ID=your_model_id
```

## Project Structure

- `main.py`: Application entry point and session management
- `classifier.py`: Query classification and response generation logic
- `instrumentation.py`: OpenTelemetry setup and configuration
- `requirements.txt`: Project dependencies
- `arize_testing_experiment.ipynb`: Notebook for running experiments with Arize, this is currently configured 

## Usage

To run the application:

```bash
python -m src.llamaindex_app.main
```

The application will start an interactive session where you can:
- Ask OSHA-related questions
- Request risk assessments; this is intended to mock a logged in user so it will present a "profile" that it used to provide a risk score.
- Type 'end' to conclude the current session
- Type 'quit' to exit the application

## Experimentation

To run experiments and evaluate model performance:

1. Open `arize_testing_experiment.ipynb` in Jupyter
2. Ensure your environment variables are set
3. Run the notebook cells to execute experiments and view results

## Monitoring

The application is instrumented with OpenTelemetry and sends telemetry data to Arize. You can monitor:
- Query classification performance
- Response generation quality
- Error rates and types
- System performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]