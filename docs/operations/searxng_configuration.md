# SearXNG Configuration and Troubleshooting

## Current Configuration

The LedgerFlow application uses SearXNG for web searches. The setup involves:

- Container name: `ledger-dev-searxng-1`
- Internal port: 8080
- External port: 8888
- Network: Same Docker network as Django application

### Key Settings

```yaml
# SearXNG settings.yml
use_default_settings: true

server:
    secret_key: "b636835ed4ee4c9b85dcaaa4d0153b25f7043112fc21dabf302e24960cb0f2ae"
    limiter: false
    image_proxy: false
    method: "POST"
    port: 8080
    bind_address: "0.0.0.0"
```

### Django Configuration

The Django application connects to SearXNG using:
- URL: `http://ledger-dev-searxng-1:8080`
- Method: POST
- Format: JSON

## Known Issues

1. **Rate Limiting (2025-04-24)**
   - Issue: 429 TOO MANY REQUESTS errors when using Xfinity network
   - Potential causes:
     - ISP-level rate limiting
     - SearXNG's upstream search providers rate limiting
   - Workaround: Test on different network connection
   - Status: Under investigation

2. **Container Networking (2025-04-24)**
   - Issue: Django unable to reach SearXNG via localhost
   - Resolution: Updated configuration to use Docker container name instead of localhost
   - Root cause: Container isolation - localhost refers to the container itself

## Recovery Procedures

If SearXNG configuration is lost:

1. Ensure settings.yml is properly mounted:
   ```yaml
   volumes:
     - ./searxng/settings.yml:/etc/searxng/settings.yml
   ```

2. Verify Docker network connectivity:
   ```bash
   docker network inspect ledgerflow_default
   ```

3. Test SearXNG connectivity from Django:
   ```python
   import requests
   response = requests.post('http://ledger-dev-searxng-1:8080/search', 
                          params={'q': 'test', 'format': 'json'})
   ```

## Maintenance Notes

- Regular backups of settings.yml should be maintained
- Monitor rate limiting issues and adjust as needed
- Consider implementing request caching if rate limiting persists 