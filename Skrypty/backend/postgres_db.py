# backend/postgres_db.py
from sqlalchemy import create_engine, text
import pandas as pd
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
dotenv_path = os.path.join(base_dir, ".env")
load_dotenv(dotenv_path)


DB_URL = os.environ.get("DB_URL")

if not DB_URL:
    raise ValueError("Brak DB_URL w pliku .env")

engine = create_engine(DB_URL)

def save_df_to_db(df, table_name):
    #df.to_sql(table_name, engine, if_exists='replace', index=False)
    with engine.begin() as connection:
        connection.execute(text(f"DELETE FROM {table_name}"))
        df.to_sql(table_name, con=connection, if_exists='append', index=False)

def load_df_from_db(table_name):
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)

def load_df_from_query(query, params=None):
    if params is None:
        params = []
    with engine.connect() as connection:
        return pd.read_sql(query, con=connection, params=params)



"""

CREATE TABLE cenotworstwo_history (
    id SERIAL,
    action_type TEXT,
    changed_at TIMESTAMP DEFAULT now(),
    changed_by TEXT,
    old_data JSONB
);

-- Funkcja logująca zmiany --
CREATE OR REPLACE FUNCTION log_cenotworstwo_changes()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        INSERT INTO cenotworstwo_history (changed_by, action_type, old_data)
        VALUES (
            current_user,
            TG_OP,
            to_jsonb(OLD)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger przypięty do tabeli --
CREATE TRIGGER trg_cenotworstwo_history
AFTER UPDATE OR DELETE ON cenotworstwo
FOR EACH ROW
EXECUTE FUNCTION log_cenotworstwo_changes();


"""