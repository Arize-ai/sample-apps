#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ .env file not found. Please run ./setup.sh first"
    exit 1
fi

# Run the Spring Boot application
./gradlew run
