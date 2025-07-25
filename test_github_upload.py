#!/usr/bin/env python3
"""
Test script for GitHub upload configuration
"""
import os
import requests
import subprocess
import time

def check_github_config():
    """Check if GitHub is configured in docker-compose.yml"""
    with open('docker-compose.yml', 'r') as f:
        content = f.read()
    
    config = {
        'enabled': 'UPLOAD_TO_GITHUB=true' in content,
        'has_repo': 'GITHUB_REPO=' in content and 'GITHUB_REPO=' not in content.split('\n'),
        'has_token': 'GITHUB_TOKEN=' in content and len([line for line in content.split('\n') if 'GITHUB_TOKEN=' in line and len(line.strip()) > 20]) > 0
    }
    
    return config

def test_github_upload():
    print("🔧 GitHub Upload Test")
    print("=" * 50)
    
    # Check configuration
    config = check_github_config()
    
    print("📋 Current Configuration:")
    print(f"   GitHub Upload Enabled: {'✅ Yes' if config['enabled'] else '❌ No'}")
    print(f"   Repository Configured: {'✅ Yes' if config['has_repo'] else '❌ No'}")
    print(f"   Token Configured: {'✅ Yes' if config['has_token'] else '❌ No'}")
    
    if not all(config.values()):
        print("\n⚠️  GitHub upload is not fully configured!")
        print("\nTo configure, edit docker-compose.yml and set:")
        print("   - UPLOAD_TO_GITHUB=true")
        print("   - GITHUB_REPO=yourusername/your-repo")
        print("   - GITHUB_TOKEN=ghp_YourTokenHere")
        print("\nThen restart: docker-compose restart")
        return
    
    print("\n🧪 Testing Force Upload...")
    
    # Test the API endpoint
    try:
        response = requests.post("http://localhost:5002/api/force-upload-github")
        result = response.json()
        
        print(f"\n📤 Upload Result:")
        print(f"   Status: {'✅ SUCCESS' if result.get('success') else '❌ FAILED'}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        if result.get('success'):
            print("\n🎉 GitHub upload successful!")
            print("   Check your repository for:")
            print(f"   - tor_nodes_{time.strftime('%Y-%m-%d')}.csv")
            print("   - tor_nodes_latest.csv")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to http://localhost:5002")
        print("   Make sure the container is running")
    except Exception as e:
        print(f"❌ Error: {e}")

def quick_config_helper():
    print("\n💡 Quick Configuration Helper")
    print("-" * 30)
    print("To quickly configure GitHub upload:")
    print("\n1. Run: ./setup_github.sh")
    print("2. Or manually edit docker-compose.yml")
    print("3. Then restart: docker-compose restart")
    print("\nNeed help? Check docs/GITHUB_UPLOAD.md")

if __name__ == "__main__":
    test_github_upload()
    
    # Show helper if not configured
    config = check_github_config()
    if not all(config.values()):
        quick_config_helper()