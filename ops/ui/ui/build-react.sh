#!/bin/bash

# Build script for React Telemetry Dashboard
# This script builds the React app and copies it to the appropriate location

echo "🚀 Building React Telemetry Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the application
echo "🔨 Building application..."
npm run build

# Copy built files to the main directory
echo "📁 Copying built files..."
cp -r dist/* ../

echo "✅ React dashboard built successfully!"
echo "🌐 Open http://localhost to view the new dashboard"
