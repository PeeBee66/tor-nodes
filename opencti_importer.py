import csv
import logging
import os
from pycti import OpenCTIApiClient

# Configure logger to inherit from root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Reduce verbosity of pycti library logs
logging.getLogger('api').setLevel(logging.WARNING)
logging.getLogger('pycti').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class OpenCTIImporter:
    def __init__(self):
        self.api_url = os.getenv('OPENCTI_URL', 'http://localhost:4000')
        self.api_key = os.getenv('OPENCTI_API_KEY', '')
        self.csv_file = '/app/data/tor_nodes.csv'
        
        if not self.api_key:
            raise ValueError("OpenCTI API key must be configured")
        
        logger.info(f"Initializing OpenCTI connection to {self.api_url}")
        self.client = OpenCTIApiClient(self.api_url, self.api_key)
        self.organization_name = "PeeBee"
    
    def create_organization(self):
        """Create or update an Organisation named 'PeeBee'."""
        try:
            organization = self.client.identity.create(
                type="Organization",
                name=self.organization_name,
                description="PeeBee Tor node monitoring system",
                update=True
            )
            logger.info(f"Created/Updated organization: {organization}")
            return organization
        except Exception as e:
            logger.error(f"Error creating organization: {str(e)}")
            raise

    def create_ipv4(self, ip, peebee_id):
        """Create (or update) an IPv4 observable."""
        try:
            observable = self.client.stix_cyber_observable.create(
                observableData={
                    'type': 'IPv4-Addr',
                    'value': ip
                },
                createdById=peebee_id,
                update=True
            )
            logger.debug(f"Created/Updated IPv4: {observable}")
            return observable
        except Exception as e:
            logger.error(f"Error creating IPv4 {ip}: {str(e)}")
            return None

    def create_indicator(self, ip_data, peebee_id):
        """Create (or update) an Indicator for the IP data."""
        # Determine indicator name based on IsExit
        exit_node_value = ip_data.get("IsExit", "").strip().lower()
        if exit_node_value in ["exitnode", "true", "yes", "1"]:
            indicator_name = f"TOR Exit Node - {ip_data.get('IP')}"
        else:
            indicator_name = f"TOR Node - {ip_data.get('IP')}"

        # Build description
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

        # Create STIX pattern
        ip_value = ip_data.get("IP", "")
        stix_pattern = f"[ipv4-addr:value = '{ip_value}']"

        try:
            indicator = self.client.indicator.create(
                name=indicator_name,
                description=description,
                pattern=stix_pattern,
                pattern_type="stix",
                x_opencti_main_observable_type="IPv4-Addr",
                x_opencti_score=75,
                createdById=peebee_id,
                update=True
            )
            logger.debug(f"Created/Updated indicator: {indicator}")
            return indicator
        except Exception as e:
            logger.error(f"Error creating indicator for IP {ip_value}: {str(e)}")
            return None

    def create_relationship(self, indicator, ipv4, peebee_id):
        """Create (or update) a 'based-on' relationship."""
        try:
            relationship = self.client.stix_core_relationship.create(
                fromId=indicator["id"],
                toId=ipv4["id"],
                relationship_type="based-on",
                description="Indicator based on IP observable",
                createdById=peebee_id,
                update=True
            )
            logger.debug(f"Created/Updated relationship: {relationship}")
            return relationship
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            return None

    def import_nodes(self):
        """Import all nodes from CSV to OpenCTI"""
        from datetime import datetime
        import_start_time = datetime.now()
        
        logger.info("🚀 Starting OpenCTI import process...")
        logger.info(f"🌐 Target OpenCTI Server: {self.api_url}")
        logger.info(f"📅 Import started at: {import_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        try:
            # Count total rows first
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for line in f) - 1  # Subtract header
            
            logger.info(f"📊 Found {total_rows} Tor nodes to import to OpenCTI")
            
            # Test OpenCTI API availability first
            logger.info("🔍 Testing OpenCTI API connectivity...")
            try:
                # Test basic connectivity by checking if we can reach the GraphQL endpoint
                import requests
                api_health_url = f"{self.api_url}/graphql"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                # Simple connectivity test with timeout
                response = requests.post(
                    api_health_url,
                    json={"query": "{ __typename }"},
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ API Test: SUCCESSFUL - OpenCTI API is available at {self.api_url}")
                    logger.info(f"🚀 Proceeding with import job...")
                else:
                    logger.error(f"❌ API Test: FAILED - OpenCTI API returned status code {response.status_code}")
                    return {
                        'success': False,
                        'message': f'OpenCTI API not available - HTTP {response.status_code}'
                    }
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ API Test: FAILED - Connection timeout to {self.api_url}")
                return {
                    'success': False,
                    'message': f'OpenCTI API connection timeout to {self.api_url}'
                }
            except Exception as e:
                logger.error(f"❌ API Test: FAILED - {str(e)}")
                return {
                    'success': False,
                    'message': f'OpenCTI API connectivity failed: {str(e)}'
                }
            
            # Create/Update PeeBee organization - this will test connectivity
            logger.info("🏢 Testing OpenCTI connectivity and creating/updating PeeBee organization...")
            try:
                peebee_org = self.create_organization()
                if not peebee_org or "id" not in peebee_org:
                    logger.error("❌ Failed to create/find PeeBee organization")
                    return {
                        'success': False,
                        'message': 'Unable to create/find PeeBee organization'
                    }
                
                logger.info(f"✅ OpenCTI connection successful - Organization created/found")
                logger.info(f"🔗 Connected to OpenCTI server: {self.api_url}")
                peebee_id = peebee_org["id"]
                logger.info(f"✅ Using organization ID: {peebee_id}")
                
            except Exception as e:
                logger.error(f"❌ OpenCTI connection failed during organization creation: {str(e)}")
                return {
                    'success': False,
                    'message': f'OpenCTI connection failed: {str(e)}'
                }
            
            imported_count = 0
            error_count = 0
            
            # Start the import job
            logger.info(f"📋 IMPORT JOB STARTED: Processing {total_rows} entries")
            logger.info(f"📤 Starting import of {total_rows} Tor nodes to OpenCTI...")
            
            # Read CSV and create objects
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, 1):
                    ip = row.get("IP", "").strip()
                    if not ip:
                        continue
                    
                    # Log progress every 100 nodes
                    if i % 100 == 0:
                        progress_percent = (i / total_rows * 100) if total_rows > 0 else 0
                        logger.info(f"📈 OpenCTI import progress: {i}/{total_rows} nodes processed ({progress_percent:.1f}% complete, {imported_count} imported, {error_count} errors)")
                    
                    try:
                        # Create IPv4 observable
                        ipv4_observable = self.create_ipv4(ip, peebee_id)
                        if not ipv4_observable or "id" not in ipv4_observable:
                            error_count += 1
                            continue
                        
                        # Create Indicator
                        indicator = self.create_indicator(row, peebee_id)
                        if not indicator or "id" not in indicator:
                            error_count += 1
                            continue
                        
                        # Create relationship
                        self.create_relationship(indicator, ipv4_observable, peebee_id)
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing IP {ip}: {e}")
                        error_count += 1
            
            # Final summary with detailed server confirmation
            import_end_time = datetime.now()
            total_duration = import_end_time - import_start_time
            success_rate = (imported_count / total_rows * 100) if total_rows > 0 else 0
            
            # Log job completion summary
            logger.info(f"📋 IMPORT JOB COMPLETED: Processed {total_rows} entries")
            logger.info(f"🏁 OpenCTI import process completed!")
            logger.info(f"📅 Import finished at: {import_end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info(f"⏱️  Total import duration: {total_duration}")
            logger.info(f"🌐 Data successfully sent to OpenCTI server: {self.api_url}")
            
            if error_count == 0:
                logger.info(f"🎉 OpenCTI import completed successfully!")
                logger.info(f"✅ JOB SUMMARY: Successfully processed {total_rows} entries - All {imported_count} nodes imported")
                logger.info(f"✅ OpenCTI server confirmed acceptance of all {imported_count} nodes")
                logger.info(f"📊 Success rate: {success_rate:.1f}% ({imported_count}/{total_rows})")
                message = f"Successfully imported {imported_count} nodes to {self.api_url}"
            else:
                logger.info(f"⚠️  OpenCTI import completed with some errors")
                logger.info(f"📋 JOB SUMMARY: Processed {total_rows} entries - {imported_count} imported, {error_count} failed")
                logger.info(f"✅ OpenCTI server confirmed acceptance of {imported_count} nodes")
                logger.info(f"❌ OpenCTI server rejected {error_count} nodes")
                logger.info(f"📊 Success rate: {success_rate:.1f}% ({imported_count}/{total_rows})")
                message = f"Imported {imported_count} nodes to {self.api_url} ({error_count} errors)"
            
            logger.info(f"🏆 Final result: Import job completed - Data transmitted to OpenCTI server {self.api_url}")
            
            return {
                'success': True,
                'message': message,
                'imported': imported_count,
                'errors': error_count
            }
            
        except Exception as e:
            logger.error(f"❌ OpenCTI import failed: {e}")
            return {
                'success': False,
                'message': str(e),
                'imported': 0
            }