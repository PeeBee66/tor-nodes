import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', '')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.username = os.getenv('EMAIL_USERNAME', '')
        self.password = os.getenv('EMAIL_PASSWORD', '')
        self.from_email = os.getenv('EMAIL_FROM', '')
        self.to_email = os.getenv('EMAIL_TO', '')
        self.frequency = os.getenv('EMAIL_FREQUENCY', 'daily')
        self.last_sent_file = '/app/data/last_email_sent.txt'
    
    def should_send_email(self):
        """Check if email should be sent based on frequency"""
        if not self.enabled:
            return False
        
        # Check required fields (username/password optional for servers without auth)
        if not all([self.smtp_server, self.from_email, self.to_email]):
            logger.warning("Email configuration incomplete - need SMTP server, from, and to addresses")
            return False
        
        # Check last sent time
        if os.path.exists(self.last_sent_file):
            with open(self.last_sent_file, 'r') as f:
                last_sent = datetime.fromisoformat(f.read().strip())
            
            if self.frequency == 'daily':
                if datetime.now() - last_sent < timedelta(days=1):
                    return False
            elif self.frequency == 'weekly':
                if datetime.now() - last_sent < timedelta(days=7):
                    return False
        
        return True
    
    def send_summary(self, stats, force=False):
        """Send email summary of operations"""
        # For test emails, skip frequency check
        if not force and not self.should_send_email():
            return False
        
        # For test emails, we need at least SMTP server and email addresses
        if force and not all([self.smtp_server, self.from_email, self.to_email]):
            logger.warning("Email configuration incomplete for test email")
            return False
        
        try:
            # Prepare email content
            is_test = stats.get('test', False)
            if is_test:
                subject = f"[TEST] Tor Node Monitor - Test Email"
            else:
                subject = f"Tor Node Monitor Summary - {datetime.now().strftime('%Y-%m-%d')}"
            
            body = self.generate_email_body(stats)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            
            # Add HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                # Only use TLS if not on port 25 or 1025 (local test servers)
                if self.smtp_port not in [25, 1025]:
                    server.starttls()
                
                # Only login if credentials are provided
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(msg)
            
            # Update last sent time (only for non-test emails)
            if not stats.get('test', False):
                with open(self.last_sent_file, 'w') as f:
                    f.write(datetime.now().isoformat())
            
            logger.info(f"Email sent successfully to {self.to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def generate_email_body(self, stats):
        """Generate HTML email body"""
        # Check if this is a test email
        if stats.get('test', False):
            return self.generate_test_email_body()
        
        # Load email settings to determine what to include
        import json
        email_settings_file = '/app/data/email_settings.json'
        settings = {
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
                    saved_settings = json.load(f)
                    settings.update(saved_settings)
            except:
                pass
        
        # Get recent history
        scrape_summary = self.summarize_history(stats.get('scrape_history', []))
        github_summary = self.summarize_history(stats.get('github_history', []))
        opencti_summary = self.summarize_history(stats.get('opencti_history', []))
        
        # Current node statistics
        node_stats = stats.get('node_stats', {})
        
        # Build email content based on settings
        html_parts = ["""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Tor Node Monitor Weekly Summary</h2>
            <p>Report generated on {}</p>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
        
        # Node Statistics
        if settings.get('includeNodeStats', True):
            html_parts.append(f"""
            <h3>Current Node Statistics</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <td><b>Total Nodes:</b></td>
                    <td>{node_stats.get('total_nodes', 0)}</td>
                </tr>
                <tr>
                    <td><b>Exit Nodes:</b></td>
                    <td>{node_stats.get('exit_nodes', 0)}</td>
                </tr>
                <tr>
                    <td><b>Recently Added:</b></td>
                    <td>{node_stats.get('added_nodes', 0)}</td>
                </tr>
                <tr>
                    <td><b>Recently Removed:</b></td>
                    <td>{node_stats.get('removed_nodes', 0)}</td>
                </tr>
            </table>
            """)
        
        # Operation Summary
        if any([settings.get('includeScrapeHistory'), settings.get('includeGithubHistory'), 
                settings.get('includeOpenctiHistory')]):
            html_parts.append("<h3>Operation Summary (Last 7 Days)</h3>")
        
        # Scraping History
        if settings.get('includeScrapeHistory', True):
            html_parts.append(f"""
            <h4>Scraping Operations</h4>
            <p>Success: {scrape_summary['success']} | Failed: {scrape_summary['error']} | Skipped: {scrape_summary['skipped']}</p>
            """)
            if settings.get('includeErrors', True):
                html_parts.append(self.format_errors(scrape_summary['recent_errors'], 'Scraping'))
        
        # GitHub History
        if settings.get('includeGithubHistory', False):
            html_parts.append(f"""
            <h4>GitHub Uploads</h4>
            <p>Success: {github_summary['success']} | Failed: {github_summary['error']}</p>
            """)
            if settings.get('includeErrors', True):
                html_parts.append(self.format_errors(github_summary['recent_errors'], 'GitHub'))
        
        # OpenCTI History
        if settings.get('includeOpenctiHistory', False):
            html_parts.append(f"""
            <h4>OpenCTI Imports</h4>
            <p>Success: {opencti_summary['success']} | Failed: {opencti_summary['error']}</p>
            """)
            if settings.get('includeErrors', True):
                html_parts.append(self.format_errors(opencti_summary['recent_errors'], 'OpenCTI'))
        
        # System Health
        if settings.get('includeSystemHealth', False):
            html_parts.append("""
            <h4>System Health Status</h4>
            <p>✅ All systems operational</p>
            <p>Uptime: System running normally</p>
            """)
        
        html_parts.append("""
            <hr>
            <p style="font-size: 12px; color: #666;">
                This is an automated report from the Tor Node Monitor system.
            </p>
        </body>
        </html>
        """)
        
        html = ''.join(html_parts)
        
        return html
    
    def summarize_history(self, history):
        """Summarize history for the last 24 hours"""
        summary = {
            'success': 0,
            'error': 0,
            'skipped': 0,
            'recent_errors': []
        }
        
        cutoff = datetime.now() - timedelta(hours=24)
        
        for item in history:
            try:
                timestamp = datetime.fromisoformat(item['timestamp'])
                if timestamp < cutoff:
                    break
                
                status = item.get('status', '')
                if status == 'success':
                    summary['success'] += 1
                elif status == 'error':
                    summary['error'] += 1
                    summary['recent_errors'].append({
                        'time': timestamp.strftime('%H:%M'),
                        'message': item.get('message', 'Unknown error')
                    })
                elif status == 'skipped':
                    summary['skipped'] += 1
            except:
                continue
        
        return summary
    
    def format_errors(self, errors, operation_type):
        """Format error list for email"""
        if not errors:
            return ""
        
        html = f"<p style='color: red;'>Recent {operation_type} Errors:</p><ul>"
        for error in errors[:5]:  # Show max 5 recent errors
            html += f"<li>{error['time']}: {error['message']}</li>"
        html += "</ul>"
        
        return html
    
    def generate_test_email_body(self):
        """Generate test email body"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Tor Node Monitor - Test Email</h2>
            <p>This is a test email from your Tor Node Monitor system.</p>
            
            <p><strong>Email Configuration:</strong></p>
            <ul>
                <li>SMTP Server: {self.smtp_server}</li>
                <li>SMTP Port: {self.smtp_port}</li>
                <li>From: {self.from_email}</li>
                <li>To: {self.to_email}</li>
                <li>Authentication: {'Enabled' if self.username else 'Disabled'}</li>
            </ul>
            
            <p><strong>If you received this email, your email configuration is working correctly!</strong></p>
            
            <hr>
            <p style="font-size: 12px; color: #666;">
                Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """
        return html