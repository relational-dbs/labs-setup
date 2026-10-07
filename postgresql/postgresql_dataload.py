# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.6
#   kernelspec:
#     display_name: 2026-02-relational-dbs (3.13.7)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Setup

# %% tags=["parameters"]
POSTGRESQL_START_FROM_SCRATCH = True
DOCKER_INTERNAL_HOST = "host.docker.internal"

POSTGRESQL_NAME = "postgres"
POSTGRESQL_PORT = 5423

POSTGRESQL_WORKDIR = "/"
POSTGRESQL_DATADIR = "/var/lib/postgresql"

POSTGRESQL_INIT_USER = "postgres"
POSTGRESQL_INIT_PASSWORD = "password"

# %% [markdown]
# ### Local work directories
#
# Compute the host working directory and create the `mount/` folder that will be shared with the Postgres container.
#

# %%
import os
from pathlib import Path

LOCALHOST_WORKDIR = f"{os.path.join(os.path.relpath(Path.cwd()))}"
LOCALHOST_DOCKER_MOUNTDIR = os.path.join(LOCALHOST_WORKDIR, "mount")

mount_path = Path(LOCALHOST_DOCKER_MOUNTDIR)
mount_path.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# ### Copy the schemas
#
# Copies the per-dataset SQL schemas into `mount/<POSTGRESQL_NAME>/schemas/` (by default `mount/postgres/schemas/`), the folder `postgresql_infra` mounts into the container.
#

# %%
import shutil

shutil.copytree(
    "schemas",
    os.path.join(LOCALHOST_DOCKER_MOUNTDIR, POSTGRESQL_NAME, "schemas"),
    dirs_exist_ok=True,
)

# %% [markdown]
# ### Delete old Databases

# %%
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} aerolinea
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} amazon
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} banco
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} biblioteca
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} uber
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} youtube
# !docker exec {POSTGRESQL_NAME} dropdb --if-exists --username {POSTGRESQL_INIT_USER} ferrocarril

# %% [markdown]
# ### Create databases
#
# Recreates the seven course databases (aerolinea, amazon, banco, biblioteca, ferrocarril, uber, youtube) after dropping any previous copies.
#

# %%
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} aerolinea
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} amazon
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} banco
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} biblioteca
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} uber
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} youtube
# !docker exec {POSTGRESQL_NAME} createdb --username {POSTGRESQL_INIT_USER} ferrocarril

# %% [markdown]
# ### Import data

# %%
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db aerolinea   -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/aerolinea/aerolinea_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db amazon      -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/amazon/amazon_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db banco       -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/banco/banco_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db biblioteca  -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/biblioteca/biblioteca_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db uber        -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/uber/uber_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db youtube     -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/youtube/youtube_db.sql
# !docker exec {POSTGRESQL_NAME} psql --username {POSTGRESQL_INIT_USER} --db ferrocarril -v ON_ERROR_STOP=1 -f {POSTGRESQL_WORKDIR}/schemas/ferrocarril/ferrocarril_db.sql
