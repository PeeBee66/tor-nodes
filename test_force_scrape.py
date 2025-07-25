#!/usr/bin/env python3
"""
Quick test script to demonstrate the force scrape functionality
"""
import requests
import time
import json

def test_force_scrape():
    url = "http://localhost:5002/api/force-scrape"
    
    print("🧪 Testing Force Scrape Functionality")
    print("=" * 50)
    
    # First attempt - should work if enough time has passed
    print("1️⃣ First force scrape attempt...")
    response = requests.post(url)
    result = response.json()
    
    print(f"   Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    print(f"   Message: {result['message']}")
    
    if result['success']:
        stats = result['stats']
        print(f"   📊 Nodes: {stats.get('total_nodes', 0)} total, {stats.get('exit_nodes', 0)} exit")
    
    print()
    
    # Second attempt - should trigger rate limiting
    print("2️⃣ Immediate second attempt (should trigger rate limiting)...")
    response = requests.post(url)
    result = response.json()
    
    print(f"   Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED (Expected)'}")
    print(f"   Message: {result['message']}")
    
    if 'RATE_LIMITED' in result['message']:
        print("   🎯 Rate limiting detected correctly!")
    
    print()
    print("🌐 You can view the web interface at: http://localhost:5002")
    print("   - Navigate to the 'Scrape History' tab")
    print("   - Click the yellow 'Force Scrape (Testing)' button")
    print("   - Observe rate limiting behavior in the interface")

if __name__ == "__main__":
    try:
        test_force_scrape()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to http://localhost:5002")
        print("   Make sure the container is running with: docker-compose up -d")
    except Exception as e:
        print(f"❌ Error: {e}")