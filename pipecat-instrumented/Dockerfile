FROM dailyco/pipecat-base:latest

# Copy requirements and install dependencies
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the tracing setup module (essential for Arize AX tracing)
COPY ./tracing_setup.py tracing_setup.py

# Copy the main bot file
COPY ./bot.py bot.py