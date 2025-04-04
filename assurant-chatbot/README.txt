# Installation and Setup Guide for Azure OpenAI Integration

## Requirements

- Python 3.8+
- Access to OpenAI direct API key

## Step 1: Install Required Packages

```bash
# Install core dependencies
pip install -r requirements.txt

```

## Step 2: Configure Environment Variables

Create a `.env` file in your project root with the following settings:

```ini
#OpenAI Configuration - Required
OPENAI_MODEL=gpt-4-turbo
OPENAI_API_KEY=your_api_key_here

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

## Step 4: Run the Application

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