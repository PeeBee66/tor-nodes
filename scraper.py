import requests
import csv
from datetime import datetime, date
import os
import re
import time
import logging

logger = logging.getLogger(__name__)

class TorNodeScraper:
    def __init__(self, csv_file='/app/data/tor_nodes.csv'):
        self.base_url = os.getenv('TOR_SCRAPE_SITE', 'https://www.dan.me.uk')
        self.details_url = f'{self.base_url}/tornodes'
        self.csv_file = csv_file
        self.data_file = '/app/data/node_data.txt'
        self.headers = ['IP', 'IsExit', 'Name', 'OnionPort', 'DirPort', 'Flags', 'Uptime', 'Version', 'Contact', 'CollectionDate']
        self.stats = {'total_nodes': 0, 'exit_nodes': 0, 'new_nodes': 0, 'updated_nodes': 0, 'removed_nodes': 0, 'detail_errors': 0}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })


    def fetch_url(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                
                # Check for rate limiting (403 Forbidden often indicates rate limiting)
                if response.status_code == 403:
                    logger.warning("Rate limited by server (403 Forbidden) - can only fetch data every 30 minutes")
                    raise Exception("RATE_LIMITED: Server returned 403 Forbidden. You can only fetch data every 30 minutes. Please wait before trying again.")
                
                response.raise_for_status()
                
                # Check for rate limiting message in content
                content = response.text
                if "You can only fetch the data every 30 minutes" in content:
                    logger.warning("Rate limited by server - can only fetch data every 30 minutes")
                    raise Exception("RATE_LIMITED: Server allows fetching data only every 30 minutes. Please wait before trying again.")
                
                return content
            except requests.RequestException as e:
                # Don't retry if it's a rate limit error
                if "RATE_LIMITED" in str(e):
                    raise
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
        return None

    def stage1_collect_all_nodes(self):
        logger.info("Stage 1: Collecting All Nodes")
        all_nodes_text = self.fetch_url(f'{self.base_url}/torlist/?full')
        if not all_nodes_text:
            raise Exception("Failed to collect all nodes")

        all_nodes = set(re.split(r'[\n<br>]+', all_nodes_text.strip()))
        all_nodes = {ip.strip() for ip in all_nodes if ip.strip() and self.is_valid_ip(ip.strip())}
        
        existing_data = self.load_csv()
        existing_ips = {row.get('IP', '') for row in existing_data}
        
        today = date.today().isoformat()
        self.stats['total_nodes'] = len(all_nodes)
        self.stats['new_nodes'] = len(all_nodes - existing_ips)
        self.stats['removed_nodes'] = len(existing_ips - all_nodes)

        updated_data = []
        for ip in all_nodes:
            node_data = next((row for row in existing_data if row.get('IP', '') == ip), None)
            if node_data:
                node_data['CollectionDate'] = today
                updated_data.append(node_data)
            else:
                updated_data.append({
                    'IP': ip, 'IsExit': '', 'Name': '', 'OnionPort': '', 'DirPort': '', 
                    'Flags': '', 'Uptime': '', 'Version': '', 'Contact': '', 'CollectionDate': today
                })

        self.save_csv(updated_data)
        logger.info(f"Stage 1 complete: {self.stats['total_nodes']} nodes")

    def stage2_update_exit_nodes(self):
        logger.info("Stage 2: Updating Exit Nodes")
        exit_nodes_text = self.fetch_url(f'{self.base_url}/torlist/?exit')
        if not exit_nodes_text:
            raise Exception("Failed to collect exit nodes")

        exit_nodes = set(re.split(r'[\n<br>]+', exit_nodes_text.strip()))
        exit_nodes = {ip.strip() for ip in exit_nodes if ip.strip() and self.is_valid_ip(ip.strip())}
        self.stats['exit_nodes'] = len(exit_nodes)

        existing_data = self.load_csv()
        for row in existing_data:
            if row.get('IP', '') in exit_nodes:
                row['IsExit'] = 'ExitNode'
            else:
                row['IsExit'] = ''

        self.save_csv(existing_data)
        logger.info(f"Stage 2 complete: {self.stats['exit_nodes']} exit nodes")

    def stage3_collect_details(self):
        logger.info("Stage 3: Collecting Node Details")
        details_text = self.fetch_url(self.details_url)
        if not details_text:
            raise Exception("Failed to fetch node details")

        with open(self.data_file, 'w', encoding='utf-8') as f:
            f.write(details_text)
        logger.info(f"Saved node details to {self.data_file}")

    def stage4_update_from_details(self):
        logger.info("Stage 4: Updating Node Details from File")
        if not os.path.exists(self.data_file):
            raise Exception(f"Detail file {self.data_file} not found")

        nodes = self.load_csv()
        with open(self.data_file, 'r', encoding='utf-8') as f:
            details_text = f.read()

        start_marker = "<!-- __BEGIN_TOR_NODE_LIST__ //-->"
        start_idx = details_text.find(start_marker)
        if start_idx == -1:
            raise Exception("Could not find node data section")

        details_text = details_text[start_idx + len(start_marker):]
        node_lines = details_text.split('<br>')

        node_details = {}
        for line in node_lines:
            if '|' not in line:
                continue
            parts = line.strip().split('|')
            if len(parts) >= 7:
                ip = parts[0].strip()
                if self.is_valid_ip(ip):
                    node_details[ip] = {
                        'Name': parts[1].strip(),
                        'OnionPort': parts[2].strip(),
                        'DirPort': parts[3].strip(),
                        'Flags': parts[4].strip(),
                        'Uptime': parts[5].strip(),
                        'Version': parts[6].strip(),
                        'Contact': parts[7].strip() if len(parts) > 7 else ''
                    }

        for node in nodes:
            ip = node.get('IP', '')
            if ip in node_details:
                node.update(node_details[ip])
                self.stats['updated_nodes'] += 1
            else:
                self.stats['detail_errors'] += 1

        self.save_csv(nodes)
        logger.info(f"Stage 4 complete: {self.stats['updated_nodes']} nodes updated")

    def load_csv(self):
        if not os.path.exists(self.csv_file):
            return []
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames != self.headers:
                    return []
                return list(reader)
        except:
            return []

    def save_csv(self, data):
        os.makedirs(os.path.dirname(self.csv_file), exist_ok=True)
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(data)

    def is_valid_ip(self, ip):
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except:
            return False

    def run_all_stages(self):
        self.stage1_collect_all_nodes()
        time.sleep(2)
        self.stage2_update_exit_nodes()
        time.sleep(2)
        self.stage3_collect_details()
        time.sleep(2)
        self.stage4_update_from_details()
        
        return {
            'scraped': True,
            'message': 'Successfully scraped all stages',
            **self.stats
        }

    def run(self):
        """Run scraping on schedule"""
        logger.info("Scheduled scraping initiated")
        try:
            return self.run_all_stages()
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {
                'scraped': False,
                'message': f"Scraping failed: {e}",
                **self.stats
            }

    def force_scrape(self):
        """Force scraping regardless of update status (for testing)"""
        logger.info("Force scraping initiated")
        try:
            return self.run_all_stages()
        except Exception as e:
            logger.error(f"Force scraping failed: {e}")
            return {
                'scraped': False,
                'message': f"Force scraping failed: {e}",
                **self.stats
            }