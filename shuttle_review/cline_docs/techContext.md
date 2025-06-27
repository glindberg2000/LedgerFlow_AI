[MEMORY BANK: ACTIVE]
# Technical Context

## Technology Stack

### Backend
- **Framework**: Django 5.2
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery
- **Search**: PostgreSQL Full-text Search
- **API**: Django REST Framework

### Frontend
- **Framework**: Django Templates
- **CSS Framework**: Bootstrap
- **JavaScript**: Vanilla JS
- **Asset Pipeline**: Django Static Files

### Infrastructure
- **Containerization**: Docker
- **Web Server**: Nginx
- **Process Manager**: Gunicorn
- **Version Control**: Git
- **CI/CD**: GitHub Actions

## Development Environment

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Git

### Local Setup
1. Clone repository
2. Copy `.env.example` to `.env.dev`
3. Configure environment variables
4. Build Docker containers
5. Run migrations
6. Create superuser
7. Start development server

### Environment Variables
- `DEBUG`: Debug mode flag
- `SECRET_KEY`: Django secret key
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `ALLOWED_HOSTS`: Allowed host names
- `MEDIA_ROOT`: Media file storage path
- `STATIC_ROOT`: Static file collection path

## Technical Constraints

### Performance Requirements
- Document processing < 30s
- Page load time < 2s
- API response time < 500ms
- Search results < 1s
- Concurrent users: 100+

### Security Requirements
- HTTPS only
- JWT authentication
- Role-based access control
- Data encryption at rest
- Regular security audits
- Secure file storage

### Scalability Requirements
- Horizontal scaling support
- Load balancing ready
- Database replication support
- Caching implementation
- Asynchronous task processing

### Compliance Requirements
- GDPR compliance
- Data retention policies
- Audit logging
- Backup requirements
- Access control policies

## Development Workflow

### Code Management
- Feature branches
- Pull request reviews
- Automated testing
- Code quality checks
- Documentation updates

### Testing Requirements
- Unit test coverage > 80%
- Integration tests
- End-to-end tests
- Performance tests
- Security tests

### Deployment Process
1. Code review
2. Automated tests
3. Staging deployment
4. Manual testing
5. Production deployment
6. Post-deployment verification

### Monitoring
- Application metrics
- Error tracking
- Performance monitoring
- User analytics
- Security monitoring

## External Dependencies

### Third-party Services
- Email service
- Storage service
- Payment processing
- Authentication providers
- Analytics service

### Key Libraries
- django-environ
- django-rest-framework
- celery
- psycopg2-binary
- redis-py

### Integration Points
- REST APIs
- WebSocket connections
- Database connections
- Cache connections
- File system access

## Resource Requirements

### Hardware Requirements
- CPU: 2+ cores
- RAM: 4GB+ minimum
- Storage: 20GB+ minimum
- Network: 100Mbps+

### Software Requirements
- Linux/Unix environment
- Python runtime
- PostgreSQL server
- Redis server
- Docker engine

### Development Tools
- IDE/Code editor
- Git client
- Docker Desktop
- Database client
- API testing tools

## Documentation Requirements

### Code Documentation
- Docstrings
- Type hints
- README files
- API documentation
- Architecture diagrams

### User Documentation
- Installation guide
- User manual
- API reference
- Troubleshooting guide
- Release notes

### System Documentation
- Architecture overview
- Deployment guide
- Security guidelines
- Backup procedures
- Recovery procedures

## Version Control

### Branch Strategy
- main: production
- develop: development
- feature/*: features
- bugfix/*: bug fixes
- release/*: releases

### Release Process
1. Version bump
2. Changelog update
3. Documentation update
4. Release branch
5. Testing
6. Merge to main
7. Tag release

## Backup Strategy

### Backup Types
- Full database dumps
- Incremental backups
- File system backups
- Configuration backups
- Code repository backups

### Backup Schedule
- Daily: incremental
- Weekly: full
- Monthly: archive
- Yearly: long-term storage

## Security Measures

### Authentication
- Password policies
- 2FA support
- Session management
- Token expiration
- Failed login protection

### Authorization
- Role-based access
- Permission system
- Resource isolation
- API authentication
- Access logging

### Data Protection
- TLS encryption
- Data encryption
- Secure storage
- Key management
- Data sanitization

## Performance Optimization

### Database Optimization
- Query optimization
- Index management
- Connection pooling
- Query caching
- Regular maintenance

### Application Optimization
- Code profiling
- Cache implementation
- Async processing
- Resource optimization
- Load balancing

## Monitoring Strategy

### System Monitoring
- Server metrics
- Resource usage
- Error rates
- Response times
- Security events

### Application Monitoring
- User activity
- Feature usage
- Performance metrics
- Error tracking
- Business metrics

## Disaster Recovery

### Recovery Procedures
1. Issue identification
2. Impact assessment
3. Recovery initiation
4. Data restoration
5. Service restoration
6. Verification
7. Documentation

### Recovery Testing
- Regular testing
- Scenario planning
- Documentation review
- Team training
- Process improvement

---
[2025-06-26] Tech Note: All parser submodules (PDF-extractor/dataextractai/parsers) must use module-level loggers with unique names, avoid function-level assignments, and ensure contract-compliant outputs. The recent Wells Fargo Mastercard parser fix is a reference for best practices.
---