# Development Deployment Guide

## Overview
This guide explains how to safely work with the LedgerFlow development environment using our Make-based tooling system.

## Prerequisites
- Docker Desktop installed and running
- Make installed
- Access to the repository
- `.env.dev` file configured

## Basic Commands

### Starting Development Environment
```bash
make dev
```
This command:
- Starts all development containers
- Ensures volumes are properly mounted
- Sets up development network
- Runs in detached mode

### Checking Status
```bash
make status
```
Shows:
- Running containers
- Container health
- Exposed ports
- Volume status

### Viewing Logs
```bash
make logs
```
Displays:
- Application logs
- Database logs
- Error messages
- Access logs

## Database Operations

### Creating a Backup
```bash
make backup
```
Best practices:
- Always create a backup before major changes
- Verify backup size (should be > 10KB)
- Check backup logs for success

### Restoring from Backup
```bash
make restore FILE=path/to/backup.sql.gz
```
Safety measures:
- Only works in development environment
- Verifies backup integrity
- Checks for minimum size
- Validates data after restore

## Safe Development Practices

### 1. Before Starting Work
```bash
# Update your environment
git pull
make dev

# Verify environment
make status
make check-volumes
```

### 2. Making Database Changes
```bash
# Create backup first
make backup

# Apply migrations
make migrate

# Verify changes
make test
```

### 3. Cleaning Up
```bash
# Safe cleanup (preserves data)
make down

# Complete cleanup (USE WITH CAUTION)
make nuke ENV=dev
```

## Safety Features

### Protected Operations
Some commands require explicit confirmation:
```bash
make nuke ENV=dev
# Requires typing "DESTROY" to proceed
```

### Environment Protection
- Production commands are blocked
- Volume deletion requires confirmation
- Automatic backup verification

## Common Tasks

### Rebuilding Containers
```bash
make rebuild
```
This safely:
1. Creates a backup
2. Stops containers
3. Rebuilds images
4. Restarts services

### Updating Dependencies
```bash
make update-deps
```
Safely updates:
- Python packages
- Node modules
- System dependencies

### Running Tests
```bash
make test
```
Includes:
- Unit tests
- Integration tests
- Linting
- Type checking

## Troubleshooting

### If Containers Won't Start
1. Check logs: `make logs`
2. Verify volumes: `make check-volumes`
3. Check environment: `make env-check`

### If Database Issues Occur
1. Create backup: `make backup`
2. Check volumes: `make check-volumes`
3. Verify data: `make verify-data`

### If Changes Aren't Reflected
1. Rebuild: `make rebuild`
2. Clear cache: `make clear-cache`
3. Check logs: `make logs`

## Best Practices

1. **Always Backup First**
   ```bash
   make backup
   # Then proceed with changes
   ```

2. **Check Status Regularly**
   ```bash
   make status
   make health-check
   ```

3. **Use Safe Cleanup**
   ```bash
   make down  # Instead of docker compose down
   ```

4. **Verify After Changes**
   ```bash
   make test
   make verify-data
   ```

## Emergency Procedures

If you encounter issues:

1. Stop operations:
   ```bash
   make down
   ```

2. Check status:
   ```bash
   make status
   make check-volumes
   ```

3. Verify data:
   ```bash
   make verify-data
   ```

4. Restore if needed:
   ```bash
   make restore FILE=backups/latest.sql.gz
   ```

Remember: Safety first! When in doubt, create a backup and ask for help. 