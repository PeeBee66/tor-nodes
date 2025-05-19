#!/usr/bin/env python3
import csv
import logging
import os
import sys
from pathlib import Path
import urllib3
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Check for pycti and install if needed
try:
    from pycti import OpenCTIApiClient
except ImportError:
    logger.error("pycti library not found. Please install with: pip install pycti")
    sys.exit(1)

# API Configuration - using .180 server
API_URL = "http://172.21.32.180:4000/"
API_KEY = "81d704bc-d5d8-482f-b349-ccb972b6d423"

def get_or_create_tor_project(api_client):
    """Get or create the Tor Project organization and return its ID."""
    # First try to find it using direct API query
    try:
        query = """
        query TorProject {
          identities(filters: {
            mode: and,
            filters: [
              { key: "entity_type", values: ["Identity"] },
              { key: "name", values: ["Tor Project"] }
            ]
          }) {
            edges {
              node {
                id
                standard_id
                name
              }
            }
          }
        }
        """
        
        result = api_client.query(query)
        identities = result.get('data', {}).get('identities', {}).get('edges', [])
        
        if identities and len(identities) > 0:
            org = identities[0]['node']
            logger.info(f"Found existing Tor Project organization: {org['id']}")
            return org['id']
    except Exception as e:
        logger.warning(f"Error searching for organization: {e}")
    
    # Create it if not found
    try:
        organization = api_client.identity.create(
            type="Organization",
            name="Tor Project",
            description="Tor Project Organization - Author of Tor Node data"
        )
        org_id = organization.get('id')
        logger.info(f"Created new Tor Project organization with ID: {org_id}")
        return org_id
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        
        # Last resort - try direct mutation
        try:
            mutation = """
            mutation CreateTorProject {
              identityAdd(input: {
                type: "Organization",
                name: "Tor Project",
                description: "Tor Project Organization"
              }) {
                id
              }
            }
            """
            result = api_client.query(mutation)
            org_id = result.get('data', {}).get('identityAdd', {}).get('id')
            if org_id:
                logger.info(f"Created Tor Project with direct mutation: {org_id}")
                return org_id
        except Exception as e2:
            logger.error(f"All organization creation methods failed: {e2}")
            
    return None

def create_ipv4(api_client, ip, org_id):
    """Create (or update) an IPv4 observable with createdById = Tor Project."""
    try:
        observable_data = {
            'type': 'IPv4-Addr',
            'value': ip
        }
        
        # Add createdBy if we have an org_id
        params = {
            "observableData": observable_data,
            "update": True
        }
        
        if org_id:
            params["createdBy"] = org_id
            
        observable = api_client.stix_cyber_observable.create(**params)
        logger.info(f"[IPv4] Created/Updated: {ip}")
        return observable
    except Exception as e:
        logger.error(f"[IPv4] Error creating {ip}: {str(e)}")
        
        # Try without createdBy if that might be the issue
        if org_id:
            try:
                observable = api_client.stix_cyber_observable.create(
                    observableData=observable_data,
                    update=True
                )
                logger.info(f"[IPv4] Created without author: {ip}")
                return observable
            except Exception as e2:
                logger.error(f"[IPv4] Second attempt failed: {str(e2)}")
                
        return None

def create_indicator(api_client, ip_data, org_id):
    """Create (or update) an Indicator for the IP data."""
    # Decide the name based on IsExit
    exit_node_value = ip_data.get("IsExit", "").strip().lower()
    if exit_node_value in ["exitnode", "true", "yes", "1"]:
        indicator_name = f"TOR Node exit node {ip_data.get('IP')}"
    else:
        indicator_name = f"TOR Node {ip_data.get('IP')}"

    # Build a description
    description = (
        f"TOR Node Information:\n"
        f"IP: {ip_data.get('IP')}\n"
        f"IsExit: {ip_data.get('IsExit')}\n"
        f"Name: {ip_data.get('Name')}\n"
        f"OnionPort: {ip_data.get('OnionPort')}\n"
        f"DirPort: {ip_data.get('DirPort')}\n"
        f"Flags: {ip_data.get('Flags')}\n"
        f"Uptime: {ip_data.get('Uptime')}\n"
        f"Version: {ip_data.get('Version')}\n"
        f"Contact: {ip_data.get('Contact')}\n"
        f"CollectionDate: {ip_data.get('CollectionDate')}"
    )

    # Create a STIX pattern referencing the IPv4
    ip_value = ip_data.get("IP", "")
    stix_pattern = f"[ipv4-addr:value = '{ip_value}']"

    try:
        # Basic parameters
        params = {
            "name": indicator_name,
            "description": description,
            "pattern": stix_pattern,
            "pattern_type": "stix",
            "x_opencti_main_observable_type": "IPv4-Addr",
            "x_opencti_score": 75,
            "update": True
        }
        
        # Add createdBy if we have an org_id
        if org_id:
            params["createdBy"] = org_id
            
        indicator = api_client.indicator.create(**params)
        logger.info(f"[Indicator] Created/Updated: {indicator_name}")
        return indicator
    except Exception as e:
        logger.error(f"[Indicator] Error creating for IP {ip_value}: {str(e)}")
        
        # Try without createdBy
        if org_id:
            try:
                del params["createdBy"]
                indicator = api_client.indicator.create(**params)
                logger.info(f"[Indicator] Created without author: {indicator_name}")
                return indicator
            except Exception as e2:
                logger.error(f"[Indicator] Second attempt failed: {str(e2)}")
                
        # Try with minimal parameters
        try:
            indicator = api_client.indicator.create(
                name=indicator_name,
                pattern=stix_pattern,
                pattern_type="stix"
            )
            logger.info(f"[Indicator] Created with minimal params: {indicator_name}")
            return indicator
        except Exception as e3:
            logger.error(f"[Indicator] All attempts failed: {str(e3)}")
            return None

def create_relationship(api_client, indicator, ipv4, org_id):
    """Create (or update) a 'based-on' relationship between the Indicator and IPv4."""
    try:
        if "id" not in indicator or "id" not in ipv4:
            logger.error("[Relationship] Missing IDs in objects")
            return None
            
        # Basic parameters
        params = {
            "fromId": indicator["id"],
            "toId": ipv4["id"],
            "relationship_type": "based-on",
            "description": "Indicator based on IP observable",
            "update": True
        }
        
        # Add createdBy if we have an org_id
        if org_id:
            params["createdBy"] = org_id
            
        relationship = api_client.stix_core_relationship.create(**params)
        logger.info(f"[Relationship] Created for {ipv4.get('value', 'unknown')}")
        return relationship
    except Exception as e:
        logger.error(f"[Relationship] Error: {str(e)}")
        
        # Try without createdBy
        if org_id:
            try:
                del params["createdBy"]
                relationship = api_client.stix_core_relationship.create(**params)
                logger.info(f"[Relationship] Created without author")
                return relationship
            except Exception as e2:
                logger.error(f"[Relationship] Second attempt failed: {str(e2)}")
                
        return None

def main():
    # Get the directory where the script is located
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Check connection before proceeding
    try:
        logger.info(f"Connecting to OpenCTI at {API_URL}")
        # Set ssl_verify=False to ignore SSL certificate validation
        client = OpenCTIApiClient(API_URL, API_KEY, ssl_verify=False)
        # Test connection by making a simple API call
        client.identity.list(first=1)
        logger.info("Connection to OpenCTI successful")
    except Exception as e:
        logger.error(f"Failed to connect to OpenCTI: {e}")
        logger.error("Please check API_URL, API_KEY, and network connectivity")
        sys.exit(1)
        
    # Get or create the Tor Project organization
    logger.info("Getting or creating Tor Project organization")
    org_id = get_or_create_tor_project(client)
    if org_id:
        logger.info(f"Using Tor Project organization ID: {org_id}")
    else:
        logger.warning("Continuing without Tor Project organization")

    # Locate the CSV file
    csv_path = script_dir / 'tor_nodes.csv'
    if not csv_path.exists():
        logger.error(f"CSV file not found at {csv_path}")
        logger.info("Checking current directory...")
        csv_path = Path('tor_nodes.csv')
        if not csv_path.exists():
            logger.error("CSV file 'tor_nodes.csv' not found. Please provide the correct path.")
            sys.exit(1)
    
    logger.info(f"Using CSV file: {csv_path}")

    # Read the CSV & create objects
    processed = 0
    errors = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ip = row.get("IP", "").strip()
                if not ip:
                    logger.warning("Row has no IP address, skipping")
                    continue

                try:
                    # 1) Create IPv4
                    ipv4_observable = create_ipv4(client, ip, org_id)
                    if not ipv4_observable or "id" not in ipv4_observable:
                        errors += 1
                        continue

                    # 2) Create Indicator
                    indicator = create_indicator(client, row, org_id)
                    if not indicator or "id" not in indicator:
                        errors += 1
                        continue

                    # 3) Link them with a 'based-on' relationship
                    relationship = create_relationship(client, indicator, ipv4_observable, org_id)
                    if relationship:
                        processed += 1
                    else:
                        logger.warning(f"Failed to create relationship for {ip}, but continuing")
                        processed += 1
                except Exception as e:
                    logger.error(f"Error processing IP {ip}: {e}")
                    errors += 1
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    logger.info(f"Processing complete. Processed {processed} entries with {errors} errors.")

if __name__ == "__main__":
    main()
