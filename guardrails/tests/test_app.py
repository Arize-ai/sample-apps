import os

# Disable OpenTelemetry metrics export to avoid connection errors
os.environ['OTEL_METRICS_EXPORTER'] = 'none'
os.environ['OTEL_TRACES_EXPORTER'] = 'none'
os.environ['OTEL_LOGS_EXPORTER'] = 'none'

from openai import OpenAI

client = OpenAI(
  base_url='http://127.0.0.1:8000/guards/gibberish_guard/openai/v1',
  # Will use OPENAI_API_KEY environment variable
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": "Make up some gibberish for me please!"
    }]
)

print(response.choices[0].message.content)
print(response.guardrails['validation_passed'])