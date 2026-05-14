import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://org_user:org_pass@db:5432/org_structure"
)