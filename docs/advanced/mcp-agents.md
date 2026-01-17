# AI Agents & MCP

FastUCP has built-in support for the **Model Context Protocol (MCP)**. This allows AI Agents (like Claude, Gemini, or OpenAI based assistants) to connect directly to your store's API as a "Tool".



## Enabling MCP

To enable the MCP server, simply set the flag when initializing FastUCP:

```python
app = FastUCP(
    ...,
    enable_mcp=True
)
```
This automatically exposes an endpoint at /mcp.

## ⚙️ How it Works

FastUCP acts as a bridge between the stateless HTTP protocol and the stateful, conversational nature of AI Agents using the **Model Context Protocol (MCP)**.



### 1. The Handshake & Initialization
When an AI Agent connects to your server (e.g., via `http://127.0.0.1:8000/mcp`), FastUCP establishes a JSON-RPC 2.0 connection. It identifies itself as an MCP-compliant server and negotiates capabilities.

### 2. Automatic Tool Discovery
This is where the magic happens. FastUCP inspects your registered routes and automatically converts them into **MCP Tools** that the AI can understand.

* **Reflection:** It reads your Python type hints and Pydantic models.
* **Schema Generation:** It generates strict JSON Schemas for input arguments.
* **Registration:** Functions decorated with `@app.checkout` or `@app.discovery` are exposed as tools like `create_session` or `search_products`.

### 3. Execution & Routing
When the Agent decides to perform an action (e.g., *"I need to search for a Pixel phone"*):

1.  The Agent sends a `tools/call` JSON-RPC request.
2.  FastUCP intercepts this request and routes it to your corresponding Python function.
3.  Your standard Python logic executes (fetching data, calculating prices).
4.  The result is serialized back into a structured format the AI can process.

```mermaid
sequenceDiagram
    autonumber
    participant Agent as AI Agent (Client)
    participant FastUCP as FastUCP Server
    participant Logic as Your Python Code

    Note over Agent, FastUCP: 1. Handshake
    Agent->>FastUCP: Initialize Connection
    FastUCP-->>Agent: Server Capabilities

    Note over Agent, FastUCP: 2. Discovery
    Agent->>FastUCP: tools/list
    FastUCP-->>Agent: Returns Tools (search_products, create_session)

    Note over Agent, Logic: 3. Execution
    Agent->>FastUCP: Call Tool: search_products(query="Pixel")
    FastUCP->>Logic: Execute Python Function
    Logic-->>FastUCP: Return List[Product]
    FastUCP-->>Agent: Return JSON Result


```python
from fastucp import FastUCPClient

# Connect using 'mcp' transport
client = FastUCPClient(base_url="[http://127.0.0.1:8000](http://127.0.0.1:8000)", transport="mcp")

# The client handles the JSON-RPC wrapping automatically
results = client._send_mcp_tool_call(
    "search_products", 
    {"query": "Pixel"}
)

print(results)
```