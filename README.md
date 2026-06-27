# Agentic Marketing Agency

An autonomous, multi-agent framework for digital marketing. The system operates as an end-to-end digital marketing agency that onboard clients, conducts market research, generates content and assets, and programs campaigns directly into advertising platforms via APIs.

## 🚀 Features

- **Multi-Agent System**: Orchestrator, Researcher, Creative, Launch, and Performance Analyst agents work together
- **Website Scraping**: Automatically analyzes client websites to extract products, services, and brand voice
- **Campaign Creation**: Generates Google RSA and Meta ads with platform-specific constraints
- **A/B Testing**: Automatically tests multiple variants and promotes winners
- **Performance Optimization**: Background monitoring with auto-optimization
- **Client Portal**: Separate dashboards for clients
- **PDF Reports**: Professional client-ready reports
- **Real API Integration**: Google Ads and Meta Ads API support
- **Multi-Client**: Support for multiple clients and user roles

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js (for development)

## 🚀 Quick Start

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/iulio/marketing-agents.git
cd marketing-agents

# Start the services
docker-compose up -d

# Wait for the app to be ready
docker-compose logs -f app

# Access the dashboard
open http://localhost:8000