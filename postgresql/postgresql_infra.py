# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: relational-databases-labs (3.13.7.final.0)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Setup

# %% tags=["parameters"]
POSTGRESQL_START_FROM_SCRATCH = False
DOCKER_INTERNAL_HOST = "host.docker.internal"

# Docker Compose project: every `docker compose` command below acts only on this project.
POSTGRESQL_COMPOSE_PROJECT = "postgres-compose"
POSTGRESQL_NAME = "postgres"
POSTGRESQL_PORT = 5423

POSTGRESQL_WORKDIR = "/"
POSTGRESQL_DATADIR = "/var/lib/postgresql"

POSTGRESQL_INIT_USER = "postgres"
POSTGRESQL_INIT_PASSWORD = "password"

# Pinned versions (latest available on 2026-10-10). The image is pinned by digest, and every package by its exact
# Debian version, installed from apt-archive.postgresql.org, which keeps all released versions (apt.postgresql.org
# keeps only the newest one). Everyone who builds gets the same server.
POSTGRESQL_IMAGE = "postgres:18.6-trixie@sha256:74935e72241653ca55e0414067e6d8763aceb8a810eb51b452253ec3dcfc4336"
POSTGRESQL_PACKAGE_VERSION = "18.6-1.pgdg13+2"
POSTGIS_PACKAGE_VERSION = "3.6.4+dfsg-2.pgdg13+1"
PG_CRON_PACKAGE_VERSION = "1.6.8-1.pgdg13+2"
PGVECTOR_PACKAGE_VERSION = "0.8.7-1.pgdg13+1"
POSTGRESQL_IMAGE_TAG = "labs-postgres:18.6-postgis3.6.4-pgcron1.6.8-pgvector0.8.7"

# %% [markdown]
# ### Local work directories
#
# Compute the host working directory and create the `mount/` folder that will be bind-mounted into the Postgres container.
#

# %%
import os
from pathlib import Path

LOCALHOST_WORKDIR = f"{os.path.join(os.path.relpath(Path.cwd()))}"
LOCALHOST_DOCKER_MOUNTDIR = os.path.join(LOCALHOST_WORKDIR, "mount")

mount_path = Path(LOCALHOST_DOCKER_MOUNTDIR)
mount_path.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# # Stop postgresql.docker-compose.yml

# %%
# !docker compose -p {POSTGRESQL_COMPOSE_PROJECT} -f postgresql.docker-compose.yml down -v

# %% [markdown]
# ### Reset local data (only when starting from scratch)
#
# Removes this server's data (`mount/<POSTGRESQL_NAME>/`) when `POSTGRESQL_START_FROM_SCRATCH` is enabled, so the
# container is recreated with a clean volume. Other servers under `mount/` are not touched. On Linux the data files
# belong to the container's `postgres` user, so a container removes them when Python is not allowed to.
#
# Then creates `mount/<POSTGRESQL_NAME>/data` and `mount/<POSTGRESQL_NAME>/schemas` as the current user: if Docker
# created them at start-up they would belong to `root` on Linux, and the dataload notebook could not copy the dumps.
#

# %%
import shutil
import subprocess

server_mount_path = (mount_path / POSTGRESQL_NAME).resolve()
if POSTGRESQL_START_FROM_SCRATCH and server_mount_path.exists():
    try:
        shutil.rmtree(server_mount_path)
    except PermissionError:
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{server_mount_path}:/to-delete", "--entrypoint", "sh",
             POSTGRESQL_IMAGE, "-c", "rm -rf /to-delete/* /to-delete/.[!.]*"],
            check=True,
        )
        shutil.rmtree(server_mount_path)
    print(f"Removed: '{server_mount_path}'")

for subdir in ("data", "schemas"):
    (server_mount_path / subdir).mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ### Write the PostgreSQL Dockerfile
#
# Generates `postgresql.dockerfile`: the official PostgreSQL image pinned by digest, plus PostGIS, PL/Python,
# `pg_cron` and `pgvector` at the exact versions of the parameters cell. The build fails if any installed version
# differs from its pin.
#

# %%
import os
from IPython.display import Markdown, display

dockerfile_postgresql_name = "postgresql.dockerfile"

pinned_packages = {
    "postgresql-18": POSTGRESQL_PACKAGE_VERSION,
    "postgresql-client-18": POSTGRESQL_PACKAGE_VERSION,
    "postgresql-plpython3-18": POSTGRESQL_PACKAGE_VERSION,
    "postgresql-18-postgis-3": POSTGIS_PACKAGE_VERSION,
    "postgresql-18-postgis-3-scripts": POSTGIS_PACKAGE_VERSION,
    "postgresql-18-cron": PG_CRON_PACKAGE_VERSION,
    "postgresql-18-pgvector": PGVECTOR_PACKAGE_VERSION,
}
install_list = " \\\n    ".join(f"{name}={version}" for name, version in pinned_packages.items())
version_checks = " && \\\n    ".join(
    f'test "$(dpkg-query -W -f=\'${{Version}}\' {name})" = "{version}"'
    for name, version in pinned_packages.items()
)

# language=dockerfile
dockerfile_postgresql_contents = f"""
# Official PostgreSQL image, pinned by digest
FROM {POSTGRESQL_IMAGE}

# Every released PGDG package version stays available in apt-archive.postgresql.org (same signing key as the
# image's own PGDG source), so exact versions can always be installed.
RUN echo "deb [ signed-by=/usr/local/share/keyrings/postgres.gpg.asc ] https://apt-archive.postgresql.org/pub/repos/apt trixie-pgdg-archive main" \\
    > /etc/apt/sources.list.d/pgdg-archive.list && \\
    apt-get update && apt-get install -y \\
    {install_list} \\
    && rm -rf /var/lib/apt/lists/*

# Fail the build if any installed version differs from its pin
RUN {version_checks}
"""

with open(
    os.path.join(LOCALHOST_WORKDIR, dockerfile_postgresql_name), "w"
) as dockerfile_postgresql_file:
    dockerfile_postgresql_file.write(dockerfile_postgresql_contents)

print(
    f"Successfully created: '{os.path.relpath(os.path.join(LOCALHOST_WORKDIR,dockerfile_postgresql_name))}'"
)
display(Markdown(f"```dockerfile\n{dockerfile_postgresql_contents}\n```"))

# %% [markdown]
# # Start postgresql.docker-compose.yml

# %%
import os
import yaml
from IPython.display import Markdown, display

node_cpus = "2.0"
node_memory = "2G"
node_start_heap = "1G"
node_max_heap = "2G"

postgresql_compose_dict = {
    "name": POSTGRESQL_COMPOSE_PROJECT,
    "services": {},
    "networks": {"postgres-cluster": {"driver": "bridge"}},
}

postgresql_compose_dict["services"][POSTGRESQL_NAME] = {
    # The tag names the pinned versions: changing a pin changes the tag, so `up` builds the new image.
    "image": POSTGRESQL_IMAGE_TAG,
    "build": {"context": ".", "dockerfile": dockerfile_postgresql_name},
    "container_name": POSTGRESQL_NAME,
    "environment": {
        "POSTGRES_DB": "postgres",
        "POSTGRES_USER": f"{POSTGRESQL_INIT_USER}",
        "POSTGRES_PASSWORD": f"{POSTGRESQL_INIT_PASSWORD}",
        # "DBS_LIST": "bank_db,ecommerce_db,healthcare_db,social_media_db,streaming_service_db",
    },
    "volumes": [
        f"{os.path.join(LOCALHOST_DOCKER_MOUNTDIR, POSTGRESQL_NAME, "data")}:{POSTGRESQL_DATADIR}",
        f"{os.path.join(LOCALHOST_DOCKER_MOUNTDIR, POSTGRESQL_NAME, "schemas")}:{POSTGRESQL_WORKDIR}/schemas",
        f"{os.path.join(LOCALHOST_WORKDIR, "init-db.sh")}:/docker-entrypoint-initdb.d/init-db.sh:ro",
    ],
    "networks": ["postgres-cluster"],
    "ports": [
        f"{POSTGRESQL_PORT}:5432",
    ],
    "extra_hosts": [
        f"{DOCKER_INTERNAL_HOST}:host-gateway",
    ],
    "command": [
        "postgres",
        "-c",
        "shared_preload_libraries=pg_stat_statements,pg_cron",
        "-c",
        "cron.database_name=postgres",
    ],
    "deploy": {"resources": {"limits": {"cpus": node_cpus, "memory": node_memory}}},
    "restart": "unless-stopped",
    "healthcheck": {
        "test": [
            "CMD-SHELL",
            " && ".join(
                [
                    # "test -f /tmp/dbs_initialized",
                    f"pg_isready -h 127.0.0.1 -U {POSTGRESQL_INIT_USER} -d postgres",
                    " ".join(
                        [
                            "for db in $$(echo $$DBS_LIST | tr ',' ' '); do",
                            f'psql -h 127.0.0.1 -U {POSTGRESQL_INIT_USER} -d $$db -c "SELECT 1" || exit 1;'
                            "done",
                        ]
                    ),
                ]
            ),
        ],
        "interval": "5s",
        "timeout": "10s",
        "retries": 10,
        "start_period": "20s",
    },
}

postgresql_compose_yaml_path = os.path.join(
    LOCALHOST_WORKDIR, "postgresql.docker-compose.yml"
)
postgresql_compose_yaml_contents = yaml.dump(
    postgresql_compose_dict, default_flow_style=False, sort_keys=False, indent=4
)
with open(postgresql_compose_yaml_path, "w") as f:
    f.write(postgresql_compose_yaml_contents)

print(f"Successfully created: '{os.path.relpath(postgresql_compose_yaml_path)}'")
display(Markdown(f"```yaml\n{postgresql_compose_yaml_contents}\n```"))

# %% [markdown]
# ### Build and start the stack
#
# Brings the container up in detached mode and waits for the healthcheck to pass.
#

# %%
# # !docker compose -p {POSTGRESQL_COMPOSE_PROJECT} -f postgresql.docker-compose.yml build --no-cache
# !docker compose -p {POSTGRESQL_COMPOSE_PROJECT} -f postgresql.docker-compose.yml up -d --wait

# %% [markdown] vscode={"languageId": "raw"}
# # Plugins commands
#
# ------------------------------------------
#
# -- Show loaded libraries and available extensions
#
# SHOW shared_preload_libraries;
#
# SELECT * FROM pg_available_extensions;
#
# ------------------------------------------
#
# -- Python scripts \
# CREATE EXTENSION IF NOT EXISTS plpython3u;
#
# -- AI and Semantic Search \
# CREATE EXTENSION IF NOT EXISTS vector;
#
# -- Maps and Geometry \
# CREATE EXTENSION IF NOT EXISTS postgis;
#
# -- For "Google"-like search (forgive typos) \
# CREATE EXTENSION IF NOT EXISTS pg_trgm;
#
# -- Ignore accents automatically (camión -> camion) \
# CREATE EXTENSION IF NOT EXISTS unaccent;
#
# -- View performance stats of your queries \
# CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
#
# -- Schedule tasks (CAREFUL: run in the DB defined in the previous command) \
# CREATE EXTENSION IF NOT EXISTS pg_cron;
#
# -- For hierarchies and trees (like categories or comments) \
# CREATE EXTENSION IF NOT EXISTS ltree;
#
# -- For key-value pairs (quick metadata) \
# CREATE EXTENSION IF NOT EXISTS hstore;
#
# ------------------------------------------
#
# -- Python scripts \
# DROP EXTENSION IF EXISTS plpython3u;
#
# -- AI and Semantic Search \
# DROP EXTENSION IF EXISTS vector;
#
# -- Maps and Geometry \
# DROP EXTENSION IF EXISTS postgis;
#
# -- For "Google"-like search (forgive typos) \
# DROP EXTENSION IF EXISTS pg_trgm;
#
# -- Ignore accents automatically (camión -> camion) \
# DROP EXTENSION IF EXISTS unaccent;
#
# -- View performance stats of your queries \
# DROP EXTENSION IF EXISTS pg_stat_statements;
#
# -- Schedule tasks (CAREFUL: run in the DB defined in the previous command) \
# DROP EXTENSION IF EXISTS pg_cron;
#
# -- For hierarchies and trees (like categories or comments) \
# DROP EXTENSION IF EXISTS ltree;
#
# -- For key-value pairs (quick metadata) \
# DROP EXTENSION IF EXISTS hstore;
