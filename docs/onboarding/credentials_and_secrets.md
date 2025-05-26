# Credentials and Secrets Guide

This document outlines the credentials and secrets that team members need to access and work with the LedgerFlow project. **None of these credentials should be committed to the repository.**

## Required Credentials by Role

### All Team Members

- GitHub repository access
- Discord/Matrix access
- Knowledge of where to find the Memory Bank (`cline_docs/`)

### Project Manager

- Admin dashboard credentials (for monitoring)
- Access to project management tools
- Cloud storage access (for backup verification)

### Database Manager

- Database credentials (`.env.dev` and `.env.prod`)
- Cloud storage access (for backups)
- Production server SSH access (if applicable)
- Monitoring dashboard access

### Full Stack Developer

- Development environment credentials (`.env.dev`)
- API keys for external services
- Docker Hub credentials (if applicable)
- Database credentials for development

### Reviewer

- GitHub credentials with reviewer permissions
- Development environment credentials (`.env.dev`)
- Code quality tool access

## Environment Files

### .env.dev (Development)

This file contains development environment variables and should be created by copying `.env.example` and filling in the values:

```
# Django settings
DEBUG=True
SECRET_KEY=<your-secret-key>
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://ledgerflow:ledgerflow@postgres:5432/ledgerflow
POSTGRES_DB=ledgerflow
POSTGRES_USER=ledgerflow
POSTGRES_PASSWORD=<your-db-password>

# Media and static files
MEDIA_ROOT=/app/media
STATIC_ROOT=/app/static/collected

# Security settings
CSRF_TRUSTED_ORIGINS=http://localhost:9001
SESSION_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False

# Email settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### .env.prod (Production)

Similar to `.env.dev` but with production values:

```
# Django settings
DEBUG=False
SECRET_KEY=<your-production-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://ledgerflow:<prod-password>@postgres:5432/ledgerflow
POSTGRES_DB=ledgerflow
POSTGRES_USER=ledgerflow
POSTGRES_PASSWORD=<prod-db-password>

# Media and static files
MEDIA_ROOT=/app/media
STATIC_ROOT=/app/static/collected

# Security settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True

# Email settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<email-user>
EMAIL_HOST_PASSWORD=<email-password>
```

## How to Request Access

1. **GitHub Access**: Contact the team lead to be added to the repository.
2. **Discord/Matrix**: The team lead will send an invitation to join.
3. **Development Credentials**: The team lead will provide a secure method to share the `.env.dev` file.
4. **Production Credentials**: These will be provided only to team members who need them, using a secure sharing method.

## How to Securely Handle Credentials

1. **Never commit credentials** to the repository (even in comments or documentation).
2. **Do not share credentials** via public channels, unsecured email, or chat.
3. Use a **password manager** to store credentials securely.
4. Use **encrypted communications** when sharing credentials.
5. **Rotate credentials** regularly or when team members leave.

## Backup and Recovery

Database backups are stored in iCloud at:
```
~/Library/Mobile Documents/com~apple~CloudDocs/repos/LedgerFlow_Archive/backups
```

The backup files contain sensitive data and should be handled securely. Access to these files should be restricted to team members who need it.

## SSH Keys

For production server access (if applicable), SSH keys must be:
1. Generated with strong encryption (ED25519 or RSA 4096+)
2. Protected with a passphrase
3. Never committed to the repository
4. Distributed securely to team members who need them

## Contact for Access

For all credential requests or access issues, please contact:
- Team Lead: [Name and contact information to be provided separately] 