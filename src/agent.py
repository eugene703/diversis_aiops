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
    HumanMessage,
    BaseMessage,
    ToolCall,
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
def query_db(question: str) -> dict:
    """
    Generate and execute a DuckDB SQL query over a parquet file.

    Steps:
      1) Ask the LLM (Anthropic/Claude) to produce a single SELECT
         statement in JSON: {"sql": "..."}.
      2) Run that SQL against the CSV via DuckDB's read_parquet.
      3) Return the result as {"data": <col_to_list dict>}.

    Parameters
    ----------
    question : str
        The user's natural-language business question.

    Returns
    -------
    dict
        {"data": <column-name → list of values>} from the query result.
    """
    # 1) Build the LLM prompt
    prompt = (
        _format_instructions
        + "\n\n"
        + "Table schema:\n"
        + SCHEMA
        + "\n\nData context:\n"
        + DATA_CONTEXT
        + f"\n\nQuestion: {question}\n"
    )

    # 2) Invoke the LLM
    llm_result = llm.invoke(list(prompt), stop=None)
    raw = llm_result.generations[0][0].text
    parsed = _parser.parse(raw)
    sql = parsed["sql"]

    # 3) Run the SQL against the CSV
    #    We'll refer to the CSV as `events` in the SQL
    query = sql.replace("FROM events", f"FROM read_parquet('{PARQUET_PATH}')")
    con = duckdb.connect()
    df = con.execute(query).fetchdf()
    con.close()

    return {"data": df.to_dict()}


@tool
def summarize_result(question: str, result) -> str:
    """
    Produce a Markdown summary of the top rows from a query result.

    Parameters
    ----------
    question : str
        The original user question, for context in the summary.
    result : pandas.DataFrame
        The DataFrame returned by running the SQL query.

    Returns
    -------
    str
        A Markdown-formatted string showing the question and the first ten rows
        of the result, or a "No results found." message if empty.
    """
    if result.empty:
        return "No results found."
    return f"Top results for: **{question}**\n\n{result.head(10).to_markdown()}"


## wrap them up together
tools = [query_db, summarize_result, ] #build_chart
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
                Use tools as needed (generate_sql, run_sql, summarize_result) to answer the user's data questions."""
            )
        ]
        + messages
    )

@task
def call_tool(tool_call: ToolCall):
    """Performs the tool call."""
    tool = tools_by_name[tool_call["name"]]
    return tool.invoke(tool_call["args"])

@entrypoint()
def agent(messages: list[BaseMessage]):
    llm_response = call_llm(messages).result()

    while True:
        if not llm_response.tool_calls:
            break

        # Execute tools requested by the LLM
        tool_result_futures = [
            call_tool(tool_call) for tool_call in llm_response.tool_calls
        ]
        tool_results = [fut.result() for fut in tool_result_futures]
        messages = add_messages(messages, [llm_response, *tool_results])
        llm_response = call_llm(messages).result()

    messages = add_messages(messages, llm_response)
    return messages
