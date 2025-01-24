# BookChat Deployment Guide

This guide covers how to deploy and configure BookChat in various environments.

## Prerequisites

- Python 3.7 or higher
- Node.js 16 or higher (for testing)
- Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bookchat.git
   cd bookchat
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. (Optional) Install Node.js dependencies for testing:
   ```bash
   npm install
   ```

## Configuration

1. Copy the environment template:
   ```bash
   cp .env.template .env
   ```

2. Configure the following environment variables in `.env`:

### Required Settings
- `DEBUG`: Set to 'true' for detailed logging (default: false)
- `PORT`: Server port (optional, will auto-detect if not set)

### Optional Settings
- `GITHUB_TOKEN`: GitHub personal access token for syncing
- `GITHUB_REPO`: Repository name (format: username/repository)
- `MESSAGE_VERIFICATION`: Enable message verification (true/false)

## Running the Server

1. Start the server:
   ```bash
   python server.py
   ```

   The server will:
   - Find an available port (starting from 8001)
   - Open your default web browser
   - Create necessary directories if they don't exist

2. Access the application:
   - Open `http://localhost:<PORT>` in your browser
   - The port will be displayed in the console output

## Production Deployment

For production deployment, consider:

1. Using a process manager (e.g., supervisord)
2. Setting up a reverse proxy (nginx/Apache)
3. Implementing proper logging
4. Setting up SSL/TLS

### Example Supervisor Configuration
```ini
[program:bookchat]
command=/path/to/venv/bin/python server.py
directory=/path/to/bookchat
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/bookchat/err.log
stdout_logfile=/var/log/bookchat/out.log
environment=
    DEBUG=false,
    PORT=8001
```

### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name your.domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

1. Port in use:
   - The server will automatically find an available port
   - Override with `PORT` environment variable

2. Browser doesn't open:
   - Access the URL shown in console output
   - Check if running in WSL/container environment

3. Message storage issues:
   - Ensure write permissions in messages directory
   - Check log file for detailed errors

## Maintenance

1. Backup strategy:
   - Regular backups of `messages/` directory
   - Git repository serves as version control

2. Updating:
   ```bash
   git pull
   pip install -r requirements.txt
   ```

*Last updated: 2025-01-23*
