import os
import chainlit as cl
from src.duckdb_utils import run_sql, get_table_schema
from src.agent import generate_sql, summarize_result

# Path to your main Parquet data file
PARQUET_PATH = os.path.join(os.getcwd(), "data", "2019-Nov.parquet")

@cl.on_message
async def handle_message(message):
    question = message.content
    table_schema = get_table_schema(PARQUET_PATH)
    sql = generate_sql(question, table_schema)
    await cl.Message(content=f"**Generated SQL:**\n```sql\n{sql}\n```").send()
    try:
        result = run_sql(sql, PARQUET_PATH)
        summary = summarize_result(question, result)
        await cl.Message(content=summary).send()
    except Exception as e:
        await cl.Message(content=f"Error running query: {e}").send()
