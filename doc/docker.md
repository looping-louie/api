# Docker

## Start the API

Create the local configuration if it does not exist, then build and start the
production image:

```sh
make create-config
docker compose up --build
```

The API is available at <http://localhost:2000>. Its OpenAPI documentation is
available at <http://localhost:2000/docs>.

Compose loads `LOUIE_ENCRYPTION_KEY` from `.env.local`. The SQLite database is
stored in the `looping-louie-api-runtime` Docker volume at
`/app/runtime/db/looping-louie.db`, so it remains available after containers
are replaced.

## Release images

Pushing a `vMAJOR.MINOR.PATCH` tag that matches the version in `pyproject.toml`
runs the release workflow. It tests the API, publishes
`ghcr.io/looping-louie/api:<version>`, and creates a GitHub Release.

Published images support `linux/amd64` and `linux/arm64`; Docker selects the
matching image automatically. A Raspberry Pi 4 needs a 64-bit operating system
because 32-bit `linux/arm/v7` is not published.

## Check the API

Show the container status and health state:

```sh
docker compose ps
```

The API reports `healthy` when its OpenAPI document is available at
`/openapi.json` after application startup completes.

## Stop the API

Stop and remove the API container without deleting its database volume:

```sh
docker compose down
```

To remove the persisted database as well:

```sh
docker compose down --volumes
```
