import os
import getpass
import duckdb
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langgraph.graph import add_messages
from langgraph.func import task, entrypoint

from langchain_core.messages import (
    SystemMessage,
    BaseMessage,
    ToolCall,
    ToolMessage,
)

## define what model to use
model = "claude-3-5-haiku-latest"

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("ANTHROPIC_API_KEY")

try:
    with open('src/data_context.txt', 'r') as file:
        DATA_CONTEXT = file.read()
except FileNotFoundError:
    print("Error: 'data_context.txt' not found.")

try:
    with open('src/schema.txt', 'r') as file:
        SCHEMA = file.read()
except FileNotFoundError:
    print("Error: 'schema.txt' not found.")

PARQUET_PATH = os.path.join(os.getcwd(), "data", "2019-Nov.parquet")

## initialize llm and tracer
llm = ChatAnthropic(model=model)


# Prepare a single-field parser schema for SQL
_response_schemas = [
    ResponseSchema(
        name="sql",
        description="A DuckDB-compatible SELECT query that answers the user's question"
    )
]
_parser = StructuredOutputParser.from_response_schemas(_response_schemas)
_format_instructions = _parser.get_format_instructions()

## Define tools
@tool
def query_db(question: str, max_retries: int = 2) -> dict:
    """
    Generate and execute a DuckDB SQL query over a parquet file. Retries up to `max_retries` times if the generated query fails.

    Parameters
    ----------
    question : str
        The user's natural-language business question.
    max_retries : int
        Number of additional attempts to make with error feedback if query fails.

    Returns
    -------
    dict
        {"data": ...} with results, or {"error": ...} if all attempts fail.
    """
    attempt = 0
    error_msg = ""
    prev_queries = []

    # 1) Build the LLM prompt
    while attempt <= max_retries:
        prompt = (
            _format_instructions
            + "\n\nImportant:\n"
            + "- Output only standard JSON (no triple quotes).\n"
            + "- If your SQL query is multi-line, escape all line breaks with \\n as required by JSON.\n"
            + "- Do NOT output any text before or after the JSON.\n"
            + "- This sql query is for DuckDB, so do not use json_group_array or json_object. stay in DuckDB syntax"
            + "\n\n"
            + "Table schema:\n"
            + f"Table name is read_parquet('{PARQUET_PATH}')\n"
            + SCHEMA
            + "\n\nData context:\n"
            + DATA_CONTEXT
            + f"\n\nQuestion: {question}\n"
        )
        if attempt > 0:
            prompt += (
                f"\n\nThe previous query failed with this error:\n{error_msg}\n"
                + (f"Last attempted query:\n{prev_queries[-1]}\n" if prev_queries else "")
            )

        # print(f"\nquery_db prompt (attempt {attempt+1}):\n{prompt}\n")
        llm_result = llm.invoke(prompt, stop=None)
        raw = llm_result.content
        parsed = _parser.parse(raw)
        sql = parsed["sql"]
        prev_queries.append(sql)

        query = sql.replace("FROM events", f"FROM read_parquet('{PARQUET_PATH}')")

        try:
            con = duckdb.connect()
            print(query)
            df = con.execute(query).fetchdf()
            con.close()
            if df.empty:
                return "No results found."
            return df.head(10).to_markdown(index=False)
        except Exception as e:
            error_msg = str(e)
            attempt += 1
            print(f"Attempt {attempt} failed: {error_msg}")

    return f"All {max_retries+1} attempts failed. Last error: {error_msg}. Please try a different query or try again later."


## wrap them up together
tools = [query_db, ] #build_chart
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(
    tools,
    )


## define main llm

@task
def call_llm(messages: list[BaseMessage]):
    """LLM decides whether to call a tool or not."""
    return llm_with_tools.invoke(
        [
            SystemMessage(
                content="""
                You are a business data analyst agent. 
                Make sure you understand the user's intention before querying the data set, 
                Use tools as needed to answer the user's data questions.
                {tools_by_name}
                """
            )
        ]
        + messages
    )

@task
def call_tool(tool_call: ToolCall):
    """Performs the tool call and returns a ToolMessage."""
    tool = tools_by_name[tool_call["name"]]
    output = tool.invoke(tool_call["args"])
    # Ensure the output is a string!
    if not isinstance(output, str):
        output = str(output)
    return ToolMessage(
        tool_call_id=tool_call["id"],
        content=output
    )

@entrypoint()
def agent(messages: list[BaseMessage]):
    llm_response = call_llm(messages).result()
    print("DEBUG: llm_response.tool_calls =", llm_response.tool_calls)
    while True:
        if not llm_response.tool_calls:
            break
        print("DEBUG: entering tool call loop")
        tool_result_futures = [
            call_tool(tool_call) for tool_call in llm_response.tool_calls
        ]
        tool_results = [fut.result() for fut in tool_result_futures]
        print("DEBUG: tool_results =", tool_results)
        messages = add_messages(messages, [llm_response, *tool_results])
        llm_response = call_llm(messages).result()
    messages = add_messages(messages, llm_response)
    return messages
