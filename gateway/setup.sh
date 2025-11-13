#!/bin/bash

# SoundCanvas Gateway - Local Development Setup
# This script sets up the local development environment

set -e

echo "🚀 SoundCanvas Gateway Setup"
echo "=============================="

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✓ Node.js found: $(node --version)"

# Check for MySQL
if ! command -v mysql &> /dev/null; then
    echo "⚠️  MySQL client not found. You'll need MySQL running on localhost:3306"
    echo "   Or use Docker: docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=soundcanvas -e MYSQL_USER=soundcanvas -e MYSQL_PASSWORD=soundcanvas mysql:8"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and fill in your AWS credentials and database settings"
else
    echo "✓ .env file already exists"
fi

# Check if database is accessible
echo ""
echo "🔍 Checking database connection..."
if ! mysql -h localhost -u soundcanvas -psoundcanvas -e "USE soundcanvas;" &> /dev/null; then
    echo "⚠️  Could not connect to local MySQL database"
    echo "   Make sure MySQL is running and the database 'soundcanvas' exists"
    echo "   You can create it with:"
    echo "   mysql -u root -p -e \"CREATE DATABASE soundcanvas; GRANT ALL ON soundcanvas.* TO 'soundcanvas'@'localhost' IDENTIFIED BY 'soundcanvas';\""
else
    echo "✓ Database connection successful"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and configure your environment variables"
echo "  2. Start the development server: npm run dev"
echo "  3. GraphQL Playground: http://localhost:4000/graphql"
echo ""
echo "For production deployment, see: ../PHASE10_PERSON_B_IMPLEMENTATION.md"
