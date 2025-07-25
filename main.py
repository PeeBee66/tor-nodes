import requests
import csv
from datetime import date
import os
import re
import time

class TORNodeScraper:
    def __init__(self, csv_file='tor_nodes.csv'):
        self.base_url = 'https://www.dan.me.uk'
        self.details_url = 'https://www.dan.me.uk/tornodes'
        self.csv_file = csv_file
        self.data_file = 'node_data.txt'
        self.headers = ['IP', 'IsExit', 'Name', 'OnionPort', 'DirPort', 'Flags', 'Uptime', 'Version', 'Contact', 'CollectionDate']
        self.stats = {'total_nodes': 0, 'exit_nodes': 0, 'new_nodes': 0, 'updated_nodes': 0, 'detail_errors': 0}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_url(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
        return None

    def stage1_collect_all_nodes(self):
        print("\nStage 1: Collecting All Nodes")
        all_nodes_text = self.fetch_url(f'{self.base_url}/torlist/?full')
        if not all_nodes_text:
            print("Failed to collect all nodes")
            return

        all_nodes = set(re.split(r'[\n<br>]+', all_nodes_text.strip()))
        all_nodes = {ip.strip() for ip in all_nodes if ip.strip() and self.is_valid_ip(ip.strip())}
        
        existing_data = self.load_csv()
        today = date.today().isoformat()
        self.stats['total_nodes'] = len(all_nodes)

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
        self.print_stats("All Nodes Collection")

    def stage2_update_exit_nodes(self):
        print("\nStage 2: Updating Exit Nodes")
        exit_nodes_text = self.fetch_url(f'{self.base_url}/torlist/?exit')
        if not exit_nodes_text:
            print("Failed to collect exit nodes")
            return

        exit_nodes = set(re.split(r'[\n<br>]+', exit_nodes_text.strip()))
        exit_nodes = {ip.strip() for ip in exit_nodes if ip.strip() and self.is_valid_ip(ip.strip())}
        self.stats['exit_nodes'] = len(exit_nodes)

        existing_data = self.load_csv()
        for row in existing_data:
            if row.get('IP', '') in exit_nodes:
                row['IsExit'] = 'ExitNode'

        self.save_csv(existing_data)
        self.print_stats("Exit Nodes Update")

    def stage3_collect_details(self):
        print("\nStage 3: Collecting Node Details")
        details_text = self.fetch_url(self.details_url)
        if not details_text:
            print("Failed to fetch node details")
            return

        with open(self.data_file, 'w', encoding='utf-8') as f:
            f.write(details_text)
        print(f"Saved node details to {self.data_file}")

    def stage4_update_from_details(self):
        print("\nStage 4: Updating Node Details from File")
        if not os.path.exists(self.data_file):
            print(f"Detail file {self.data_file} not found")
            return

        nodes = self.load_csv()
        with open(self.data_file, 'r', encoding='utf-8') as f:
            details_text = f.read()

        start_marker = "<!-- __BEGIN_TOR_NODE_LIST__ //-->"
        start_idx = details_text.find(start_marker)
        if start_idx == -1:
            print("Could not find node data section")
            return

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
                        'Name': parts[1],
                        'OnionPort': parts[2],
                        'DirPort': parts[3],
                        'Flags': parts[4],
                        'Uptime': parts[5],
                        'Version': parts[6],
                        'Contact': parts[7] if len(parts) > 7 else ''
                    }

        for node in nodes:
            ip = node.get('IP', '')
            if ip in node_details:
                node.update(node_details[ip])
                self.stats['updated_nodes'] += 1
            else:
                self.stats['detail_errors'] += 1

        self.save_csv(nodes)
        self.print_stats("Node Details Update")

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

    def print_stats(self, stage):
        print(f"\n{stage} Statistics:")
        print(f"Total Nodes: {self.stats['total_nodes']}")
        print(f"Exit Nodes: {self.stats['exit_nodes']}")
        print(f"Updated Nodes: {self.stats['updated_nodes']}")
        print(f"Detail Errors: {self.stats['detail_errors']}")

    def run_all_stages(self):
        self.stage1_collect_all_nodes()
        time.sleep(2)
        self.stage2_update_exit_nodes()
        time.sleep(2)
        self.stage3_collect_details()
        time.sleep(2)
        self.stage4_update_from_details()

def main():
    scraper = TORNodeScraper()
    scraper.run_all_stages()

if __name__ == "__main__":
    main()