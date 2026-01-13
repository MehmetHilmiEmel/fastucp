import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import traceback

from .models.discovery.profile_schema import UcpDiscoveryProfile
from .models.schemas.shopping.checkout_resp import CheckoutResponse
from .models.schemas.shopping.order import Order 

PROTOCOL_PATHS = {
    "dev.ucp.shopping.checkout": "/checkout-sessions",
    "dev.ucp.shopping.discovery": "/products",
}

class FastUCPClient:
    def __init__(self, base_url: str):
        self.entry_point = base_url.rstrip("/")
        self.session = requests.Session()
        self.manifest: Optional[UcpDiscoveryProfile] = None
        self._capability_endpoints: Dict[str, str] = {}

    def discover(self):
        discovery_url = f"{self.entry_point}/.well-known/ucp"
        try:
            print(f"🔍 Discovery: {discovery_url}")
            response = self.session.get(discovery_url)
            response.raise_for_status()
            
            data = response.json()
            self.manifest = UcpDiscoveryProfile(**data)
            
            base_api_url = self.entry_point
            
            if self.manifest.ucp.services:
                services_dict = self.manifest.ucp.services.root
                shopping_service = services_dict.get("dev.ucp.shopping")
                
                if shopping_service and shopping_service.rest:
                     base_api_url = str(shopping_service.rest.endpoint).rstrip("/")
            
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
        if not self.manifest:
            self.discover()
            
        url = self._capability_endpoints.get(capability_name)
        if not url:
             return f"{self.entry_point}/checkout-sessions"
             
        return url

    def create_checkout(self, line_items: List[Dict[str, Any]], buyer: Dict[str, Any] = {}) -> CheckoutResponse:
        url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        
        payload = {
            "line_items": line_items,
            "buyer": buyer,
            "currency": "USD", 
            "payment": {}      
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return CheckoutResponse(**response.json())

    def update_checkout(self, session_id: str, buyer_data: Dict[str, Any]) -> CheckoutResponse:
        base_url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        url = f"{base_url}/{session_id}"
        
        payload = {
            "id": session_id,
            "line_items": [], 
            "buyer": buyer_data,
            "currency": "USD",
            "payment": {}
        }
        
        response = self.session.patch(url, json=payload)
        response.raise_for_status()
        return CheckoutResponse(**response.json())

    def complete_checkout(self, session_id: str, payment_data: Dict[str, Any]) -> Order:
        base_url = self._get_url_for_capability("dev.ucp.shopping.checkout")
        url = f"{base_url}/{session_id}/complete"
        
        payload = {"payment": payment_data}
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return Order(**response.json())