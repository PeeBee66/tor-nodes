# GitHub Upload Configuration Guide

This guide helps you set up automatic uploads of Tor node data to GitHub.

## Prerequisites

1. **GitHub Account**: You need a GitHub account
2. **Repository**: Create a repository on GitHub to store the data
3. **Personal Access Token**: Generate a token with appropriate permissions

## Step 1: Create a GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon → "New repository"
3. Name it something like `tor-node-data`
4. Choose Public or Private (your choice)
5. Initialize with a README if desired
6. Create repository

## Step 2: Generate Personal Access Token

1. Go to GitHub → Settings → Developer settings
2. Navigate to Personal access tokens → Tokens (classic)
3. Click "Generate new token"
4. Configure the token:
   - **Note**: "Tor Node Scraper Upload"
   - **Expiration**: Choose based on your needs
   - **Scopes**: 
     - For public repos: Select `public_repo`
     - For private repos: Select `repo` (full control)
5. Generate token and **copy it immediately** (you won't see it again!)

## Step 3: Configure the Upload

### Option A: Using the Setup Script (Recommended)
```bash
./setup_github.sh
```
Follow the prompts to enter:
- Your repository (e.g., `yourusername/tor-node-data`)
- Your GitHub token
- Upload frequency (default: 1 hour)

### Option B: Manual Configuration
Edit `docker-compose.yml`:
```yaml
- UPLOAD_TO_GITHUB=true
- GITHUB_REPO=yourusername/your-repo-name
- GITHUB_TOKEN=ghp_YourTokenHere
- GITHUB_UPLOAD_FREQ_HOURS=1
```

### Option C: Using Environment File (Most Secure)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your values
3. Update `docker-compose.yml` to use env_file:
   ```yaml
   env_file:
     - .env
   ```

## Step 4: Apply Changes

Restart the container:
```bash
docker-compose down
docker-compose up -d
```

## Step 5: Verify Upload

1. Check logs:
   ```bash
   docker-compose logs -f tor-scraper | grep -i github
   ```

2. Check your GitHub repository for:
   - `tor_nodes_YYYY-MM-DD.csv` - Daily snapshots
   - `tor_nodes_latest.csv` - Always current data

## Upload Schedule

- Uploads run according to `GITHUB_UPLOAD_FREQ_HOURS` (default: every hour)
- Each upload creates/updates two files:
  1. A dated file for historical records
  2. A "latest" file for easy access to current data

## Troubleshooting

### Common Issues:

1. **401 Unauthorized**
   - Check your token is correct
   - Ensure token has necessary permissions

2. **404 Not Found**
   - Verify repository name format: `username/repo`
   - Ensure repository exists

3. **No uploads appearing**
   - Check `UPLOAD_TO_GITHUB=true` is set
   - Review logs for errors
   - Ensure at least one successful scrape has completed

## Security Best Practices

1. **Never commit tokens**: Add `.env` to `.gitignore`
2. **Use minimal permissions**: Only grant necessary scopes
3. **Rotate tokens regularly**: Set expiration dates
4. **Use secrets in production**: Consider GitHub Actions secrets or environment variables

## Data Structure

Uploaded CSV files contain:
- IP
- IsExit
- Name
- OnionPort
- DirPort
- Flags
- Uptime
- Version
- Contact
- CollectionDate

## Example Repository Structure

After running for a few days:
```
your-repo/
├── README.md
├── tor_nodes_latest.csv
├── tor_nodes_2025-07-24.csv
├── tor_nodes_2025-07-25.csv
└── tor_nodes_2025-07-26.csv
```