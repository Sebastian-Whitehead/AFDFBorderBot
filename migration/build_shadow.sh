#!/usr/bin/env bash
# Build the local "shadow" Postgres used by the shared_db tests: production's public/economy/military
# schemas (schema only, read-only dump, no data) plus migration/sql/*.sql. Recreates container afdf-shadow.
# Needs Docker and SUPABASE_DUMP_URL (session pooler string) in .env.test.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p migration/shadow

docker run --rm --env-file .env.test postgres:17 sh -c \
  'pg_dump "$SUPABASE_DUMP_URL" --schema-only --no-owner --no-privileges -n public -n economy -n military' \
  > migration/shadow/schema.sql

docker rm -f afdf-shadow >/dev/null 2>&1 || true
docker run -d --name afdf-shadow -e POSTGRES_PASSWORD=shadow -p 54329:5432 postgres:17 >/dev/null
until docker exec afdf-shadow pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
sleep 2  # the image restarts once after init

docker exec -i afdf-shadow psql -U postgres -v ON_ERROR_STOP=1 < migration/shadow_stubs.sql
# "schema public already exists" is expected; anything else is worth reading
docker exec -i afdf-shadow psql -U postgres < migration/shadow/schema.sql 2> migration/shadow/restore-errors.txt || true
for f in migration/sql/*.sql; do docker exec -i afdf-shadow psql -U postgres -v ON_ERROR_STOP=1 < "$f"; done

grep -v 'schema "public" already exists' migration/shadow/restore-errors.txt || true
echo "shadow DB ready. Add to .env.test:"
echo "TEST_SHARED_DATABASE_URL=postgresql+asyncpg://postgres:shadow@localhost:54329/postgres"
