import inspect
import json 
import traceback
from typing import get_type_hints
from fastapi import Request
from pydantic import BaseModel

class MCPProtocol:
    def __init__(self, app):
        self.app = app 

    async def handle_request(self, request: Request):
        
        try:
            if request.method == "GET":
                return {"status": "online", "message": "MCP Server is running. Please use POST request with JSON-RPC payload."}
                
            payload = await request.json()
        except Exception: 
            return self._error_response(None, -32700, "Parse error: Invalid JSON was received by the server.")

        method = payload.get("method")
        params = payload.get("params", {})
        req_id = payload.get("id")

        print(f"📡 MCP Request: {method}")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {} 
                    },
                    "serverInfo": {"name": self.app.title, "version": "0.1.2"}
                }
            }

        if method == "notifications/initialized":
             return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            tools = []
            for name, func in self.app._handlers.items():
                description = (func.__doc__ or "UCP Operation").strip()
                
                input_schema = {"type": "object", "properties": {}, "required": []}
                type_hints = get_type_hints(func)
                sig = inspect.signature(func)
                
                for param_name, param in sig.parameters.items():
                    if param_name in ["self", "request", "ucp_agent"]: continue
                    
                    param_type = type_hints.get(param_name, str)
                    
                    json_type = "string"
                    if param_type == int: json_type = "integer"
                    elif param_type == bool: json_type = "boolean"
                    elif param_type == dict: json_type = "object"
                    elif param_type == float: json_type = "number" # Float added
                    
                    input_schema["properties"][param_name] = {
                        "type": json_type,
                        "description": f"Parameter: {param_name}"
                    }
                    
                    if param.default == inspect.Parameter.empty:
                        input_schema["required"].append(param_name)


                tools.append({
                    "name": name,
                    "description": description,
                    "inputSchema": input_schema
                })

            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}


        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            print(f"🛠️  Tool Call: {tool_name} -> Args: {tool_args}")

            if tool_name not in self.app._handlers:
                return self._error_response(req_id, -32601, f"Tool not found: {tool_name}")

            try:
                session_id = tool_args.get("session_id") or tool_args.get("checkout_id") or tool_args.get("id")
                
                result = self.app._call_internal_handler(tool_name, session_id, tool_args)
                
                if isinstance(result, BaseModel):
                    result_data = result.model_dump(mode="json", exclude_none=True)
                else:
                    result_data = result

                json_string = json.dumps(result_data)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json_string 
                            }
                        ],

                        "_raw": result_data 
                    }
                }

            except Exception as e:
                traceback.print_exc()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error executing tool: {str(e)}"}],
                        "isError": True
                    }
                }

        return self._error_response(req_id, -32601, f"Method not found: {method}")

    def _error_response(self, req_id, code, message):
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": req_id
        }