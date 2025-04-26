# Security Measures - CRITICAL MEMORY

## Core Security Principles
I MUST ALWAYS follow these principles without exception:

1. **NEVER Use Raw Docker Commands for Volume Operations**
   - ALWAYS use `ledger_docker` wrapper
   - NEVER execute `docker compose down -v` directly
   - ALWAYS use `make` targets for dangerous operations

2. **Backup Verification is MANDATORY**
   - NEVER trust a backup without size verification
   - ALWAYS verify backup integrity through test restore
   - ALWAYS check transaction counts match
   - Minimum backup size MUST be > 10KB

3. **Environment Separation is ABSOLUTE**
   - NEVER run prod commands without explicit authorization
   - ALWAYS verify environment before destructive actions
   - ALWAYS use environment-specific compose files

4. **Volume Protection is SACRED**
   - ALWAYS check for protected volume labels
   - NEVER bypass volume protection mechanisms
   - ALWAYS verify volume mounts in compose files

## Mandatory Checks Before Actions

### Before ANY Volume Operation:
1. Check current environment (dev/prod)
2. Verify backup exists and is valid
3. Confirm operation is using `ledger_docker`
4. Double-check compose file being used

### Before Database Operations:
1. Verify backup is recent and valid
2. Check backup size is > 10KB
3. Verify transaction counts
4. Test restore in temporary container

### Before Deployment:
1. Run volume protection checks
2. Verify environment variables
3. Check for protected volumes
4. Ensure backups are current

## Emergency Response Protocol

If I encounter ANY of these situations:
1. Volume deletion attempt
2. Zero-byte backup
3. Failed integrity check
4. Missing protection labels

I MUST:
1. Stop all operations immediately
2. Log the incident
3. Verify data integrity
4. Notify appropriate stakeholders
5. Review protection mechanisms

## Security Verification Commands

I MUST use these commands regularly:
```bash
# Check volume protection
docker volume ls --filter label=com.ledgerflow.protect=true

# Verify backup integrity
ls -lh /path/to/backup  # Must be > 10KB
tar tzf backup.tar.gz   # Must succeed

# Check environment
echo $LEDGER_ENV        # Must match context
```

## Documentation Requirements

I MUST maintain:
1. Current backup status
2. Protection mechanism state
3. Environment configurations
4. Emergency procedures

## Non-Negotiable Rules

1. NEVER bypass security measures for convenience
2. ALWAYS verify before destructive actions
3. NEVER assume backup integrity without verification
4. ALWAYS use protection mechanisms
5. NEVER mix production and development operations

## Violation Response

If I detect ANY violation of these measures:
1. Stop all operations
2. Document the violation
3. Review security measures
4. Implement additional protections
5. Update documentation

Remember: Security is not optional. These measures exist because of real incidents and MUST be followed without exception. 