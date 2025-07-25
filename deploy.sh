#!/bin/bash

# Tor Node Monitor Deployment Script
# This script helps deploy and test the Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Create necessary directories
setup_directories() {
    print_status "Creating data and log directories..."
    mkdir -p data logs
    chmod 755 data logs
}

# Build the Docker image
build_container() {
    print_status "Building Docker container..."
    docker-compose build --no-cache
    
    if [ $? -eq 0 ]; then
        print_status "Container built successfully"
    else
        print_error "Failed to build container"
        exit 1
    fi
}

# Start the container
start_container() {
    print_status "Starting container..."
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        print_status "Container started successfully"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Wait for the application to be ready
wait_for_app() {
    print_status "Waiting for application to be ready..."
    
    for i in {1..30}; do
        if curl -s http://localhost:5002 > /dev/null; then
            print_status "Application is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    print_error "Application failed to start within 30 seconds"
    return 1
}

# Run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check if web interface is accessible
    if curl -s http://localhost:5002 > /dev/null; then
        print_status "Web interface is accessible"
    else
        print_error "Web interface is not accessible"
        return 1
    fi
    
    # Check API endpoints
    if curl -s http://localhost:5002/api/stats > /dev/null; then
        print_status "Stats API is working"
    else
        print_error "Stats API is not working"
        return 1
    fi
    
    if curl -s http://localhost:5002/api/nodes > /dev/null; then
        print_status "Nodes API is working"
    else
        print_error "Nodes API is not working"
        return 1
    fi
    
    # Check if CSV file is created
    if [ -f "data/tor_nodes.csv" ]; then
        print_status "CSV file has been created"
        print_status "Current node count: $(wc -l < data/tor_nodes.csv)"
    else
        print_warning "CSV file not yet created (will be created after first scrape)"
    fi
    
    # Check logs
    if [ -f "logs/app.log" ]; then
        print_status "Log file is being written"
        print_status "Recent log entries:"
        tail -n 5 logs/app.log | sed 's/^/    /'
    else
        print_warning "Log file not yet created"
    fi
}

# Display container logs
show_logs() {
    print_status "Recent container logs:"
    docker-compose logs --tail=20 tor-scraper
}

# Display usage information
show_usage() {
    echo ""
    print_status "Deployment successful! Here's how to use the system:"
    echo ""
    echo "  Web Interface:    http://localhost:5002"
    echo "  Test Force Scrape: python3 test_force_scrape.py"
    echo "  View logs:        docker-compose logs -f tor-scraper"
    echo "  Stop container:   docker-compose down"
    echo "  Restart:          docker-compose restart"
    echo ""
    print_status "Configuration:"
    echo "  Edit docker-compose.yml to:"
    echo "  - Enable GitHub uploads (set UPLOAD_TO_GITHUB=true and add token)"
    echo "  - Enable OpenCTI import (set UPLOAD_TO_OPENCTI=true and add API key)"
    echo "  - Enable email notifications (set EMAIL_ENABLED=true and add SMTP settings)"
    echo ""
}

# Clean up function
cleanup() {
    print_warning "Cleaning up..."
    docker-compose down
    exit 1
}

# Set trap for cleanup on error
trap cleanup ERR INT

# Main deployment process
main() {
    echo "======================================"
    echo "Tor Node Monitor Deployment Script"
    echo "======================================"
    echo ""
    
    # Run deployment steps
    check_docker
    setup_directories
    build_container
    start_container
    
    # Wait and check
    if wait_for_app; then
        run_health_checks
        show_logs
        show_usage
    else
        print_error "Deployment failed. Showing logs:"
        show_logs
        exit 1
    fi
}

# Handle command line arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    stop)
        print_status "Stopping container..."
        docker-compose down
        ;;
    restart)
        print_status "Restarting container..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f tor-scraper
        ;;
    status)
        print_status "Container status:"
        docker-compose ps
        ;;
    clean)
        print_warning "This will remove containers, images, and data. Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            docker-compose down -v --rmi all
            rm -rf data/* logs/*
            print_status "Cleanup complete"
        else
            print_status "Cleanup cancelled"
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|stop|restart|logs|status|clean}"
        echo ""
        echo "  deploy  - Build and start the container (default)"
        echo "  stop    - Stop the container"
        echo "  restart - Restart the container"
        echo "  logs    - Show container logs (follow mode)"
        echo "  status  - Show container status"
        echo "  clean   - Remove containers, images, and data"
        exit 1
        ;;
esac