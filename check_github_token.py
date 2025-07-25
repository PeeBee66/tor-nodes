#!/usr/bin/env python3
"""
GitHub Token Permission Checker
"""
import requests
import os

def check_github_token():
    token = os.getenv('GITHUB_TOKEN', '')
    repo = os.getenv('GITHUB_REPO', '')
    
    if not token:
        print("❌ No GitHub token found")
        return False
        
    if not repo:
        print("❌ No GitHub repository configured")  
        return False
    
    print(f"🔍 Checking GitHub token permissions for {repo}")
    print("=" * 60)
    
    # Support both classic and fine-grained personal access tokens
    if token.startswith('github_pat_'):
        auth_header = f'Bearer {token}'
    else:
        auth_header = f'token {token}'
        
    headers = {
        'Authorization': auth_header,
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Check token info
    try:
        response = requests.get('https://api.github.com/user', headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Token is valid for user: {user_info.get('login', 'Unknown')}")
        else:
            print(f"❌ Token validation failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        return False
    
    # Check repository access
    try:
        response = requests.get(f'https://api.github.com/repos/{repo}', headers=headers)
        if response.status_code == 200:
            repo_info = response.json()
            print(f"✅ Repository accessible: {repo_info.get('full_name')}")
            print(f"   Private: {repo_info.get('private', False)}")
            print(f"   Permissions: {repo_info.get('permissions', {})}")
        else:
            print(f"❌ Repository access failed: {response.status_code}")
            if response.status_code == 404:
                print("   Repository not found or no access")
            return False
    except Exception as e:
        print(f"❌ Error checking repository: {e}")
        return False
    
    # Check if we can create/update files
    try:
        # Try to get repository contents to check write access
        response = requests.get(f'https://api.github.com/repos/{repo}/contents/', headers=headers)
        if response.status_code == 200:
            print("✅ Can read repository contents")
        else:
            print(f"⚠️  Cannot read repository contents: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error checking contents access: {e}")
    
    print("\n📋 Token Requirements for File Upload:")
    print("   ✅ Token must have 'repo' scope (for private repos)")
    print("   ✅ OR 'public_repo' scope (for public repos)")
    print("   ✅ Repository must exist")
    print("   ✅ Token owner must have write access to repository")
    
    return True

def show_token_instructions():
    print("\n" + "=" * 60)
    print("🔧 HOW TO FIX GITHUB TOKEN PERMISSIONS")
    print("=" * 60)
    print("\n1. 🔗 Go to: https://github.com/settings/tokens")
    print("\n2. 🗑️  Delete your current token (for security)")
    print("\n3. ➕ Click 'Generate new token' → 'Generate new token (classic)'")
    print("\n4. ⚙️  Configure the new token:")
    print("   📝 Note: 'Tor Node Scraper - Contents Access'")
    print("   📅 Expiration: 90 days (or your preference)")
    print("   🔐 Scopes - Check ONE of these:")
    print("      ✅ 'repo' (if your repository is private)")
    print("      ✅ 'public_repo' (if your repository is public)")
    print("\n5. 🔄 Update docker-compose.yml with the new token")
    print("\n6. 🔄 Restart: docker-compose restart")
    print("\n⚠️  IMPORTANT: Make sure PeeBee66/tor-nodes repository exists!")
    print("   Create it at: https://github.com/new")

if __name__ == "__main__":
    success = check_github_token()
    if not success:
        show_token_instructions()