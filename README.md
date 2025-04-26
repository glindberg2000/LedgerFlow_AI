# LedgerFlow

LedgerFlow is a Django-based application designed to handle financial document processing and data extraction. It provides automated extraction of financial data from PDF documents, structured storage and categorization of financial transactions, and integration with accounting systems.

## Features

- PDF document upload and processing
- Automated data extraction
- Transaction categorization
- Business profile management
- Data validation and verification
- Modern web-based interface

## Prerequisites

- Docker Desktop
- Make (optional, for using Makefile commands)

## Development Setup

1. Clone the repository:
```bash
   git clone https://github.com/yourusername/ledgerflow.git
   cd ledgerflow
```

2. Create environment files:
   ```bash
   cp .env.dev.template .env.dev
   ```
   Edit `.env.dev` with your development settings.

3. Build and start the development environment:
```bash
   make dev-build
   make dev-up
```

4. Run migrations:
```bash
   make migrate
```

5. Create a superuser:
```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml exec django python manage.py createsuperuser
   ```

The application will be available at:
- Main application: http://localhost:9001
- Adminer (database management): http://localhost:8082

## Development Commands

- `make help` - Show available commands
- `make dev-up` - Start development environment
- `make dev-down` - Stop development environment
- `make migrate` - Run database migrations
- `make migrations` - Create database migrations
- `make shell` - Open Django shell
- `make test` - Run tests
- `make lint` - Run linters
- `make format` - Format code
- `make clean` - Remove Python artifacts

## Production Deployment

1. Create and configure production environment file:
   ```bash
   cp .env.dev.template .env.prod
   ```
   Edit `.env.prod` with your production settings.

2. Build and start the production environment:
```bash
   make prod-build
   make prod-up
   ```

3. Run migrations:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec django python manage.py migrate
```

## Project Structure

```
ledgerflow/
├── app/                    # Django application
│   ├── core/              # Core functionality
│   ├── documents/         # Document processing
│   ├── profiles/          # Business profiles
│   └── ledgerflow/        # Project settings
├── requirements/          # Python dependencies
│   ├── base.txt          # Base requirements
│   └── dev.txt           # Development requirements
├── static/               # Static files
├── media/                # User-uploaded files
├── docker-compose.yml    # Base Docker configuration
├── docker-compose.dev.yml # Development configuration
├── docker-compose.prod.yml # Production configuration
└── Dockerfile           # Docker build instructions
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
