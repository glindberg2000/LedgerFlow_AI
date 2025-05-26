## SearXNG Configuration for All Environments

LedgerFlow uses SearXNG for federated search. You must configure the `SEARXNG_HOST` environment variable to point to the correct SearXNG instance for your environment:

| Environment         | Value for SEARXNG_HOST           | Notes                                  |
|---------------------|----------------------------------|----------------------------------------|
| Host (local dev)    | http://localhost:8888            | SearXNG must be running on host        |
| Docker Compose      | http://searxng:8080              | SearXNG service in same Compose stack  |
| Docker container    | http://host.docker.internal:8888 | Access host SearXNG from container     |
| Cloud/Remote        | http://<public-ip>:8888          | SearXNG must be exposed to internet    |

- Set this in your `.env.dev` or as an environment variable.
- See `.env.dev` for commented-out examples.

### Troubleshooting
- If using a remote IDE (e.g., Codespaces, Windsurf), use `host.docker.internal` if supported, or expose SearXNG on a public IP.
- If you get connection errors, check that SearXNG is running and accessible from your environment.
- For advanced setups, consult the Memory Bank or ask the DB manager. 