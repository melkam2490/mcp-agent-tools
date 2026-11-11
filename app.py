
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ==========================================
# 1. PROJECT SETTINGS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
SERVER_FILE = PROJECT_DIR / "server" / "mcp_server.py"

load_dotenv(PROJECT_DIR / ".env")

MODEL = "gpt-5.5"
MAX_TURNS = 5


# ==========================================
# 2. STREAMLIT PAGE SETTINGS
# ==========================================

st.set_page_config(
    page_title="MCP AI Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 MCP Tool-Augmented AI Assistant")

st.write(
    "Ask questions about weather, math, "
    "or the employee database."
)


# ==========================================
# 3. SAVE CHAT HISTORY
# ==========================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "previous_response_id" not in st.session_state:
    st.session_state.previous_response_id = None

if "available_tools" not in st.session_state:
    st.session_state.available_tools = []


# ==========================================
# 4. MCP SERVER SETTINGS
# ==========================================

def get_server_parameters():

    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_FILE)],
    )


# ==========================================
# 5. DISCOVER MCP TOOLS
# ==========================================

async def discover_tools():

    async with stdio_client(
        get_server_parameters()
    ) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.list_tools()

            return result.tools


# ==========================================
# 6. CALL MCP TOOL
# ==========================================

async def call_mcp_tool(tool_name, arguments):

    async with stdio_client(
        get_server_parameters()
    ) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments
            )

            output = "\n".join(
                item.text
                for item in result.content
                if hasattr(item, "text")
            )

            return output, result.isError


# ==========================================
# 7. AI ASSISTANT
# ==========================================

async def ask_ai(question, previous_response_id=None):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is missing from your .env file."
        )

    ai = AsyncOpenAI(api_key=api_key)

    # Connect to MCP server
    async with stdio_client(
        get_server_parameters()
    ) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            # Discover tools dynamically
            mcp_tools = await session.list_tools()

            tools = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                    "strict": False,
                }
                for tool in mcp_tools.tools
            ]

            instructions = (
                "You are a helpful assistant. "
                "Use available tools when needed. "
                "Never claim a tool was used if it was not."
            )

            request = {
                "model": MODEL,
                "instructions": instructions,
                "input": question,
                "tools": tools,
                "tool_choice": "auto",
            }

            if previous_response_id:
                request["previous_response_id"] = (
                    previous_response_id
                )

            response = await ai.responses.create(**request)

            called_tools = []

            # Maximum five tool-calling rounds
            for turn in range(MAX_TURNS):

                calls = [
                    item
                    for item in response.output
                    if item.type == "function_call"
                ]

                if not calls:
                    break

                outputs = []

                for call in calls:

                    arguments = json.loads(call.arguments)

                    # Execute the requested MCP tool
                    tool_result = await session.call_tool(
                        call.name,
                        arguments
                    )

                    tool_output = "\n".join(
                        item.text
                        for item in tool_result.content
                        if hasattr(item, "text")
                    )

                    called_tools.append({
                        "name": call.name,
                        "arguments": arguments,
                        "result": tool_output,
                        "error": tool_result.isError,
                    })

                    outputs.append({
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": tool_output,
                    })

                # Send tool results back to AI
                response = await ai.responses.create(
                    model=MODEL,
                    instructions=instructions,
                    previous_response_id=response.id,
                    input=outputs,
                    tools=tools,
                    tool_choice="auto",
                )

            return (
                response.output_text,
                response.id,
                called_tools
            )


# ==========================================
# 8. SIDEBAR: TOOL INSPECTOR
# ==========================================

with st.sidebar:

    st.header("Tool Inspector")

    if st.button("Discover MCP Tools"):

        try:

            tools = asyncio.run(discover_tools())

            st.session_state.available_tools = tools

            st.success("MCP tools discovered successfully!")

        except Exception as error:

            st.error(f"Tool discovery failed: {error}")

            st.code(traceback.format_exc())

    for tool in st.session_state.available_tools:

        st.write(f"**{tool.name}**")

        st.caption(tool.description)

    st.divider()

    st.caption(
        "MCP server: connected when a request runs"
    )


# ==========================================
# 9. DISPLAY CHAT HISTORY
# ==========================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])


# ==========================================
# 10. CHAT INPUT
# ==========================================

question = st.chat_input("Ask me something...")


if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):

        st.write(question)

    with st.chat_message("assistant"):

        with st.spinner("Thinking and checking tools..."):

            try:

                answer, response_id, called_tools = asyncio.run(
                    ask_ai(
                        question,
                        st.session_state.previous_response_id
                    )
                )

                st.session_state.previous_response_id = response_id

                st.write(answer)

                # Display tool calls
                if called_tools:

                    with st.expander("View tool calls"):

                        for item in called_tools:

                            st.write(
                                f"**Tool:** {item['name']}"
                            )

                            st.write(
                                "Arguments:",
                                item["arguments"]
                            )

                            st.write(
                                "Result:",
                                item["result"]
                            )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception as error:

                st.error(
                    f"Something went wrong: {error}"
                )

                st.code(traceback.format_exc())


# ==========================================
# 11. SECURITY TEST PANEL
# ==========================================

with st.expander("🔒 Security Test Panel"):

    st.write(
        "Test that unsafe SQL and math expressions are rejected."
    )

    if st.button("Run Security Tests"):

        tests = [

            (
                "Block SQL DELETE",
                "query_database",
                {"sql": "DELETE FROM employees"},
            ),

            (
                "Block multiple SQL statements",
                "query_database",
                {
                    "sql": (
                        "SELECT * FROM employees; "
                        "DROP TABLE employees"
                    )
                },
            ),

            (
                "Block unsafe Python code",
                "calculate",
                {
                    "expression": (
                        "__import__('os').system('whoami')"
                    )
                },
            ),

            (
                "Block excessive exponent",
                "calculate",
                {"expression": "2 ** 100"},
            ),

        ]

        for name, tool_name, arguments in tests:

            try:

                result, is_error = asyncio.run(
                    call_mcp_tool(
                        tool_name,
                        arguments
                    )
                )

                passed = (
                    result.startswith("Error:")
                    or (
                        tool_name == "query_database"
                        and result.startswith("Database error:")
                    )
                )

                if passed:

                    st.success(f"PASS: {name}")

                else:

                    st.error(
                        f"FAIL: {name} — {result}"
                    )

            except Exception as error:

                st.error(
                    f"ERROR: {name} — {error}"
                )
