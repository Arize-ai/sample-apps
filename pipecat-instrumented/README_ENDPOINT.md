# Pipecat Agent Starter Scripts

Scripts to start Pipecat agents using the official API format.

## Quick Setup

1. **Install dependencies:**
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Copy the example file
   cp env.example .env
   
   # Edit .env and add your Pipecat Cloud API key
   PIPECAT_CLOUD_API_KEY=pk_your_actual_api_key_here
   ```

3. **Run the scripts:**
   ```bash
   # Simple version
   python hit_endpoint_simple.py
   
   # Full-featured version
   python start_pipecat_agent.py
   ```

## Scripts Available

### `hit_endpoint_simple.py`
- Simple async script using aiohttp
- Starts an agent with basic configuration
- Good for quick testing

### `start_pipecat_agent.py`
- Comprehensive script with full error handling
- Supports custom agent names and data
- Multiple examples included
- Better for production use

## API Format

Both scripts use the official Pipecat Cloud API format:

```python
endpoint = "https://api.pipecat.daily.co/v1/public/{service}/start"
agent_name = "my-first-agent"
api_key = "pk_..."

async with aiohttp.ClientSession() as session:
    response = await session.post(
        f"{endpoint.format(service=agent_name)}",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "createDailyRoom": True,  # Creates a Daily room
            "body": {"custom": "data"}  # Data to pass to your agent
        }
    )
```

## Customization

You can easily modify the scripts to:
- Change the agent name
- Add custom data in the request body
- Modify Daily room settings
- Add additional error handling

## Environment Variables

Required:
- `PIPECAT_CLOUD_API_KEY` - Your Pipecat Cloud API key (starts with `pk_`)

The scripts automatically load environment variables from a `.env` file using python-dotenv.