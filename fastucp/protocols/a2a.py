from fastapi import Request, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import uuid

class A2AProtocol:
    """
    Handles Agent-to-Agent (A2A) Message Protocol.
    Compliant with UCP A2A Binding Specification (2026-01-11).
    """
    def __init__(self, app):
        self.app = app

    def handle_agent_card(self):
        """
        /.well-known/agent-card.json
        """
        capabilities = []
        for name in self.app._handlers.keys():
            # Naming according to Spec (dev.ucp.shopping...)
            cap_name = f"dev.ucp.shopping.{name.replace('create_session', 'checkout').replace('_checkout', '')}"
            if name == "create_checkout": cap_name = "dev.ucp.shopping.checkout"
            
            capabilities.append({
                "name": cap_name,
                "version": "2026-01-11"
            })

        return {
            "type": "agent-card",
            "extensions": [
                {
                    "uri": "https://ucp.dev/specification/reference?v=2026-01-11",
                    "description": "Business agent supporting UCP Checkout",
                    "params": {
                        "capabilities": capabilities
                    }
                }
            ]
        }

    async def handle_message(self, request: Request, ucp_agent: str = Header(None, alias="UCP-Agent")):
        """
        POST /agent/message
        Handles structured A2A messages conformant to UCP Spec.
        """
        try:
            body = await request.json()

        except:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)


        params = body.get("params", {})

        message_wrapper = params.get("message") if "message" in params else body.get("message", {})
        
        context_id = message_wrapper.get("contextId", str(uuid.uuid4()))
        parts = message_wrapper.get("parts", [])
        
        # --- PARSING LOGIC ---
        
        data_part = next((p for p in parts if p.get("type") == "data" or p.get("kind") == "data"), None)
        text_part = next((p for p in parts if p.get("type") == "text" or p.get("kind") == "text"), None)
        
        payload = {}
        action = ""
        internal_method = ""

        if data_part:
            # Structured Data (Button clicks, etc.)
            print("⚙️ Data Part Detected")
            payload = data_part.get("data", {})
            action = payload.get("action")
            
            internal_method = action
            if action == "add_to_checkout": internal_method = "create_checkout"

        elif text_part:

            print(f"📝 Text Part Detected: {text_part.get('text')}")
            action = "search_shopping_catalog"
            internal_method = "search_shopping_catalog"
            payload = {"query": text_part.get("text")}
            
        else:
            print("❌ ERROR: Neither Data nor Text part found!")
            print(f"Inspected Parts: {parts}")
            return self._create_error_reply(body, "No recognizable part found (text or data).")



        if not internal_method or internal_method not in self.app._handlers:
             print(f"❌ Unknown Action: {action} (Mapped method: {internal_method})")
             return self._create_error_reply(body, f"Unknown action: {action}")

        try:

            clean_params = payload.copy()
            if "action" in clean_params: del clean_params["action"]
            
            session_id = clean_params.pop("id", None)
            if not session_id and "checkout_id" in clean_params:
                session_id = clean_params.pop("checkout_id")

            if "a2a.ucp.checkout.payment_data" in clean_params:
                clean_params["payment"] = clean_params.pop("a2a.ucp.checkout.payment_data")

            # Handler Call
            print(f"🚀 Executing: {internal_method} (Session: {session_id})")
            result = self.app._call_internal_handler(internal_method, session_id, clean_params)

            # Result Processing
            if isinstance(result, BaseModel):
                result_data = result.model_dump(mode="json", exclude_none=True)
            else:
                result_data = result

            response_data_content = {}
            if "line_items" in result_data or "id" in result_data:
                response_data_content["a2a.ucp.checkout"] = result_data
            else:
                response_data_content = result_data

            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "kind": "message",
                    "role": "agent",
                    "messageId": str(uuid.uuid4()),
                    "contextId": context_id,
                    "parts": [{
                        "kind": "data",
                        "data": response_data_content
                    }]
                }
            }

        except Exception as e:
            traceback.print_exc()
            return self._create_error_reply(body, str(e))
    
    def _create_error_reply(self, original_body, error_msg):
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": original_body.get("id"),
            "error": {
                "code": -32603,
                "message": error_msg
            }
        }, status_code=500)