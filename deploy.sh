#!/bin/bash

# Medical Chatbot Deployment Script
# This script helps you deploy the application quickly

set -e

echo "=========================================="
echo "Medical Chatbot Deployment Helper"
echo "=========================================="
echo ""

# Check if .env or SECRET.env exists
if [ ! -f "SECRET.env" ] && [ ! -f ".env" ]; then
    echo "⚠️  No environment file found!"
    echo "Please create SECRET.env with your API keys."
    echo "You can copy .env.example as a template:"
    echo ""
    echo "  cp .env.example SECRET.env"
    echo ""
    echo "Then edit SECRET.env and add your API keys."
    exit 1
fi

echo "Select deployment method:"
echo ""
echo "1. Docker Compose (Recommended - easiest)"
echo "2. Docker only"
echo "3. Local development server"
echo "4. Heroku"
echo "5. Exit"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🐳 Starting deployment with Docker Compose..."
        echo ""
        
        # Check if docker-compose is installed
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ docker-compose is not installed!"
            echo "Please install Docker and Docker Compose first."
            exit 1
        fi
        
        # Build and start
        echo "Building and starting containers..."
        docker-compose up -d --build
        
        echo ""
        echo "⏳ Waiting for application to start (30 seconds)..."
        sleep 30
        
        # Initialize database
        echo ""
        echo "📊 Initializing database..."
        curl -s http://localhost:8080/init-db > /dev/null
        echo "Database tables created."
        
        echo ""
        echo "👨‍⚕️ Populating doctors data..."
        curl -s http://localhost:8080/populate-doctors > /dev/null
        echo "Doctors data populated."
        
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        echo "🌐 Access your application at: http://localhost:8080"
        echo ""
        echo "📋 Useful commands:"
        echo "  - View logs: docker-compose logs -f"
        echo "  - Stop app: docker-compose down"
        echo "  - Restart: docker-compose restart"
        ;;
        
    2)
        echo ""
        echo "🐳 Starting deployment with Docker..."
        echo ""
        
        # Check if docker is installed
        if ! command -v docker &> /dev/null; then
            echo "❌ Docker is not installed!"
            echo "Please install Docker first."
            exit 1
        fi
        
        # Build image
        echo "Building Docker image..."
        docker build -t medical-chatbot .
        
        # Stop and remove existing container if it exists
        docker stop medical-chatbot 2>/dev/null || true
        docker rm medical-chatbot 2>/dev/null || true
        
        # Run container
        echo ""
        echo "Starting container..."
        docker run -d \
            -p 8080:8080 \
            --name medical-chatbot \
            --env-file SECRET.env \
            -v $(pwd)/instance:/app/instance \
            -v $(pwd)/saved_models:/app/saved_models \
            -v $(pwd)/data:/app/data \
            medical-chatbot
        
        echo ""
        echo "⏳ Waiting for application to start (30 seconds)..."
        sleep 30
        
        # Initialize database
        echo ""
        echo "📊 Initializing database..."
        curl -s http://localhost:8080/init-db > /dev/null
        echo "Database tables created."
        
        echo ""
        echo "👨‍⚕️ Populating doctors data..."
        curl -s http://localhost:8080/populate-doctors > /dev/null
        echo "Doctors data populated."
        
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        echo "🌐 Access your application at: http://localhost:8080"
        echo ""
        echo "📋 Useful commands:"
        echo "  - View logs: docker logs -f medical-chatbot"
        echo "  - Stop app: docker stop medical-chatbot"
        echo "  - Restart: docker restart medical-chatbot"
        ;;
        
    3)
        echo ""
        echo "🐍 Starting local development server..."
        echo ""
        
        # Check if Python is installed
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python 3 is not installed!"
            exit 1
        fi
        
        # Check if virtual environment exists
        if [ ! -d "venv" ]; then
            echo "Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate virtual environment
        echo "Activating virtual environment..."
        source venv/bin/activate
        
        # Install dependencies
        echo "Installing dependencies..."
        pip install -r requirements.txt
        
        # Run the application
        echo ""
        echo "🚀 Starting Flask development server..."
        echo ""
        python app.py
        ;;
        
    4)
        echo ""
        echo "☁️  Deploying to Heroku..."
        echo ""
        
        # Check if Heroku CLI is installed
        if ! command -v heroku &> /dev/null; then
            echo "❌ Heroku CLI is not installed!"
            echo "Install it from: https://devcenter.heroku.com/articles/heroku-cli"
            exit 1
        fi
        
        # Login to Heroku
        echo "Logging into Heroku..."
        heroku login
        
        # Ask for app name
        read -p "Enter your Heroku app name (or press Enter to generate): " app_name
        
        if [ -z "$app_name" ]; then
            heroku create
        else
            heroku create "$app_name"
        fi
        
        # Set environment variables from SECRET.env
        echo ""
        echo "Setting environment variables..."
        
        while IFS='=' read -r key value; do
            # Skip empty lines and comments
            if [[ ! -z "$key" ]] && [[ ! "$key" =~ ^# ]]; then
                # Remove any quotes from value
                value=$(echo "$value" | sed 's/"//g' | sed "s/'//g")
                if [[ ! -z "$value" ]]; then
                    echo "Setting $key..."
                    heroku config:set "$key=$value" 2>/dev/null || true
                fi
            fi
        done < SECRET.env
        
        # Deploy
        echo ""
        echo "Deploying to Heroku..."
        git push heroku main || git push heroku master
        
        # Open the app
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        heroku open
        ;;
        
    5)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
