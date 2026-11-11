<<<<<<< HEAD
# MCP Tool-Augmented AI Assistant

## Project Description

This project is an AI assistant that uses MCP tools to answer questions and perform tasks.

The assistant has three tools:

1. **Database Tool:** Reads employee information from a SQLite database.
2. **Weather Tool:** Gets current weather information using the Open-Meteo API.
3. **Calculator Tool:** Performs safe mathematical calculations.

## Technologies Used

- Python
- MCP (Model Context Protocol)
- OpenAI API
- Streamlit
- SQLite
- Open-Meteo API
- Pytest

## Project Features

- AI assistant with tool calling
- Dynamic MCP tool discovery
- Weather information
- Read-only database queries
- Safe mathematical calculations
- Security testing
- Automated tests

## How to Run

1. Activate the virtual environment.
2. Make sure your `.env` file contains your OpenAI API key.
3. Run the Streamlit application:

```powershell
.\.venv2\Scripts\python.exe -m streamlit run app.py
```

4. Open `http://localhost:8501` in your browser.

## Run Automated Tests

```powershell
.\.venv2\Scripts\python.exe -m pytest tests -v
```

## Security

The project includes protections against unsafe SQL operations and unsafe mathematical expressions.

## Testing

Seven automated tests have been created using pytest.
=======
# mcp-agent-tools
>>>>>>> ad337750d16d9cd52eb7d30147a0605a26f815ea
