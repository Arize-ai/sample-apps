# Installation and Setup Guide for Azure OpenAI Integration

## Requirements

- Python 3.8+
- Access to Azure OpenAI via VPN or direct API key
- Required Azure OpenAI deployment

## Step 1: Install Required Packages

```bash
# Install core dependencies
pip install -r requirements.txt

```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root with the following settings:

```ini
# Azure OpenAI Configuration - Required
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=your_api_version
AZURE_OPENAI_MODEL=gpt-4-turbo
AZURE_OPENAI_API_KEY=your_api_key_here

# Other required settings for your application
ARIZE_SPACE_ID=your_space_id
ARIZE_API_KEY=your_api_key
ARIZE_MODEL_ID=your_model_id
```

## Step 3: Install Guardrails AI
Make sure you are not on a VPN, this creates issue with the Hub.
```bash
#This gets guardrails setup including setting your API key
guardrails configure

guardrails hub install hub://guardrails/detect_jailbreak

guardrails hub install hub://guardrails/toxic_language

## Step 4: Test Azure OpenAI Connection

Create a small test script to verify the connection:

```python
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    # Initialize client (VPN authentication)
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"]
    )

    # Test a simple call
    response = client.chat.completions.create(
        deployment_id=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[{"role": "user", "content": "Hello, are you working?"}],
        max_tokens=10
    )

    print("Response:", response.choices[0].message.content)
    print("Connection successful!")
except Exception as e:
    print(f"Error connecting to Azure OpenAI: {str(e)}")
```

## Step 5: Run the Application

Once your environment is configured, run your application:

```bash
python -m src.llamaindex_app.main
```

## Troubleshooting

1. **VPN Authentication Issues**
   - Ensure you're connected to the correct VPN
   - Check that you have permission to access the Azure OpenAI resource
   - Try adding an explicit API key temporarily to isolate the issue

2. **Missing Environment Variables**
   - Double-check that all required environment variables are set
   - Verify the `.env` file is in the correct location
   - Make sure you're using `python-dotenv` to load the variables

3. **Module Not Found Errors**
   - Verify all required packages are installed
   - Check your Python path and virtual environment

4. **API Errors**
   - Check the deployment name is correct
   - Verify the endpoint URL is correct
   - Ensure the API version is supported