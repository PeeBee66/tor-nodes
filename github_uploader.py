import os
import requests
import base64
import logging
from datetime import datetime
import certifi
import ssl

# Configure requests to use certifi's certificates
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()

logger = logging.getLogger(__name__)

class GitHubUploader:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN', '')
        self.repo = os.getenv('GITHUB_REPO', '')  # format: owner/repo
        self.csv_file = '/app/data/tor_nodes.csv'
        self.api_base = 'https://api.github.com'
        
        if not self.token or not self.repo:
            raise ValueError("GitHub token and repository must be configured")
        
        # Create session with custom SSL context
        self.session = requests.Session()
        # Try to work around SSL issues
        self.session.verify = True
    
    def get_headers(self):
        """Get GitHub API headers"""
        # Support both classic and fine-grained personal access tokens
        if self.token.startswith('github_pat_'):
            # Fine-grained personal access token
            auth_header = f'Bearer {self.token}'
        else:
            # Classic personal access token
            auth_header = f'token {self.token}'
            
        return {
            'Authorization': auth_header,
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_file_sha(self, path):
        """Get the SHA of existing file if it exists"""
        url = f'{self.api_base}/repos/{self.repo}/contents/{path}'
        response = self.session.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()['sha']
        return None
    
    def create_ip_only_csv(self):
        """Create IP-only CSV file from the main CSV"""
        try:
            import pandas as pd
            
            # Read the main CSV
            df = pd.read_csv(self.csv_file)
            
            # Create IP-only dataframe (just the IP column)
            ip_only_df = df[['IP']].copy()
            
            # Save IP-only CSV
            ip_only_path = '/app/data/tor_nodes_IP_only.csv'
            ip_only_df.to_csv(ip_only_path, index=False)
            
            return ip_only_path
            
        except Exception as e:
            logger.error(f"Failed to create IP-only CSV: {e}")
            return None

    def upload_file(self, file_path, github_filename, commit_message):
        """Upload a single file to GitHub"""
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': f'File not found: {file_path}'
                }
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Encode content to base64
            encoded_content = base64.b64encode(content).decode('utf-8')
            
            # Get existing file SHA if updating
            sha = self.get_file_sha(github_filename)
            
            # Prepare commit data
            data = {
                'message': commit_message,
                'content': encoded_content,
                'branch': 'main'
            }
            
            if sha:
                data['sha'] = sha
            
            # Upload file
            url = f'{self.api_base}/repos/{self.repo}/contents/{github_filename}'
            response = self.session.put(url, json=data, headers=self.get_headers())
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded {github_filename} to GitHub")
                return {
                    'success': True,
                    'message': f'Successfully uploaded {github_filename}'
                }
            else:
                return {
                    'success': False,
                    'message': f'Upload failed for {github_filename}: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            logger.error(f"Upload error for {github_filename}: {e}")
            return {
                'success': False,
                'message': str(e)
            }

    def upload(self):
        """Upload only tor_nodes_latest.csv and tor_nodes_IP_only.csv to GitHub"""
        try:
            # Check if main CSV file exists
            if not os.path.exists(self.csv_file):
                return {
                    'success': False,
                    'message': 'Main CSV file not found'
                }
            
            today = datetime.now().strftime('%Y-%m-%d')
            results = []
            upload_success = True
            
            # 1. Upload tor_nodes_latest.csv (copy of main CSV)
            latest_result = self.upload_file(
                self.csv_file, 
                'tor_nodes_latest.csv',
                f'Update latest Tor nodes data - {today}'
            )
            results.append(latest_result['message'])
            if not latest_result['success']:
                upload_success = False
            
            # 2. Create and upload tor_nodes_IP_only.csv
            ip_only_path = self.create_ip_only_csv()
            if ip_only_path:
                ip_only_result = self.upload_file(
                    ip_only_path,
                    'tor_nodes_IP_only.csv', 
                    f'Update IP-only Tor nodes list - {today}'
                )
                results.append(ip_only_result['message'])
                if not ip_only_result['success']:
                    upload_success = False
            else:
                results.append('Failed to create IP-only CSV')
                upload_success = False
            
            return {
                'success': upload_success,
                'message': ' | '.join(results)
            }
                
        except Exception as e:
            logger.error(f"GitHub upload error: {e}")
            return {
                'success': False,
                'message': str(e)
            }