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
# Removes the local `mount/` data when `POSTGRESQL_START_FROM_SCRATCH` is enabled, so the container is recreated with a clean volume.
#

# %%
import shutil

if POSTGRESQL_START_FROM_SCRATCH:
    shutil.rmtree(LOCALHOST_DOCKER_MOUNTDIR, ignore_errors=True)
    Path(LOCALHOST_DOCKER_MOUNTDIR).mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ### Write the PostgreSQL Dockerfile
#
# Generates `postgresql.dockerfile`, which layers PostGIS, `pg_cron`, and `pgvector v0.8.2` on top of the official `postgres:18.1-trixie` image.
#

# %%
import os
from IPython.display import Markdown, display

dockerfile_postgresql_name = "postgresql.dockerfile"

# language=dockerfile
dockerfile_postgresql_contents = f""" 

# Use the official Spark image as the base
FROM postgres:18.1-trixie

# 1. Instalar dependencias para PostGIS y herramientas de compilación
RUN apt-get update && apt-get install -y \\
    postgresql-server-dev-18 \\
    postgresql-18-postgis-3 \\
    postgresql-18-postgis-3-scripts \\
    postgresql-plpython3-18 \\
    build-essential \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# 2. Compilar e instalar pg_cron (Versión compatible con Postgres 18)
RUN cd /tmp && \\
    git clone https://github.com/citusdata/pg_cron.git && \\
    cd pg_cron && \\
    make && \\
    make install && \\
    rm -rf /tmp/pg_cron

# 3. Compilar e instalar pgvector v0.8.2
# Se recomienda usar la versión v0.8.2 ya que es el último tag estable oficial en GitHub
RUN cd /tmp && \\
    git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git && \\
    cd pgvector && \\
    make && \\
    make install && \\
    rm -rf /tmp/pgvector

# 4. Limpieza de paquetes de compilación
RUN apt-get purge -y --auto-remove build-essential git postgresql-server-dev-18
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
    # "image": "postgres:18.1-trixie",
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
# -- Python scripts
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
# -- Python scripts
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
