#!/usr/bin/env python3
"""
Debug script to test the node table display
"""
import requests
import json

def test_node_table():
    print("🔍 Debugging Node Table Display")
    print("=" * 50)
    
    # Test API endpoint
    try:
        response = requests.get("http://localhost:5002/api/nodes")
        data = response.json()
        
        print(f"✅ API Response Status: {response.status_code}")
        print(f"📊 Total Nodes: {data.get('total', 0)}")
        
        if data.get('nodes'):
            # Check first few nodes
            print("\n📋 Sample Node Data:")
            for i, node in enumerate(data['nodes'][:3]):
                print(f"\nNode {i+1}:")
                print(f"  IP: {node.get('IP', 'N/A')}")
                print(f"  IsExit: '{node.get('IsExit', '')}' (Type: {type(node.get('IsExit')).__name__})")
                print(f"  Name: {node.get('Name', 'N/A')}")
                print(f"  Flags: {node.get('Flags', 'N/A')}")
            
            # Check for any null values
            null_count = 0
            for node in data['nodes']:
                for key, value in node.items():
                    if value is None:
                        null_count += 1
                        print(f"\n⚠️  Found null value in node {node.get('IP', 'Unknown')} for field: {key}")
            
            if null_count == 0:
                print("\n✅ No null values found in node data")
            else:
                print(f"\n⚠️  Found {null_count} null values total")
                
        else:
            print("❌ No nodes returned from API")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
    
    print("\n💡 To view the web interface:")
    print("   1. Open http://localhost:5002 in your browser")
    print("   2. Click on the 'Node List' tab")
    print("   3. Check browser console (F12) for any JavaScript errors")
    print("\n   If the table is still not showing, try:")
    print("   - Hard refresh (Ctrl+F5 or Cmd+Shift+R)")
    print("   - Clear browser cache")
    print("   - Try a different browser")

if __name__ == "__main__":
    test_node_table()