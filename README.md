# Tor Node Monitor

A lightweight Docker-based application for monitoring Tor network nodes. This tool scrapes Tor node information, maintains historical data, and can integrate with GitHub and OpenCTI for data sharing and threat intelligence.

## Features

- **Automated Tor Node Scraping**: Periodically fetches Tor node data from configured sources
- **Smart Update Detection**: Only scrapes when the source has been updated
- **Web Dashboard**: Real-time monitoring interface on port 5002
- **GitHub Integration**: Automatic backup of node data to GitHub
- **OpenCTI Integration**: Import nodes as threat intelligence indicators
- **Email Notifications**: Daily/weekly summary reports
- **Lightweight Docker Container**: Minimal resource footprint

## Quick Start

### Option 1: Using Docker Hub (Recommended)

1. Create a new directory and download the docker-compose.yml:
```bash
mkdir tor-node-monitor
cd tor-node-monitor
wget https://raw.githubusercontent.com/your-username/Tor_Daily_scraper/main/docker-compose.yml
```

2. Copy the environment template and configure your settings:
```bash
wget https://raw.githubusercontent.com/your-username/Tor_Daily_scraper/main/.env.example -O .env
nano .env  # Edit with your configuration
```

3. Start the application:
```bash
docker-compose up -d
```

### Option 2: Build from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd Tor_Daily_scraper
```

2. Copy and configure environment variables:
```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

3. Build and run:
```bash
docker-compose up -d
```

### Accessing the Application

- Web interface: `http://localhost:5002`
- The application will start scraping immediately and show data within minutes

## Configuration

All configuration is done through environment variables in `docker-compose.yml`:

### Scraping Configuration
- `TOR_SCRAPE_SITE`: Base URL for Tor node data (default: https://www.dan.me.uk)
- `TOR_SCRAPE_FREQUENCY_HOURS`: How often to check for updates (default: 1)

### GitHub Upload (Optional)
- `UPLOAD_TO_GITHUB`: Enable GitHub uploads (true/false)
- `GITHUB_REPO`: Repository in format `owner/repo`
- `GITHUB_TOKEN`: Personal access token with repo permissions
- `GITHUB_UPLOAD_FREQ_HOURS`: Upload frequency (default: 1)

### OpenCTI Integration (Optional)
- `UPLOAD_TO_OPENCTI`: Enable OpenCTI imports (true/false)
- `OPENCTI_URL`: OpenCTI server URL
- `OPENCTI_API_KEY`: OpenCTI API key
- `OPENCTI_UPLOAD_FREQ_HOURS`: Import frequency (default: 1)

### Email Notifications (Optional)
- `EMAIL_ENABLED`: Enable email reports (true/false)
- `EMAIL_SMTP_SERVER`: SMTP server address
- `EMAIL_SMTP_PORT`: SMTP port (default: 587)
- `EMAIL_USERNAME`: SMTP username
- `EMAIL_PASSWORD`: SMTP password
- `EMAIL_FROM`: Sender email address
- `EMAIL_TO`: Recipient email address
- `EMAIL_FREQUENCY`: Report frequency (daily/weekly)

## Data Storage

- **CSV Data**: `/app/data/tor_nodes.csv` (mounted as volume)
- **Logs**: `/app/logs/app.log` (mounted as volume)
- **Statistics**: `/app/data/stats.json`

## Web Interface

The web dashboard provides:
- Real-time node statistics (total, exit, new, removed)
- Searchable table of all Tor nodes
- History logs for scraping, GitHub uploads, and OpenCTI imports
- Visual status indicators for all operations

## API Endpoints

- `GET /api/stats`: Current statistics and operation history
- `GET /api/nodes`: Full list of Tor nodes in JSON format

## Security Considerations

This tool is designed for defensive security monitoring only. When deploying:

1. **API Keys**: Never commit API keys to version control
2. **Network Security**: Use appropriate firewall rules
3. **Data Privacy**: Be mindful of data retention policies
4. **Access Control**: Restrict access to the web interface

## Development

### Project Structure
```
Tor_Daily_scraper/
├── app.py              # Main Flask application
├── scraper.py          # Tor node scraping logic
├── github_uploader.py  # GitHub integration
├── opencti_importer.py # OpenCTI integration
├── email_notifier.py   # Email notification system
├── templates/          # Web interface templates
├── static/            # CSS and JavaScript files
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container definition
└── docker-compose.yml # Container orchestration
```

### Running Locally

For development without Docker:
```bash
pip install -r requirements.txt
python app.py
```

## Troubleshooting

### Common Issues

1. **Scraping fails**: Check if the source site is accessible and the format hasn't changed
2. **GitHub upload fails**: Verify token permissions and repository access
3. **OpenCTI import fails**: Ensure OpenCTI server is reachable and API key is valid
4. **No email notifications**: Check SMTP settings and firewall rules

### Logs

Check application logs at `/app/logs/app.log` or use:
```bash
docker-compose logs -f tor-scraper
```

## License

This project is for defensive security monitoring purposes only.