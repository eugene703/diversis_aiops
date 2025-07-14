import duckdb
import pandas as pd

def run_sql(sql: str, parquet_path: str) -> pd.DataFrame:
    query = sql.replace("FROM events", f"FROM '{parquet_path}'")
    con = duckdb.connect()
    result = con.execute(query).fetchdf()
    con.close()
    return result

def get_table_schema(parquet_path: str) -> str:
    con = duckdb.connect()
    df = con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchdf()
    con.close()
    schema = "\n".join(f"{row['column_name']} {row['column_type']}" for _, row in df.iterrows())
    return schema
