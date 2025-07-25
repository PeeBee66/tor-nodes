#!/bin/bash

# GitHub Upload Setup Script
echo "🔧 GitHub Upload Configuration Helper"
echo "===================================="
echo ""
echo "This script will help you configure automatic GitHub uploads."
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found!"
    exit 1
fi

# Prompt for GitHub repo
echo "📦 Step 1: GitHub Repository"
echo "Enter your GitHub repository (format: username/repo-name):"
echo "Example: johndoe/tor-node-data"
read -p "Repository: " GITHUB_REPO

if [ -z "$GITHUB_REPO" ]; then
    echo "❌ Repository cannot be empty!"
    exit 1
fi

# Validate repo format
if [[ ! "$GITHUB_REPO" =~ ^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$ ]]; then
    echo "❌ Invalid repository format! Use: username/repo-name"
    exit 1
fi

# Prompt for GitHub token
echo ""
echo "🔑 Step 2: GitHub Personal Access Token"
echo "You need a token with 'repo' or 'public_repo' scope."
echo "Get one from: https://github.com/settings/tokens"
echo ""
read -s -p "Enter your GitHub token: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Token cannot be empty!"
    exit 1
fi

# Prompt for upload frequency
echo ""
echo "⏰ Step 3: Upload Frequency"
echo "How often should the data be uploaded to GitHub? (in hours)"
echo "Default is 1 hour. Press Enter to keep default."
read -p "Upload frequency (hours) [1]: " UPLOAD_FREQ
UPLOAD_FREQ=${UPLOAD_FREQ:-1}

# Create a backup of docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup
echo ""
echo "✅ Created backup: docker-compose.yml.backup"

# Update docker-compose.yml
echo ""
echo "📝 Updating docker-compose.yml..."

# Use sed to update the values
sed -i "s|- UPLOAD_TO_GITHUB=.*|- UPLOAD_TO_GITHUB=true|" docker-compose.yml
sed -i "s|- GITHUB_REPO=.*|- GITHUB_REPO=$GITHUB_REPO|" docker-compose.yml
sed -i "s|- GITHUB_TOKEN=.*|- GITHUB_TOKEN=$GITHUB_TOKEN|" docker-compose.yml
sed -i "s|- GITHUB_UPLOAD_FREQ_HOURS=.*|- GITHUB_UPLOAD_FREQ_HOURS=$UPLOAD_FREQ|" docker-compose.yml

echo "✅ Configuration updated!"
echo ""
echo "📊 Summary:"
echo "  - Repository: $GITHUB_REPO"
echo "  - Upload Frequency: Every $UPLOAD_FREQ hour(s)"
echo "  - Token: ***hidden***"
echo ""
echo "🚀 Next Steps:"
echo "1. Restart the container: docker-compose up -d"
echo "2. Check logs: docker-compose logs -f tor-scraper"
echo "3. Your data will be uploaded as:"
echo "   - tor_nodes_YYYY-MM-DD.csv (daily files)"
echo "   - tor_nodes_latest.csv (always current)"
echo ""
echo "⚠️  Security Note:"
echo "Your GitHub token is now in docker-compose.yml"
echo "Consider using a .env file for production deployments."
echo ""
echo "✅ Setup complete!"