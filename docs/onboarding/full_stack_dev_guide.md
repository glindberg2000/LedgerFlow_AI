# Full Stack Developer Onboarding Guide

Welcome to the LedgerFlow team as a Full Stack Developer! This guide will help you understand your role, responsibilities, and the tools you'll need to be effective.

## Your Role

As a Full Stack Developer for LedgerFlow, you are responsible for:

1. Implementing new features and enhancements
2. Fixing bugs and addressing technical debt
3. Writing clean, maintainable, and well-tested code
4. Collaborating with team members on design and implementation
5. Contributing to code reviews and documentation
6. Ensuring code follows project standards and patterns

## Essential Information

### Tech Stack

LedgerFlow is built with:

- **Backend**: Django 5.2, Python 3.11+
- **Database**: PostgreSQL 15
- **Frontend**: Django Templates, Bootstrap, JavaScript
- **Infrastructure**: Docker, Docker Compose
- **Search**: SearxNG (optional)
- **Cache/Queue**: Redis (planned)
- **Web Server**: Gunicorn (prod), Django dev server (dev)

### Project Structure

```
ledgerflow/
├── app/                    # Django application
│   ├── core/              # Core functionality (main dev app)
│   ├── documents/         # Document processing
│   └── profiles/          # User profiles
├── cline_docs/            # Memory Bank documentation
├── config/                # Configuration files
├── docker/                # Docker configurations
├── docs/                  # Documentation
├── requirements/          # Python dependencies
├── scripts/               # Utility scripts
├── static/                # Static files
├── templates/             # HTML templates
└── tests/                 # Test suite
```

Key components:
- `core/` is the main development app
- `ledgerflow/` is the main production app
- `profiles/` handles user and business profiles
- Legacy code has been moved to `deprecated/`

## Required Access

You'll need access to:

- [ ] GitHub repository
- [ ] Discord/Matrix channels
- [ ] Development environment credentials (`.env.dev`)
- [ ] Docker Hub (if applicable)
- [ ] Admin dashboard credentials

## Technical Setup

### Local Environment Setup

1. Follow the general setup in the main onboarding guide
2. Install the safety wrapper (CRITICAL):
```bash
mkdir -p ~/bin
curl -s https://raw.githubusercontent.com/LedgerFlow/LedgerFlow/main/scripts/ledger_docker -o ~/bin/ledger_docker && chmod +x ~/bin/ledger_docker

# Add to your shell configuration
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
echo 'docker() { ledger_docker "$@"; }' >> ~/.zshrc
source ~/.zshrc
```

3. Additional development tools (recommended):
   - VS Code or PyCharm for development
   - Django debug toolbar
   - Python linting tools (flake8, black, etc.)
   - Git GUI client

## Key Workflows

### Development Workflow

1. Get latest code:
```bash
git pull origin main
```

2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

3. Start development environment:
```bash
make dev
```

4. Make your changes
5. Run tests:
```bash
docker compose -f docker-compose.dev.yml exec django python manage.py test
```

6. Format code:
```bash
# If using black
docker compose -f docker-compose.dev.yml exec django black .
```

7. Commit and push:
```bash
git add .
git commit -m "Descriptive commit message"
git push origin feature/your-feature-name
```

8. Create a pull request on GitHub
9. Address review feedback
10. Merge to main (after approval)

### Django Management Commands

```bash
# Create migrations
docker compose -f docker-compose.dev.yml exec django python manage.py makemigrations

# Apply migrations
docker compose -f docker-compose.dev.yml exec django python manage.py migrate

# Create superuser
docker compose -f docker-compose.dev.yml exec django python manage.py createsuperuser

# Django shell
docker compose -f docker-compose.dev.yml exec django python manage.py shell

# Collect static
docker compose -f docker-compose.dev.yml exec django python manage.py collectstatic
```

### Docker Workflow

Always use `make` commands instead of raw Docker commands to ensure safety:

```bash
make dev          # Start development environment
make backup       # Create a database backup
make restore FILE=x  # Restore database from backup
make check-volumes   # Verify volume protection
```

## Important Files

- `docker-compose.dev.yml` - Development configuration
- `docker-compose.prod.yml` - Production configuration
- `.env.dev` - Development environment variables
- `Makefile` - Contains helpful commands
- `manage.py` - Django management script
- `cline_docs/` - Memory Bank documentation

## Code Style and Guidelines

- Follow PEP 8 for Python code style
- Use Django's coding style for models, views, etc.
- Write docstrings for all functions and classes
- Include type hints where appropriate
- Keep functions small and focused
- Write tests for new features
- Update documentation as needed

## Testing

- Run tests locally before submitting PRs
- Write unit tests for models, views, forms, etc.
- Write integration tests for complex features
- Use Django's test client for view tests
- Use pytest fixtures where appropriate

## Memory Bank

The Memory Bank (`cline_docs/`) contains essential documentation:

- `productContext.md` - Product overview and context
- `activeContext.md` - Current focus and recent changes
- `systemPatterns.md` - Architecture patterns and decisions
- `techContext.md` - Technical details and constraints
- `progress.md` - Project progress and status

## Required Credentials

The following credentials are not stored in the repository and must be obtained separately:

- Development environment variables (`.env.dev`)
- Django admin credentials
- API keys (if applicable)
- Docker Hub credentials (if applicable)

## First Week Tasks

- [ ] Review the Memory Bank (`cline_docs/`)
- [ ] Set up local development environment
- [ ] Explore the codebase
- [ ] Run the application locally
- [ ] Fix a small bug or implement a simple feature
- [ ] Submit your first pull request
- [ ] Review code with a team member

## Contact Information

For access to credentials or with questions about your role, please contact:
- Team Lead: [Name and contact information to be provided separately] 