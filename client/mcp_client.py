
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Project folders
PROJECT_DIR = Path(__file__).resolve().parent.parent
SERVER_FILE = PROJECT_DIR / "server" / "mcp_server.py"
LOG_DIR = PROJECT_DIR / "logs"

# Create logs folder if it does not exist
LOG_DIR.mkdir(exist_ok=True)

# Set up audit logging
logging.basicConfig(
    filename=LOG_DIR / "ai_audit.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

# Load API key
load_dotenv(PROJECT_DIR / ".env")
ai = AsyncOpenAI()

MODEL = "gpt-5.5"
MAX_TURNS = 5


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_FILE)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover MCP tools automatically
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

            print(
                "MCP tools connected:",
                [tool.name for tool in mcp_tools.tools]
            )

            print("\nAI Assistant is ready!")
            print("Type 'exit' to stop.\n")

            while True:
                question = input("You: ").strip()

                if question.lower() == "exit":
                    break

                if not question:
                    continue

                # Record user question
                logging.info("USER QUESTION: %s", question)

                response = await ai.responses.create(
                    model=MODEL,
                    instructions=(
                        "You are a helpful assistant. "
                        "Use the available tools when needed. "
                        "Never claim a tool was used if it was not."
                    ),
                    input=question,
                    tools=tools,
                    tool_choice="auto",
                )

                # Limit the number of tool-calling rounds
                for turn in range(MAX_TURNS):
                    calls = [
                        item for item in response.output
                        if item.type == "function_call"
                    ]

                    if not calls:
                        break

                    outputs = []

                    for call in calls:
                        print(f"\n[Calling tool: {call.name}]")

                        arguments = json.loads(call.arguments)

                        # Record tool call
                        logging.info(
                            "TOOL CALLED: %s | ARGUMENTS: %s",
                            call.name,
                            json.dumps(arguments),
                        )

                        result = await session.call_tool(
                            call.name,
                            arguments,
                        )

                        tool_text = "\n".join(
                            part.text
                            for part in result.content
                            if hasattr(part, "text")
                        )

                        # Record tool result
                        logging.info(
                            "TOOL RESULT: %s | %s",
                            call.name,
                            tool_text,
                        )

                        outputs.append({
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": tool_text,
                        })

                    response = await ai.responses.create(
                        model=MODEL,
                        previous_response_id=response.id,
                        input=outputs,
                        tools=tools,
                        tool_choice="auto",
                    )

                answer = response.output_text

                # Record AI response
                logging.info("AI RESPONSE: %s", answer)

                print("\nAssistant:", answer, "\n")


if __name__ == "__main__":
    asyncio.run(main())
