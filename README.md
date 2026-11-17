# API Studio AI

## Docker

The API, MCP server, and migration job use one immutable application image with
different commands. PostgreSQL uses its own pinned image.

Copy `.env.example` to `.env`, replace `POSTGRES_PASSWORD` and
`JWT_SECRET_KEY`, then build and start the local stack:

```powershell
docker compose up --build --wait
```

The services are bound to localhost:

- FastAPI: `http://127.0.0.1:8000`
- MCP: `http://127.0.0.1:8001/mcp`
- PostgreSQL: `127.0.0.1:5433`

The one-shot `migrate` container must complete successfully before the API and
MCP containers start. Application containers run as a non-root user with a
read-only root filesystem, all Linux capabilities dropped, and only `/tmp` and
the upload volume writable.

If host port `8000` is already used, set both `API_HOST_PORT` and
`PUBLIC_BASE_URL` to another local port, for example `8002`.

## Bootstrap the first tenant administrator

The bootstrap command creates the first tenant and its admin in one database
transaction. It is a local administrative command, not a public API endpoint.

1. Copy `.env.example` to `.env` and replace every placeholder, especially
   `DATABASE_URL` and `JWT_SECRET_KEY`.
2. Apply the database migrations from the project root:

   ```powershell
   backend/.venv/Scripts/python.exe -m alembic upgrade head
   ```

3. Run the bootstrap command:

   ```powershell
   backend/.venv/Scripts/python.exe -m backend.scripts.bootstrap_admin
   ```

The command prompts for the law firm name, admin email, password, and password
confirmation. The password is hidden while typing and only its Argon2 hash is
stored. If admin creation fails, tenant creation is rolled back.

## Local PostgreSQL

Start the pinned PostgreSQL container and wait for its health check:

```powershell
docker compose up -d --wait postgres
```

The database is exposed on `127.0.0.1:5433` because port `5432` may already
be used by another local PostgreSQL installation. Copy `.env.example` to
`.env` so Docker Compose and the application use the same local password.

Set `DATABASE_URL` in `.env`, then apply migrations:

```powershell
backend/.venv/Scripts/python.exe -m alembic upgrade head
```

Run the explicit PostgreSQL integration test:

```powershell
$env:TEST_POSTGRES_URL = $env:DATABASE_URL
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_postgres_integration.py -q
```

Stop the container without deleting its named data volume:

```powershell
docker compose stop postgres
```

## File storage

Local development defaults to `STORAGE_BACKEND=local` and stores synthetic test
files under `LOCAL_STORAGE_PATH`. Production can use a private S3 bucket:

```env
STORAGE_BACKEND=s3
S3_BUCKET=your-private-document-bucket
S3_REGION=us-east-1
```

`S3_ENDPOINT_URL` is optional for S3-compatible providers. AWS credentials are
not passed in application code; Boto3 uses its standard credential provider
chain, such as a local AWS profile or an IAM role in production.

Stored objects use server-generated keys scoped by tenant and upload request.
The original customer filename is metadata only and never controls the object
key.

## Read-only MCP document search

The project exposes one small Streamable HTTP MCP integration for authenticated,
read-only document retrieval. It reuses the same JWT, active-user database check,
tenant-scoped retrieval service, and approved-document filter as the API.
`user_id` and `tenant_id` are never MCP tool arguments.

Start the API, obtain an access token from `POST /api/v1/auth/login`, and run the
MCP resource server separately:

```powershell
backend/.venv/Scripts/python.exe -m backend.scripts.run_mcp
```

The local endpoint is `http://localhost:8001/mcp`. Configure a compatible MCP
client to send the API access token as a Bearer token. This is a resource-server
integration using the project's existing login flow; a production remote client
that requires OAuth discovery and dynamic authorization needs a dedicated OAuth
authorization-server integration.
