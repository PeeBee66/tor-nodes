import csv
import logging
from pycti import OpenCTIApiClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_URL = "http://172.21.32.180:4000/"
API_KEY = "81d704bc-d5d8-482f-b349-ccb972b6d423"

#
# 1) Create or update Organisation: "PeeBee"
#
def create_organization(api_client):
    """Create or update an Organisation named 'PeeBee'."""
    try:
        organization = api_client.identity.create(
            type="Organization",
            name="PeeBee",
            description="PeeBee Tor node Input",
            update=True  # Ensures we update if it already exists
        )
        print(f"[ORG] Created/Updated: {organization}")
        return organization
    except Exception as e:
        print(f"[ORG] Error: {str(e)}")
        return None

#
# 2) Create or update an IPv4 observable
#
def create_ipv4(api_client, ip, peebee_id):
    """Create (or update) an IPv4 observable with createdById = PeeBee."""
    try:
        observable = api_client.stix_cyber_observable.create(
            observableData={
                'type': 'IPv4-Addr',
                'value': ip
            },
            createdById=peebee_id,  # <-- Link to PeeBee org
            update=True
        )
        print(f"[IPv4] Created/Updated: {observable}")
        return observable
    except Exception as e:
        print(f"[IPv4] Error creating {ip}: {str(e)}")
        return None

#
# 3) Create or update an Indicator
#
def create_indicator(api_client, ip_data, peebee_id):
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
        indicator = api_client.indicator.create(
            name=indicator_name,
            description=description,
            pattern=stix_pattern,
            pattern_type="stix",
            x_opencti_main_observable_type="IPv4-Addr",
            x_opencti_score=75,
            createdById=peebee_id,  # <-- Link to PeeBee org
            update=True
        )
        print(f"[Indicator] Created/Updated: {indicator}")
        return indicator
    except Exception as e:
        print(f"[Indicator] Error creating for IP {ip_value}: {str(e)}")
        return None

#
# 4) Create or update a "based-on" relationship between Indicator & IPv4
#
def create_relationship(api_client, indicator, ipv4, peebee_id):
    """Create (or update) a 'based-on' relationship between the Indicator and IPv4."""
    try:
        relationship = api_client.stix_core_relationship.create(
            fromId=indicator["id"],
            toId=ipv4["id"],
            relationship_type="based-on",
            description="Indicator based on IP observable",
            createdById=peebee_id,  # <-- Link to PeeBee org
            update=True
        )
        print(f"[Relationship] Created/Updated: {relationship}")
        return relationship
    except Exception as e:
        print(f"[Relationship] Error: {str(e)}")
        return None

def main():
    client = OpenCTIApiClient(API_URL, API_KEY)

    # Step A) Create/Update 'PeeBee' org, get its ID
    peebee_org = create_organization(client)
    if not peebee_org or "id" not in peebee_org:
        print("Error: Unable to create/find PeeBee org. Exiting.")
        return
    peebee_id = peebee_org["id"]

    # Step B) Read the CSV & create objects
    with open('tor_nodes.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ip = row.get("IP", "").strip()
            if not ip:
                continue

            # 1) Create IPv4
            ipv4_observable = create_ipv4(client, ip, peebee_id)
            if not ipv4_observable or "id" not in ipv4_observable:
                continue

            # 2) Create Indicator
            indicator = create_indicator(client, row, peebee_id)
            if not indicator or "id" not in indicator:
                continue

            # 3) Link them with a 'based-on' relationship
            create_relationship(client, indicator, ipv4_observable, peebee_id)

if __name__ == "__main__":
    main()
