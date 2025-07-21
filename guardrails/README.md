# GuardRails Multiple Validators

This project demonstrates how to use GuardRails AI with multiple validators:
- **GibberishText**: Detects and prevents nonsensical text in LLM outputs
- **RestrictToTopic**: Ensures responses stay within specified topics
- **ArizeDatasetEmbeddings**: Validates responses against dataset embeddings
- **DetectPII**: Detects and prevents personally identifiable information (PII) in inputs

## Project Structure

```
guardrails/
├── config.py                    # GuardRails configuration with multiple validators
├── requirements.txt             # Python dependencies
├── setup_nltk.py                # Script to download required NLTK data
├── test_nltk.py                 # Test script to verify NLTK tokenization
├── test_app.py                  # Test application using single guard
├── test_multiple_guards.py      # Test application using all guards
├── test_pii_detection.py        # Comprehensive PII detection tests
└── README.md                    # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download NLTK Data

The GibberishText validator requires NLTK data for sentence tokenization. Run the setup script:

```bash
python setup_nltk.py
```

Or manually download the data:

```bash
python -c "import nltk; import ssl; ssl._create_default_https_context = ssl._create_unverified_context; nltk.download('punkt_tab'); nltk.download('punkt')"
```

### 3. Verify Setup

Test that NLTK tokenization works correctly:

```bash
python test_nltk.py
```

## Usage

### Starting the GuardRails Server

#### Method 1: Using the startup script (Recommended)

Make sure you have your OpenAI API key set in your environment:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Then run the server using the startup script:

```bash
python run_server.py
```

#### Method 2: Direct server execution

Alternatively, you can run the server directly:

```bash
python server.py
```

#### Method 3: Using uvicorn directly

You can also run the server using uvicorn directly:

```bash
uvicorn server:app --host 127.0.0.1 --port 8000
```

The server will start at `http://127.0.0.1:8000` with all four guards available at:
- Root endpoint: `http://127.0.0.1:8000/`
- Guards list: `http://127.0.0.1:8000/guards`
- Health check: `http://127.0.0.1:8000/health`
- Gibberish Guard: `http://127.0.0.1:8000/guards/gibberish_guard/openai/v1/chat/completions`
- Topic Guard: `http://127.0.0.1:8000/guards/restrict_to_topic/openai/v1/chat/completions`
- Dataset Embeddings Guard: `http://127.0.0.1:8000/guards/dataset_embeddings_guard/openai/v1/chat/completions`
- PII Detection Guard: `http://127.0.0.1:8000/guards/pii_detection_guard/openai/v1/chat/completions`

### Testing the Guards

Run the test application to see all three guards in action:

```bash
python test_multiple_guards.py
```

This will:
1. Test the gibberish guard with normal text and gibberish requests
2. Test the topic guard with valid and invalid topics
3. Test the dataset embeddings guard with data quality examples
4. Test the PII detection guard with safe content and various PII types
5. Show validation results for each guard

For testing individual guards, you can still use:

```bash
python test_app.py  # Tests only the gibberish guard
```

#### Comprehensive PII Detection Testing

For detailed PII detection testing, run the dedicated test suite:

```bash
python test_pii_detection.py
```

This comprehensive test suite includes:
- Testing safe content without PII
- Email address detection
- Phone number detection (various formats)
- Credit card number detection
- Social Security Number detection
- Mixed content scenarios
- Guard configuration verification
- Failure message format validation

### Using with OpenAI Client

#### Using the Gibberish Guard

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:8000/guards/gibberish_guard/openai/v1',
    api_key='your-openai-api-key'  # Use your actual OpenAI API key
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": "Write a clear, coherent response about machine learning."
    }]
)

print(response.choices[0].message.content)
print(f"Validation passed: {response.guardrails['validation_passed']}")
```

#### Using the Topic Restriction Guard

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:8000/guards/restrict_to_topic/openai/v1',
    api_key='your-openai-api-key'  # Use your actual OpenAI API key
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": "Explain the basics of stock market investing."
    }]
)

print(response.choices[0].message.content)
print(f"Validation passed: {response.guardrails['validation_passed']}")
```

#### Using the Dataset Embeddings Guard

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:8000/guards/dataset_embeddings_guard/openai/v1',
    api_key='your-openai-api-key'  # Use your actual OpenAI API key
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": "Explain the concept of data quality in machine learning."
    }]
)

print(response.choices[0].message.content)
print(f"Validation passed: {response.guardrails['validation_passed']}")
```

#### Using the PII Detection Guard

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:8000/guards/pii_detection_guard/openai/v1',
    api_key='your-openai-api-key'  # Use your actual OpenAI API key
)

# This will pass - no PII detected
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": "Explain the importance of data privacy in applications."
    }]
)

print(response.choices[0].message.content)
print(f"Validation passed: {response.guardrails['validation_passed']}")

# This will fail - PII detected
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": "My email is john.doe@example.com, please help me."
        }]
    )
except Exception as e:
    print(f"PII detected: {e}")
```

## Configuration Details

### Multiple Guards Setup

The `config.py` file sets up four guards with different validators:

```python
from guardrails import Guard
from guardrails.hub import GibberishText, RestrictToTopic, ArizeDatasetEmbeddings, DetectPII

def return_failure_message(value, fail_result):
    return "Sorry, I can't help with that."

# First guard: Gibberish detection
guard = Guard()
guard.name = 'gibberish_guard'
guard.use(GibberishText(on_fail=return_failure_message))

# Second guard: Restrict to topic
topic_guard = Guard()
topic_guard.name = 'restrict_to_topic'
topic_guard.use(RestrictToTopic(
    valid_topics=["finance"],
    on_fail=return_failure_message
))

# Third guard: Dataset embeddings validation
embeddings_guard = Guard()
embeddings_guard.name = 'dataset_embeddings_guard'
embeddings_guard.use(ArizeDatasetEmbeddings(
    on_fail=return_failure_message
))

# Fourth guard: PII detection
pii_guard = Guard()
pii_guard.name = 'pii_detection_guard'
pii_guard.use(DetectPII(on_fail=return_failure_message))
```

### Validator Options

#### GibberishText Validator Options:
- `on_fail='exception'`: Raises an exception when gibberish is detected
- `on_fail='fix'`: Attempts to fix the gibberish text
- `on_fail='filter'`: Filters out gibberish sentences
- `on_fail='refrain'`: Returns empty string when gibberish is detected

#### RestrictToTopic Validator Options:
- `valid_topics`: List of allowed topics (can be modified in config.py)
- `on_fail='exception'`: Raises an exception when content is off-topic
- `on_fail='fix'`: Attempts to redirect content to valid topics
- `on_fail='filter'`: Filters out off-topic content
- `on_fail='refrain'`: Returns empty string when content is off-topic

#### ArizeDatasetEmbeddings Validator Options:
- `on_fail='exception'`: Raises an exception when content doesn't match dataset embeddings
- `on_fail='fix'`: Attempts to adjust content to match dataset patterns
- `on_fail='filter'`: Filters out content that doesn't match embeddings
- `on_fail='refrain'`: Returns empty string when content doesn't match dataset
- `on_fail=custom_function`: Uses a custom function to handle validation failures

#### DetectPII Validator Options:
- `on_fail='exception'`: Raises an exception when PII is detected
- `on_fail='fix'`: Attempts to redact or mask detected PII
- `on_fail='filter'`: Filters out content containing PII
- `on_fail='refrain'`: Returns empty string when PII is detected
- `on_fail=custom_function`: Uses a custom function to handle PII detection failures
- Detects various PII types: emails, phone numbers, credit cards, SSNs, addresses, and more

## Troubleshooting

### SSL Certificate Issues

If you encounter SSL certificate errors when downloading NLTK data:

1. **Install certificates** (recommended):
   ```bash
   /Applications/Python\ 3.x/Install\ Certificates.command
   ```
   (Replace 3.x with your Python version)

2. **Use unverified SSL context** (temporary fix):
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

### NLTK Data Not Found

If you get "Resource punkt_tab not found" errors:

1. Run the setup script: `python setup_nltk.py`
2. Verify with: `python test_nltk.py`
3. Check NLTK data locations: `python -c "import nltk; print(nltk.data.path)"`

### Environment Variables

Make sure to set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Example Output

When working correctly, you should see output like:

```
Gibberish Guard:
Normal text: "Machine learning is a powerful technology..."
Validation passed: True

Topic Guard:
Finance topic: "Stock market investing involves..."
Validation passed: True

Off-topic request: "Sorry, I can't help with that."
Validation passed: False

Dataset Embeddings Guard:
Data quality response: "Data quality in machine learning..."
Validation passed: True

PII Detection Guard:
Safe content: "Data privacy is important in applications..."
Validation passed: True

PII content: "Sorry, I can't help with that."
Validation passed: False
```

## Contributing

To extend this project:

1. Add new validators to `config.py`
2. Create additional test cases in `test_app.py`
3. Update the README with new features

## Resources

- [GuardRails AI Documentation](https://docs.guardrailsai.com/)
- [GibberishText Validator](https://hub.guardrailsai.com/validator/gibberish_text)
- [NLTK Documentation](https://www.nltk.org/) 