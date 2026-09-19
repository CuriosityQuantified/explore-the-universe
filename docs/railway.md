# Railway deployment

The repository contains separate FastAPI and Next.js applications. Configure
each Railway service explicitly; the web service must not build the root
Python Dockerfile.

| Service | Root directory | Railway config file | Healthcheck |
| --- | --- | --- | --- |
| `api` | `/` | `/railway.json` | `/health` |
| `web` | `/web` | `/web/railway.json` | `/` |

Set both **Root Directory** and **Railway Config File** in the service settings.
Railway resolves the config file path from the repository root, independently
of the service root directory. The files supply the build and start commands.
See [Railway's monorepo documentation](https://docs.railway.com/deployments/monorepo).

For the production web service:

- Set `PORT=3000` and the public domain's target port to `3000`.
- Set `API_INTERNAL_URL=http://api.railway.internal:8000`, matching the API
  service's listening port. This variable must be available during the web
  build because Next.js builds its `/api/*` rewrite into the production bundle.
- Leave `NEXT_PUBLIC_API_URL` unset to use the same-origin API proxy.
- Redeploy after changing service settings or `API_INTERNAL_URL`.

The public site is <https://web-production-97566.up.railway.app/>. After deploying,
check `/`, `/dashboard`, and `/api/observations`; a successful homepage alone
does not prove that the private backend connection works.

## Troubleshooting

If the web build installs Python packages or reports a healthcheck at `/health`,
it is using the root API configuration. Correct both web service paths above.
The Next.js application serves `/` and does not define `/health`.

For backend startup failures, check migrations and Neo4j connectivity. The API
healthcheck also requires PostgreSQL, Redis, and S3/MinIO to be available.

The manual **Railway diagnostics** GitHub Actions workflow reads service settings
and recent deployment logs. It accepts `RAILWAY_API_TOKEN` (or `RAILWAY_TOKEN`)
and `RAILWAY_PROJECT_ID` repository secrets. It masks service credential values
before printing logs and does not change service configuration or deploy code.
