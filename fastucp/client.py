import requests
import json
import traceback
from typing import List, Dict, Any, Optional, Literal
from urllib.parse import urljoin

from .models.discovery.profile_schema import UcpDiscoveryProfile
from .models.schemas.shopping.checkout_resp import CheckoutResponse
from .models.schemas.shopping.order import Order 

PROTOCOL_PATHS = {
    "dev.ucp.shopping.checkout": "/checkout-sessions",
    "dev.ucp.shopping.discovery": "/products",
}

class FastUCPClient:
    def __init__(self, base_url: str, transport: Literal["rest", "mcp", "a2a"] = "rest"):
        """
        FastUCP Client.
        
        Args:
            base_url: Store address (e.g. http://127.0.0.1:8000)
            transport: Communication protocol ('rest', 'mcp', 'a2a'). Default 'rest'.
        """
        self.entry_point = base_url.rstrip("/")
        self.transport = transport
        self.session = requests.Session()
        self.manifest: Optional[UcpDiscoveryProfile] = None
        self._capability_endpoints: Dict[str, str] = {}

        self._request_id = 1

    def discover(self):
        """
        Discovers server capabilities (.well-known/ucp).
        Note: Even in MCP/A2A mode, the discovery endpoint usually works via REST.
        """
        discovery_url = f"{self.entry_point}/.well-known/ucp"
        try:
            print(f"🔍 Discovery: {discovery_url}")
            response = self.session.get(discovery_url)
            response.raise_for_status()
            
            data = response.json()
            self.manifest = UcpDiscoveryProfile(**data)
            
            base_api_url = self.entry_point
            
            # Find Service Endpoint
            if self.manifest.ucp.services:
                services_dict = self.manifest.ucp.services.root
                shopping_service = services_dict.get("dev.ucp.shopping")
                
                # REST Endpoint
                if shopping_service and shopping_service.rest:
                      base_api_url = str(shopping_service.rest.endpoint).rstrip("/")
            
            # Map Capability Endpoints
            for cap in self.manifest.ucp.capabilities:
                cap_name = cap.name 
                if not cap_name: continue

                relative_path = PROTOCOL_PATHS.get(cap_name)
                
                if relative_path:
                    full_url = urljoin(f"{base_api_url}/", relative_path.lstrip("/"))
                    self._capability_endpoints[cap_name] = full_url
                    print(f"   ✅ Mapped: {cap_name} -> {full_url}")
            
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"UCP Discovery failed: {e}")

    def _get_url_for_capability(self, capability_name: str) -> str:
        """Finds URL for REST mode."""
        if not self.manifest:
            self.discover()
            
        url = self._capability_endpoints.get(capability_name)
        if not url:
             return f"{self.entry_point}/checkout-sessions"
             
        return url



    def create_checkout(self, line_items: List[Dict[str, Any]], buyer: Dict[str, Any] = {}) -> CheckoutResponse:
        payload = {
            "line_items": line_items,
            "buyer": buyer,
            "currency": "USD", 
            "payment": {}        
        }
        
        # Route according to protocol
        if self.transport == "rest":
            data = self._send_rest_create(payload)
        elif self.transport == "mcp":
            # UPDATE: Automatically wrap in tools/call
            data = self._send_mcp_tool_call("create_checkout", payload)
        elif self.transport == "a2a":
            data = self._send_a2a("add_to_checkout", payload)
            
        return CheckoutResponse(**data)

    def update_checkout(self, session_id: str, buyer_data: Dict[str, Any]) -> CheckoutResponse:
        payload = {
            "id": session_id,
            "line_items": [], 
            "buyer": buyer_data,
            "currency": "USD",
            "payment": {}
        }
        
        if self.transport == "rest":
            data = self._send_rest_update(session_id, payload)
        elif self.transport == "mcp":

            data = self._send_mcp_tool_call("update_checkout", payload)
        elif self.transport == "a2a":
            data = self._send_a2a("update_checkout", payload)
            
        return CheckoutResponse(**data)

    def complete_checkout(self, session_id: str, payment_data: Dict[str, Any]) -> Order:
        payload = {"id": session_id, "payment": payment_data}
        
        if self.transport == "rest":
            data = self._send_rest_complete(session_id, payload)
        elif self.transport == "mcp":
            data = self._send_mcp_tool_call("complete_checkout", payload)
        elif self.transport == "a2a":
            data = self._send_a2a("complete_checkout", payload)
            
        return Order(**data)



    def _send_rest_create(self, payload):
        url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def _send_rest_update(self, session_id, payload):
        base_url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        url = f"{base_url}/{session_id}"
        response = self.session.patch(url, json=payload)
        response.raise_for_status()
        return response.json()

    def _send_rest_complete(self, session_id, payload):
        base_url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        url = f"{base_url}/{session_id}/complete"

        rest_payload = {"payment": payload.get("payment", {})}
        response = self.session.post(url, json=rest_payload)
        response.raise_for_status()
        return response.json()

    def _send_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends raw request via MCP (JSON-RPC 2.0) protocol.
        """
        url = f"{self.entry_point}/mcp"
        
        # UCP Metadata Requirement
        if "_meta" not in params and method != "tools/call":
            params["_meta"] = {
                "ucp": {"profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"}
            }

        rpc_payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id
        }
        self._request_id += 1
        
        print(f"📡 MCP Request ({method})...")
        response = self.session.post(url, json=rpc_payload)
        response.raise_for_status()
        
        resp_data = response.json()
        
        if "error" in resp_data:
            raise Exception(f"MCP Error: {resp_data['error']}")
            
        return resp_data["result"]

    def _send_mcp_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to wrap calls in the standard 'tools/call' structure and unwrap the result.
        """
        mcp_result = self._send_mcp("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })


        if mcp_result.get("isError"):
            # Extract and raise the error message
            error_text = "Unknown MCP Error"
            if "content" in mcp_result and isinstance(mcp_result["content"], list):
                error_text = mcp_result["content"][0].get("text", error_text)
            raise Exception(f"Server Side Error ({tool_name}): {error_text}")
    


        if "_raw" in mcp_result:
            return mcp_result["_raw"]
        
        # Fallback
        if "content" in mcp_result and isinstance(mcp_result["content"], list):
            first_content = mcp_result["content"][0]
            if first_content.get("type") == "text":
                try:
                    return json.loads(first_content.get("text"))
                except:
                    pass
        
        return mcp_result
    
    def _send_a2a(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends request via A2A (Agent-to-Agent) protocol.
        """
        url = f"{self.entry_point}/agent/message"
        
        # A2A Message Structure
        message_payload = {
            "message": {
                "role": "user",
                "kind": "message",
                "messageId": str(self._request_id),
                "parts": [
                    {
                        "type": "data",
                        "data": {
                            "action": action,
                            **data
                        }
                    }
                ]
            }
        }
        self._request_id += 1
        
        # Required Header
        headers = {
            "UCP-Agent": 'profile="https://agent.example/profiles/v2026-01/shopping-agent.json"'
        }
        
        print(f"📡 A2A Request ({action})...")
        response = self.session.post(url, json=message_payload, headers=headers)
        response.raise_for_status()
        
        resp_json = response.json()
        
      
        try:
            result_block = resp_json.get("result", {})
            parts = result_block.get("parts", [])
            
            # Find Data part
            data_part = next((p for p in parts if p.get("kind") == "data" or p.get("type") == "data"), None)
            
            if data_part:
                # Usually returns under a2a.ucp.checkout key
                inner_data = data_part.get("data", {})
                if "a2a.ucp.checkout" in inner_data:
                    return inner_data["a2a.ucp.checkout"]
                return inner_data
            
            return result_block
            
        except Exception as e:
            print(f"A2A Parsing Error: {e}")
            return resp_json