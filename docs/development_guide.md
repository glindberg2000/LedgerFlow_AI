# LedgerFlow Development Guide

## Development Environment

### Hot Reload Development
The development environment is set up with hot reload capabilities, which means most changes will be automatically detected and applied without needing to restart containers:

1. Python file changes are automatically detected
2. Template changes are automatically reloaded
3. Static file changes are automatically collected

However, some changes require manual intervention:

- Database schema changes (migrations)
- Environment variable changes
- Package installations
- Changes to Docker configuration

### Working with Docker

#### Basic Commands
```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d

# Stop all services
docker compose -f docker-compose.dev.yml down

# Restart a specific service
docker compose -f docker-compose.dev.yml restart django

# View logs
docker compose -f docker-compose.dev.yml logs -f django

# Execute commands in containers
docker compose -f docker-compose.dev.yml exec django python manage.py shell
```

#### Database Operations
```bash
# Create migrations
docker compose -f docker-compose.dev.yml exec django python manage.py makemigrations

# Apply migrations
docker compose -f docker-compose.dev.yml exec django python manage.py migrate

# Reset database (caution!)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```

### Available Make Commands
The project includes several make commands for common operations:

```bash
# Start development environment
make dev

# Run tests
make test

# Create database backup
make backup

# Restore database
make restore

# Clean Docker volumes
make clean

# Install dependencies
make install

# Update dependencies
make update-deps
```

## Working with Tools

### Search Tool
The search tool provides web search capabilities using SearXNG:

```python
from tools.search_tool import search_web

# Basic search
results = search_web("query")

# Advanced search with options
results = search_web(
    query="query",
    num_results=5,
    engines=["google", "bing"],
    language="en-US",
    safesearch=1  # 0=off, 1=moderate, 2=strict
)
```

### Environment Variables
Important environment variables for development:

```bash
# Django
DEBUG=True
DJANGO_SETTINGS_MODULE=settings
SECRET_KEY=your-secret-key

# Database
POSTGRES_DB=mydatabase
POSTGRES_USER=newuser
POSTGRES_PASSWORD=newpassword
DATABASE_URL=postgres://newuser:newpassword@postgres:5432/mydatabase

# Search Configuration
SEARXNG_HOST=http://localhost:8888
SEARXNG_SECRET_KEY=your-key-here

# OpenAI
OPENAI_API_KEY=your-key-here
OPENAI_MODEL_FAST=gpt-4.1-mini
OPENAI_MODEL_PRECISE=o4-mini
```

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Check the module path in the database (`profiles_tool` table)
   - Verify `__init__.py` exports
   - Restart Django container if needed

2. **Database Connection Issues**
   - Verify credentials in `.env.dev`
   - Check if PostgreSQL container is running
   - Ensure volume persistence is working

3. **Search Tool Issues**
   - Check SearXNG container status
   - Verify environment variables
   - Check network connectivity between containers

### Debugging Tips

1. **Django Debug Toolbar**
   - Available at `/__debug__/` when `DEBUG=True`
   - Shows SQL queries, templates, cache info

2. **Container Logs**
   ```bash
   # View Django logs
   docker compose -f docker-compose.dev.yml logs -f django
   
   # View PostgreSQL logs
   docker compose -f docker-compose.dev.yml logs -f postgres
   ```

3. **Database Inspection**
   - Adminer available at `http://localhost:8082`
   - Direct PostgreSQL access:
     ```bash
     docker compose -f docker-compose.dev.yml exec postgres psql -U newuser mydatabase
     ``` 