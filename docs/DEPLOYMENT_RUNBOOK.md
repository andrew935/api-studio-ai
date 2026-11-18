# Deployment and rollback runbook

This runbook assumes a future production VM using the existing Docker Compose
services. Replace example registry names and URLs with the selected hosting
environment. Do not deploy until backups and restore procedures have been
tested.

## Release requirements

Every release must have:

- an immutable image tag, preferably the Git commit SHA;
- passing Python tests and Docker build in CI;
- a reviewed Alembic migration plan;
- a recorded previous image tag;
- a recent PostgreSQL backup with a verified restore procedure;
- health-check and monitoring access from the deployment environment.

Never deploy only `latest`. An immutable tag makes the running version and
rollback target unambiguous.

## Migration compatibility

Classify every migration before deployment:

### Backward-compatible expand migration

Examples:

- add a nullable column;
- add a column with a safe default;
- add a new table or index;
- keep old columns while new code starts dual-writing.

The previous application image can still run against this schema. Automatic
application rollback is allowed.

### Destructive or contract migration

Examples:

- drop or rename a column used by the previous image;
- tighten a constraint before all data is valid;
- change a data type incompatibly;
- delete or rewrite data.

Automatic image rollback is not sufficient. Schedule these migrations only
after all deployed code has stopped using the old schema. If deployment fails,
stop automation and use a reviewed forward fix or a verified database restore.

Do not run `alembic downgrade` automatically. A downgrade may restore schema
shape without restoring deleted or transformed data.

## Deployment sequence

1. Record the current immutable image tag as `PREVIOUS_IMAGE`.
2. Set `APP_IMAGE` to the new immutable registry tag.
3. Pull the application image.
4. Run Alembic migrations as a one-shot job.
5. If migration fails, stop. Do not replace running API or MCP containers.
6. Recreate API and MCP using the new image.
7. Poll `/health/ready` with a bounded timeout.
8. Confirm Prometheus target health, 5xx rate and latency.
9. Record the deployed image SHA and migration revision.

Example commands after production configuration and secrets are loaded:

```bash
export APP_IMAGE="ghcr.io/OWNER/api-studio-ai:COMMIT_SHA"
docker compose pull api mcp migrate
docker compose run --rm migrate
docker compose up -d --no-deps api mcp
```

Example readiness gate:

```bash
for attempt in 1 2 3 4 5 6; do
    if curl --fail --silent http://127.0.0.1:8000/health/ready; then
        exit 0
    fi
    sleep 5
done
exit 1
```

## Application rollback

Use this only when the migration was classified as backward-compatible:

```bash
export APP_IMAGE="ghcr.io/OWNER/api-studio-ai:PREVIOUS_COMMIT_SHA"
docker compose pull api mcp
docker compose up -d --no-deps api mcp
```

Repeat the readiness gate and confirm error rate and latency. PostgreSQL,
Redis, uploaded objects and queues are not replaced by an application-image
rollback.

## Recovery escalation

Stop automatic deployment and require human review when:

- migration compatibility is unknown;
- a destructive migration already succeeded;
- both the new and previous images fail readiness;
- data integrity checks fail;
- the previous image cannot process jobs created by the new version;
- restoring service would require deleting or rewriting customer data.

Record the incident timeline, image SHAs, Alembic revisions, health results and
recovery decision. Never include access tokens, passwords, document content or
other secrets in the incident record.
