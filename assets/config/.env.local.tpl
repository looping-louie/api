# Fernet key used to encrypt provider credentials. Generate with
# python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
LOUIE_ENCRYPTION_KEY=

# SQLite database path. Example: runtime/db/looping-louie.db
LOUIE_DB_PATH=

# Enable local authentication. Example: true
LOUIE_DEV_AUTH=

# User ID used when local authentication is enabled. Example: local-user
LOUIE_DEV_USER_ID=

# Require catalog-version updates when built-in catalog checksums change.
#Example: false
LOUIE_CATALOG_STRICT_VERSIONING=
