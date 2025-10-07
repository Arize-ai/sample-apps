#!/bin/bash

# Spring AI OpenInference Example Setup Script
# This script sets up the project for standalone usage

set -e

echo "🚀 Setting up Spring AI OpenInference Example..."

# Check if Java 17+ is installed
if ! command -v java &> /dev/null; then
    echo "❌ Java is not installed. Please install Java 17 or higher."
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
if [ "$JAVA_VERSION" -lt 17 ]; then
    echo "❌ Java 17 or higher is required. Found Java $JAVA_VERSION"
    exit 1
fi

echo "✅ Java $JAVA_VERSION detected"

# Make gradlew executable
chmod +x gradlew

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        cp env.example .env
        echo "📝 Created .env file from env.example"
        echo "⚠️  Please edit .env file with your API keys before running the example"
    else
        echo "❌ env.example file not found"
        exit 1
    fi
else
    echo "✅ .env file already exists"
fi

# Test Gradle wrapper
echo "🔧 Testing Gradle wrapper..."
./gradlew --version

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: ./run.sh"
echo ""
echo "For more information, see README.md"
