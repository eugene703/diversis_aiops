import os
import anthropic
from src.duckdb_utils import get_table_schema

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)
model = "claude-3-5-haiku-latest"

def generate_sql(question: str, table_schema: str) -> str:
    """Generate SQL using Anthropic Claude given a user question and table schema."""
    prompt = f"""You are a data analyst. Based on the table schema below, write a SQL query (DuckDB dialect) that answers the user's question.
Table schema:
{table_schema}

Question: {question}
SQL:"""
    # Call Claude model (change model name if you have access to a newer one)
    response = client.messages.create(
        model=model,  # or claude-3-sonnet-20240229, or another Claude-3 model
        max_tokens=256,
        temperature=0,
        system="Return only the SQL query, no explanations.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    # Parse the response (ensure you get just the SQL)
    sql = response.content[0].text.strip().split('\n')[0]
    return sql

def summarize_result(question: str, result) -> str:
    if result.empty:
        return "No results found."
    return f"Top results for: **{question}**\n\n{result.head(10).to_markdown()}"
