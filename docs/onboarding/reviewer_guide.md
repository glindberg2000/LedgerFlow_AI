# Reviewer Onboarding Guide

Welcome to the LedgerFlow team as a Reviewer! This guide will help you understand your role, responsibilities, and the tools you'll need to be effective.

## Your Role

As a Reviewer for LedgerFlow, you are responsible for:

1. Reviewing code changes for quality, functionality, and adherence to standards
2. Ensuring documentation is complete and accurate
3. Verifying that tests are adequate and passing
4. Identifying potential security, performance, or scalability issues
5. Approving or requesting changes to pull requests
6. Helping maintain high-quality codebase and documentation
7. Enforcing security protocols for dockerized environments
8. Validating proper MPC tools integration

## Essential Information

### Code Quality Standards

LedgerFlow maintains high standards for code quality:

- **Python**: PEP 8 style guide, type hints, docstrings
- **Django**: Django coding style, proper model design, security best practices
- **Documentation**: Clear, complete, and up-to-date
- **Testing**: Adequate test coverage, meaningful tests
- **Security**: OWASP best practices, secure coding patterns
- **Performance**: Efficient queries, optimized code
- **Dockerized Workflow**: Proper isolation and configuration
- **MPC Tools**: Correct integration and usage

### Memory Bank

The Memory Bank (`cline_docs/`) is a critical part of our documentation system:

- `productContext.md` - Product overview and context
- `activeContext.md` - Current focus and recent changes
- `systemPatterns.md` - Architecture patterns and decisions
- `techContext.md` - Technical details and constraints
- `progress.md` - Project progress and status

After significant changes, ensure the Memory Bank is updated.

## Required Access

You'll need access to:

- [ ] GitHub repository (with reviewer permissions)
- [ ] Discord/Matrix channels
- [ ] Task Manager admin access
- [ ] Development environment credentials (`.env.dev`)
- [ ] Dockerized reviewer environment
- [ ] Admin dashboard credentials (optional)
- [ ] MPC tools admin access

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

3. Start your dockerized reviewer environment:
```bash
make reviewer-session
```

4. Additional review tools (recommended):
   - VS Code or PyCharm for code review
   - Python linting tools (flake8, black, etc.)
   - Django debug toolbar
   - Git GUI client with diff tools
   - MPC tools integrations

## Key Workflows

### Code Review Workflow

1. Review pull request on GitHub
2. Check out the branch in your dockerized environment:
```bash
git fetch origin
git checkout feature/branch-name
```

3. Start development environment:
```bash
make dev
```

4. Review code for:
   - Code quality
   - Functionality
   - Test coverage
   - Documentation
   - Security
   - Performance
   - Proper MPC tools usage

5. Run tests:
```bash
docker compose -f docker-compose.dev.yml exec django python manage.py test
```

6. Test the feature manually
7. Use MPC tools to validate integration points
8. Provide feedback in the pull request
9. Approve or request changes
10. Update Task Manager status

### Documentation Review Workflow

1. Check for updates to:
   - Code docstrings
   - README.md and other docs
   - API documentation
   - User guides
   - Memory Bank
   - MPC tools configuration

2. Ensure documentation is:
   - Complete
   - Accurate
   - Clear
   - Up-to-date
   - Security-conscious

3. Request updates if necessary

### Security Review Workflow

1. Check for common vulnerabilities:
   - SQL injection
   - XSS
   - CSRF protection
   - Authentication/authorization issues
   - Sensitive data exposure
   - Security misconfigurations
   - Docker security issues
   - MPC tools configuration vulnerabilities

2. Use security tools if applicable
3. Provide feedback on security issues
4. Validate dockerized environment security

## Review Checklist

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Functions/classes have proper docstrings
- [ ] Error handling is appropriate
- [ ] Tests are included and passing
- [ ] No security vulnerabilities
- [ ] No performance issues
- [ ] No duplication of code
- [ ] Code is maintainable
- [ ] Proper MPC tools integration
- [ ] Docker configuration is secure

### Documentation Review Checklist

- [ ] Documentation is complete
- [ ] Documentation is accurate
- [ ] Documentation is clear
- [ ] Memory Bank is updated (if necessary)
- [ ] API documentation is complete
- [ ] User guides are updated (if applicable)
- [ ] MPC tools usage is documented

### Security Review Checklist

- [ ] Authentication is handled properly
- [ ] Authorization checks are in place
- [ ] Input validation is appropriate
- [ ] SQL queries are parameterized
- [ ] Sensitive data is protected
- [ ] Security headers are configured
- [ ] Docker images use minimal permissions
- [ ] MPC tools are configured securely

## Important Safety Protocols

As a Reviewer, you should understand and enforce these critical safety measures:

1. **Volume Protection**:
   - Database volumes are protected from accidental deletion
   - Code should never use raw `docker compose down -v` commands
   - Always use `make` commands or the safety wrapper (`ledger_docker`)

2. **Backup System**:
   - Ensure changes don't interfere with the backup system
   - Verify that new features include appropriate backup/restore support
   - Check that backups can be safely restored in dockerized environments

3. **Code Safety**:
   - Check for potential data loss scenarios
   - Verify transactions and atomic operations
   - Ensure proper error handling and recovery
   - Validate MPC tools integration points

4. **Dockerized Environment Safety**:
   - Verify container isolation
   - Check for privileged mode usage
   - Validate volume mounts
   - Review image security

## MPC Tools Integration

As a Reviewer, you'll need to understand how our MPC tools are integrated:

### Task Manager Integration
- Review all tasks linked to pull requests
- Ensure task status is accurate
- Verify task requirements are met
- Update task status after review

### GitHub Integration
- Enforce branch protection rules
- Ensure PR templates are followed
- Review commit history and messages
- Validate PR descriptions

### Discord Integration
- Monitor build and test notifications
- Track deployment status
- Communicate review findings
- Coordinate with team members

### PostgreSQL Integration
- Validate database migrations
- Review query performance
- Check schema changes
- Ensure data integrity

## Required Credentials

The following credentials are not stored in the repository and must be obtained separately:

- Development environment variables (`.env.dev`)
- GitHub credentials with reviewer permissions
- Discord/Matrix access
- Task Manager admin access
- Admin dashboard credentials (optional)
- MPC tools admin credentials

## First Week Tasks

- [ ] Review the Memory Bank (`cline_docs/`)
- [ ] Set up local development environment
- [ ] Configure your dockerized reviewer session
- [ ] Set up MPC tools access
- [ ] Review recent pull requests
- [ ] Get familiar with the codebase
- [ ] Learn the review process
- [ ] Join code review discussions
- [ ] Start reviewing simple pull requests
- [ ] Validate MPC tools integrations

## Contact Information

For access to credentials or with questions about your role, please contact:
- Team Lead: [Name and contact information to be provided separately] 