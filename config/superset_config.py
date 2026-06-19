import os
from urllib.parse import quote_plus

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

_metadata_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")

if _metadata_uri:
    SQLALCHEMY_DATABASE_URI = _metadata_uri
else:
    _db_user = os.environ.get("DATABASE_USER") or os.environ["POSTGRES_USER"]
    _db_password = quote_plus(os.environ.get("DATABASE_PASSWORD") or os.environ["POSTGRES_PASSWORD"])
    _db_host = os.environ.get("DATABASE_HOST", "postgres")
    _db_port = os.environ.get("DATABASE_PORT", "5432")
    _db_name = os.environ.get("DATABASE_DB", "superset")

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{_db_user}:{_db_password}@"
        f"{_db_host}:{_db_port}/{_db_name}"
    )
