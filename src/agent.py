import os
import getpass
import duckdb
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langgraph.graph import add_messages
from langgraph.func import task, entrypoint
from langchain_experimental.tools.python.tool import PythonREPLTool


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
            + "- In the JSON, do NOT escape single quotes in your SQL. Only use double quotes for JSON and single quotes for SQL as normal. Do not output any backslashes unless absolutely necessary (e.g., for newlines in SQL)."
            + "In DuckDB, DESCRIBE can't be used directly on read_parquet(). Instead, you can do:"
            + "DESCRIBE SELECT * FROM read_parquet('/home/echo/diversis_aiops/data/2019-Nov.parquet')"            
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

# Define python repl object that can do .run()
@tool
def python_repl_loop(code: str, max_retries: int = 2) -> dict:
    """
    Execute Python code using LangChain's PythonREPLTool with automatic retry logic.

    This function attempts to execute the provided Python code using LangChain's PythonREPLTool.
    If an error occurs during execution, it will retry the code up to `max_retries` times before returning an error message.

    Parameters
    ----------
    code : str
        The Python code to execute.
    max_retries : int, optional
        The maximum number of additional attempts to make if execution fails (default is 2).

    Returns
    -------
    dict
        {"result": ...} containing the output of the successfully executed code, 
        or {"error": ...} with the last error message if all attempts fail.
    """
    python_repl = PythonREPLTool()
    attempt = 0
    error_msg = ""
    while attempt <= max_retries:
        try:
            result = python_repl.run(code)
            return {"result": result}
        except Exception as e:
            error_msg = str(e)
            attempt += 1
    return {"error": f"All {max_retries+1} attempts failed. Last error: {error_msg}"}


## wrap them up together
tools = [query_db, python_repl_loop]
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
                If the user asks for a chart or visualization, use the `python_repl_loop` tool to write Python code that visualizes the dataframe.
                Find the best way to visualize the data set given the user's intent with their question.
                Use `python_repl_loop` ONLY for visualization tasks. If you need the underlying data, use `query_db` to fetch the data and then feed it to `python_repl`.
                When you generate a chart or image, always save it to a session-specific directory inside the .chainlit/tmp/ folder in the current working directory. 
                Use the current date (formatted as YYYY-MM-DD, for example, "2024-07-16") as the session ID.
                The directory path should be .chainlit/tmp/session_\{current_date\}/, where {current_date} is today's date.
                * The directory path should be .chainlit/tmp/session_\{session_id\}/, where {session_id} is a unique identifier for the session.                
                * Be sure to create the tmp and session-specific subfolder if they do not already exist (os.makedirs(..., exist_ok=True)).
                * Name the file clearly, such as chart.png, output.png, etc.
                * Return only the relative or absolute file path to the saved image, so it can be accessed or displayed in the app.

                Example (Python with matplotlib):
                ```python
                import os
                from datetime import date
                session_id = date.today().isoformat()  # e.g., '2024-07-16'
                session_dir = os.path.join('.chainlit', 'tmp', f'session_{session_id}')
                os.makedirs(session_dir, exist_ok=True)
                file_path = os.path.join(session_dir, 'chart.png')
                # Save your figure
                plt.savefig(file_path)
                print(f"Image saved to: {file_path}")```
                If the tool allows, return the file path or a file URL for later retrieval by the app or UI.
                Do not output a base64 string—only output the file path to the saved image.
                
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
