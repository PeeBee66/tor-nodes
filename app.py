import os
import logging
import threading
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import json
from scraper import TorNodeScraper
from github_uploader import GitHubUploader
from opencti_importer import OpenCTIImporter
from email_notifier import EmailNotifier

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Reduce verbosity of pycti library logs
logging.getLogger('api').setLevel(logging.WARNING)
logging.getLogger('pycti').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

app = Flask(__name__)
scheduler = BackgroundScheduler()

# Global stats storage
stats = {
    'scrape_history': [],
    'github_history': [],
    'opencti_history': [],
    'node_stats': {
        'total_nodes': 0,
        'exit_nodes': 0,
        'added_nodes': 0,
        'removed_nodes': 0
    }
}

def load_stats():
    """Load stats from file if exists"""
    stats_file = '/app/data/stats.json'
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return stats

def save_stats():
    """Save stats to file"""
    stats_file = '/app/data/stats.json'
    try:
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")

def scrape_tor_nodes():
    """Scheduled task to scrape Tor nodes"""
    # Check if scraping is enabled
    if not os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true':
        logger.info("Scraping is disabled via SCRAPE_ENABLED environment variable")
        return
    
    # Check if we've scraped too recently (rate limiting protection)
    if stats.get('scrape_history'):
        try:
            last_scrape_time = datetime.fromisoformat(stats['scrape_history'][0]['timestamp'])
        except:
            # Handle old timestamp format
            last_scrape_time = stats['scrape_history'][0]['timestamp']
            if isinstance(last_scrape_time, str):
                last_scrape_time = datetime.fromisoformat(last_scrape_time)
        
        time_since_last = datetime.now() - last_scrape_time
        
        # Don't scrape if less than 35 minutes since last attempt (5 min buffer)
        if time_since_last.total_seconds() < 2100:  # 35 minutes
            logger.info(f"Skipping scrape - only {time_since_last.total_seconds()/60:.1f} minutes since last attempt")
            return
    
    scraper = TorNodeScraper(csv_file='/app/data/tor_nodes.csv')
    start_time = datetime.now()
    
    try:
        result = scraper.run()
        
        stats['scrape_history'].insert(0, {
            'timestamp': start_time.isoformat(),
            'status': 'success' if result['scraped'] else 'skipped',
            'message': result.get('message', ''),
            'nodes_total': result.get('total_nodes', 0),
            'nodes_exit': result.get('exit_nodes', 0),
            'nodes_added': result.get('added_nodes', 0),
            'nodes_removed': result.get('removed_nodes', 0)
        })
        
        # Update current stats
        if result['scraped']:
            stats['node_stats'].update({
                'total_nodes': result.get('total_nodes', 0),
                'exit_nodes': result.get('exit_nodes', 0),
                'added_nodes': result.get('added_nodes', 0),
                'removed_nodes': result.get('removed_nodes', 0)
            })
        
        # Keep only last 100 entries
        stats['scrape_history'] = stats['scrape_history'][:100]
        save_stats()
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        stats['scrape_history'].insert(0, {
            'timestamp': start_time.isoformat(),
            'status': 'error',
            'message': str(e)
        })
        stats['scrape_history'] = stats['scrape_history'][:100]
        save_stats()

def upload_to_github():
    """Scheduled task to upload to GitHub"""
    if not os.getenv('UPLOAD_TO_GITHUB', 'false').lower() == 'true':
        return
    
    uploader = GitHubUploader()
    start_time = datetime.now()
    
    try:
        result = uploader.upload()
        stats['github_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success' if result['success'] else 'error',
            'message': result.get('message', '')
        })
        stats['github_history'] = stats['github_history'][:100]
        save_stats()
    except Exception as e:
        logger.error(f"GitHub upload failed: {e}")
        stats['github_history'].insert(0, {
            'timestamp': start_time,
            'status': 'error',
            'message': str(e)
        })
        stats['github_history'] = stats['github_history'][:100]
        save_stats()

def upload_to_opencti():
    """Scheduled task to upload to OpenCTI"""
    if not os.getenv('UPLOAD_TO_OPENCTI', 'false').lower() == 'true':
        logger.info("OpenCTI upload skipped - UPLOAD_TO_OPENCTI is disabled")
        return
    
    logger.info("🔄 Initiating scheduled OpenCTI import...")
    importer = OpenCTIImporter()
    start_time = datetime.now()
    
    try:
        result = importer.import_nodes()
        
        # Log the result summary
        if result['success']:
            logger.info(f"✅ Scheduled OpenCTI import completed successfully: {result.get('message', '')}")
        else:
            logger.error(f"❌ Scheduled OpenCTI import failed: {result.get('message', '')}")
        
        stats['opencti_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success' if result['success'] else 'error',
            'message': result.get('message', ''),
            'imported': result.get('imported', 0)
        })
        stats['opencti_history'] = stats['opencti_history'][:100]
        save_stats()
    except Exception as e:
        logger.error(f"❌ OpenCTI import failed with exception: {e}")
        stats['opencti_history'].insert(0, {
            'timestamp': start_time,
            'status': 'error',
            'message': str(e)
        })
        stats['opencti_history'] = stats['opencti_history'][:100]
        save_stats()

def force_upload_to_opencti_background():
    """Forced OpenCTI import task (for manual triggers) - API test already done"""
    logger.info("📋 [FORCED] IMPORT JOB STARTED: Beginning background import process...")
    importer = OpenCTIImporter()
    start_time = datetime.now()
    
    try:
        # Skip the API test in importer since we already did it
        result = importer.import_nodes()
        
        # Log the result summary
        if result['success']:
            logger.info(f"✅ [FORCED] OpenCTI import completed successfully: {result.get('message', '')}")
        else:
            logger.error(f"❌ [FORCED] OpenCTI import failed: {result.get('message', '')}")
        
        stats['opencti_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success' if result['success'] else 'error',
            'message': f"[FORCED] {result.get('message', '')}",
            'imported': result.get('imported', 0),
            'forced': True
        })
        stats['opencti_history'] = stats['opencti_history'][:100]
        save_stats()
    except Exception as e:
        logger.error(f"❌ [FORCED] OpenCTI import failed with exception: {e}")
        stats['opencti_history'].insert(0, {
            'timestamp': start_time,
            'status': 'error',
            'message': f"[FORCED] {str(e)}",
            'forced': True
        })
        stats['opencti_history'] = stats['opencti_history'][:100]
        save_stats()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """API endpoint for stats"""
    # Add configuration status to stats
    email_settings = load_email_settings()
    config_status = {
        'scrape_enabled': os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true',
        'scrape_frequency_hours': int(os.getenv('TOR_SCRAPE_FREQUENCY_HOURS', '1')),
        'github_upload_enabled': os.getenv('UPLOAD_TO_GITHUB', 'false').lower() == 'true',
        'github_upload_frequency_hours': int(os.getenv('GITHUB_UPLOAD_FREQ_HOURS', '1')),
        'opencti_upload_enabled': os.getenv('UPLOAD_TO_OPENCTI', 'false').lower() == 'true',
        'opencti_upload_frequency_hours': int(os.getenv('OPENCTI_UPLOAD_FREQ_HOURS', '24')),
        'email_enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
        'email_settings': email_settings,
        'email_config': {
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER', ''),
            'smtp_port': os.getenv('EMAIL_SMTP_PORT', ''),
            'username': os.getenv('EMAIL_USERNAME', ''),
            'from_email': os.getenv('EMAIL_FROM', ''),
            'to_email': os.getenv('EMAIL_TO', '')
        }
    }
    
    response_data = dict(stats)
    response_data['config'] = config_status
    return jsonify(response_data)

@app.route('/api/nodes')
def get_nodes():
    """API endpoint for node data"""
    try:
        import pandas as pd
        df = pd.read_csv('/app/data/tor_nodes.csv')
        # Replace NaN values with empty strings for better JSON serialization
        df = df.fillna('')
        return jsonify({
            'nodes': df.to_dict('records'),
            'total': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/force-scrape', methods=['POST'])
def force_scrape():
    """API endpoint to force scraping (for testing)"""
    try:
        scraper = TorNodeScraper(csv_file='/app/data/tor_nodes.csv')
        start_time = datetime.now()
        
        result = scraper.force_scrape()
        
        # Update stats
        stats['scrape_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success' if result['scraped'] else 'error',
            'message': f"[FORCED] {result.get('message', '')}",
            'nodes_total': result.get('total_nodes', 0),
            'nodes_exit': result.get('exit_nodes', 0),
            'nodes_added': result.get('new_nodes', 0),
            'nodes_removed': result.get('removed_nodes', 0),
            'forced': True
        })
        
        # Update current stats if successful
        if result['scraped']:
            stats['node_stats'].update({
                'total_nodes': result.get('total_nodes', 0),
                'exit_nodes': result.get('exit_nodes', 0),
                'added_nodes': result.get('new_nodes', 0),
                'removed_nodes': result.get('removed_nodes', 0)
            })
        
        # Keep only last 100 entries
        stats['scrape_history'] = stats['scrape_history'][:100]
        save_stats()
        
        return jsonify({
            'success': result['scraped'],
            'message': result.get('message', ''),
            'stats': result
        })
        
    except Exception as e:
        logger.error(f"Force scrape API failed: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/force-upload-github', methods=['POST'])
def force_upload_github():
    """API endpoint to force GitHub upload (for testing)"""
    if not os.getenv('UPLOAD_TO_GITHUB', 'false').lower() == 'true':
        return jsonify({
            'success': False,
            'message': 'GitHub upload is not enabled. Please configure UPLOAD_TO_GITHUB=true'
        }), 400
    
    try:
        uploader = GitHubUploader()
        start_time = datetime.now()
        
        # Check if CSV file exists
        if not os.path.exists('/app/data/tor_nodes.csv'):
            return jsonify({
                'success': False,
                'message': 'No data to upload. Please run a scrape first.'
            }), 400
        
        result = uploader.upload()
        
        # Update stats
        stats['github_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success' if result['success'] else 'error',
            'message': f"[FORCED] {result.get('message', '')}",
            'forced': True
        })
        stats['github_history'] = stats['github_history'][:100]
        save_stats()
        
        return jsonify({
            'success': result['success'],
            'message': result.get('message', '')
        })
        
    except Exception as e:
        logger.error(f"Force GitHub upload failed: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/force-upload-opencti', methods=['POST'])
def force_upload_opencti():
    """API endpoint to force OpenCTI import (for testing)"""
    if not os.getenv('UPLOAD_TO_OPENCTI', 'false').lower() == 'true':
        return jsonify({
            'success': False,
            'message': 'OpenCTI import is not enabled. Please configure UPLOAD_TO_OPENCTI=true'
        }), 400
    
    try:
        # Check if CSV file exists
        if not os.path.exists('/app/data/tor_nodes.csv'):
            return jsonify({
                'success': False,
                'message': 'No data to import. Please run a scrape first.'
            }), 400
        
        # Count nodes to give user an estimate
        import pandas as pd
        df = pd.read_csv('/app/data/tor_nodes.csv')
        node_count = len(df)
        
        # Test OpenCTI API availability FIRST before starting background thread
        logger.info("🔍 [FORCED] Testing OpenCTI API connectivity...")
        try:
            import requests
            api_url = os.getenv('OPENCTI_URL', 'http://localhost:4000')
            api_key = os.getenv('OPENCTI_API_KEY', '')
            api_health_url = f"{api_url}/graphql"
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Simple connectivity test with timeout
            response = requests.post(
                api_health_url,
                json={"query": "{ __typename }"},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [FORCED] API Test: SUCCESSFUL - OpenCTI API is available at {api_url}")
            else:
                logger.error(f"❌ [FORCED] API Test: FAILED - OpenCTI API returned status code {response.status_code}")
                # Add failed API test to history
                stats['opencti_history'].insert(0, {
                    'timestamp': datetime.now(),
                    'status': 'error',
                    'message': f"[FORCED] ❌ API Test Failed - HTTP {response.status_code}",
                    'imported': 0,
                    'forced': True
                })
                save_stats()
                return jsonify({
                    'success': False,
                    'message': f'OpenCTI API test failed - HTTP {response.status_code}. Cannot proceed with import.'
                }), 400
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ [FORCED] API Test: FAILED - Connection timeout to {api_url}")
            # Add failed API test to history
            stats['opencti_history'].insert(0, {
                'timestamp': datetime.now(),
                'status': 'error',
                'message': f"[FORCED] ❌ API Test Failed - Connection timeout",
                'imported': 0,
                'forced': True
            })
            save_stats()
            return jsonify({
                'success': False,
                'message': f'OpenCTI API connection timeout to {api_url}. Cannot proceed with import.'
            }), 400
        except Exception as e:
            logger.error(f"❌ [FORCED] API Test: FAILED - {str(e)}")
            # Add failed API test to history
            stats['opencti_history'].insert(0, {
                'timestamp': datetime.now(),
                'status': 'error',
                'message': f"[FORCED] ❌ API Test Failed - {str(e)}",
                'imported': 0,
                'forced': True
            })
            save_stats()
            return jsonify({
                'success': False,
                'message': f'OpenCTI API connectivity failed: {str(e)}. Cannot proceed with import.'
            }), 400
        
        # API test passed, start the import in the background
        logger.info(f"🚀 [FORCED] API test successful - Starting import job for {node_count} entries...")
        
        # Add success entry showing API test passed and job started
        start_time = datetime.now()
        stats['opencti_history'].insert(0, {
            'timestamp': start_time,
            'status': 'success',
            'message': f"[FORCED] ✅ API Test Successful - Import job started for {node_count} entries",
            'imported': 0,
            'forced': True
        })
        save_stats()
        
        # Start import in background - fire and forget
        import_thread = threading.Thread(target=force_upload_to_opencti_background)
        import_thread.daemon = True
        import_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'OpenCTI API test passed! Import job started for {node_count} nodes.',
        })
        
    except Exception as e:
        logger.error(f"Force OpenCTI import failed: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/email-settings', methods=['POST'])
def save_email_settings():
    """API endpoint to save email notification settings"""
    try:
        settings = request.json
        
        # Save email settings to a file for persistence
        email_settings_file = '/app/data/email_settings.json'
        with open(email_settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        logger.info(f"Email settings saved: {settings}")
        
        return jsonify({
            'success': True,
            'message': 'Email settings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to save email settings: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/test-email', methods=['POST'])
def send_test_email():
    """API endpoint to send a test email"""
    if not os.getenv('EMAIL_ENABLED', 'false').lower() == 'true':
        return jsonify({
            'success': False,
            'message': 'Email notifications are not enabled. Please configure EMAIL_ENABLED=true in docker-compose.yml'
        }), 400
    
    try:
        from email_notifier import EmailNotifier
        notifier = EmailNotifier()
        
        # Check if this is a summary test or simple test
        test_type = request.json.get('type', 'simple') if request.json else 'simple'
        
        if test_type == 'summary':
            # Send a real summary email to test checkbox selections
            result = notifier.send_summary(stats, force=True)
            message = 'Test summary email sent! This shows how your weekly report will look based on your checkbox selections.'
        else:
            # Create simple test email content
            test_stats = {
                'node_stats': {
                    'total_nodes': stats.get('node_stats', {}).get('total_nodes', 0),
                    'exit_nodes': stats.get('node_stats', {}).get('exit_nodes', 0)
                },
                'test': True
            }
            result = notifier.send_summary(test_stats, force=True)
            message = 'Test email sent successfully! Check your inbox.'
        
        if result:
            logger.info(f"Test email sent successfully (type: {test_type})")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email - check logs for details'
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def load_email_settings():
    """Load email settings from file"""
    email_settings_file = '/app/data/email_settings.json'
    default_settings = {
        'enabled': False,
        'includeNodeStats': True,
        'includeScrapeHistory': True,
        'includeGithubHistory': False,
        'includeOpenctiHistory': False,
        'includeErrors': True,
        'includeSystemHealth': False
    }
    
    if os.path.exists(email_settings_file):
        try:
            with open(email_settings_file, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return default_settings

def send_email_summary():
    """Send email summary if enabled"""
    notifier = EmailNotifier()
    notifier.send_summary(stats)

def setup_schedulers():
    """Configure and start schedulers"""
    global stats
    stats = load_stats()
    
    # Schedule scraping (only if enabled)
    if os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true':
        scrape_hours = int(os.getenv('TOR_SCRAPE_FREQUENCY_HOURS', '1'))
        scheduler.add_job(
            scrape_tor_nodes,
            'interval',
            hours=scrape_hours,
            id='scrape_tor',
            replace_existing=True
        )
        logger.info(f"Scraping scheduled every {scrape_hours} hour(s)")
    else:
        logger.info("Scraping is disabled via SCRAPE_ENABLED environment variable")
    
    # Schedule GitHub upload
    if os.getenv('UPLOAD_TO_GITHUB', 'false').lower() == 'true':
        github_hours = int(os.getenv('GITHUB_UPLOAD_FREQ_HOURS', '1'))
        scheduler.add_job(
            upload_to_github,
            'interval',
            hours=github_hours,
            id='github_upload',
            replace_existing=True
        )
    
    # Schedule OpenCTI import
    if os.getenv('UPLOAD_TO_OPENCTI', 'false').lower() == 'true':
        opencti_hours = int(os.getenv('OPENCTI_UPLOAD_FREQ_HOURS', '1'))
        scheduler.add_job(
            upload_to_opencti,
            'interval',
            hours=opencti_hours,
            id='opencti_import',
            replace_existing=True
        )
    
    # Schedule email notifications
    if os.getenv('EMAIL_ENABLED', 'false').lower() == 'true':
        # Check every hour if email should be sent
        scheduler.add_job(
            send_email_summary,
            'interval',
            hours=1,
            id='email_notification',
            replace_existing=True
        )
    
    scheduler.start()
    
    # Run initial scrape (only if enabled)
    if os.getenv('SCRAPE_ENABLED', 'true').lower() == 'true':
        scrape_tor_nodes()

if __name__ == '__main__':
    setup_schedulers()
    app.run(host='0.0.0.0', port=5002, debug=False)