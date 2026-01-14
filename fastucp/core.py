# fastucp/core.py
from typing import List, Callable, Dict, Any, Optional
from fastapi import FastAPI, APIRouter
from pydantic import AnyUrl

# Internal Model Imports
from .models._internal import (
    DiscoveryProfile, UcpService, Rest, Version, 
    Discovery as DiscoveryCapability, Services,
    ResponseCheckout, ResponseOrder, Response
)
from .models.discovery.profile_schema import Payment, UcpDiscoveryProfile
from .models.schemas.shopping.types.payment_handler_resp import PaymentHandlerResponse

class FastUCP(FastAPI):
    """
    FastAPI subclass customized for Universal Commerce Protocol.
    Automatically handles /.well-known/ucp discovery and response wrapping.
    """
    def __init__(
        self, 
        base_url: str, 
        title: str = "FastUCP Merchant",
        version: str = "2026-01-11", # Current UCP Version
        **kwargs
    ):
        

        CYAN = "\033[96m"
        GREEN = "\033[92m"
        BOLD = "\033[1m"
        RESET = "\033[0m" 
        
   
        print(fr"""{CYAN}{BOLD}
        ------------------------------------------------------
                ______        _   _   _  _____ _____ 
                |  ____|      | | | | | |/ ____|  __ \
                | |__ __ _ ___| |_| | | | |    | |__) |
                |  __/ _` / __| __| | | | |    |  ___/ 
                | | | (_| \__ \ |_| |_| | |____| |    
                |_|  \__,_|___/\__|\___/ \_____|_|    
        
        -------------------------------------------------------
              
        {RESET}
        
        {GREEN}⚡️ FastUCP v0.1.1 - Universal Commerce Protocol{RESET}
        """)
        super().__init__(title=title, **kwargs)
        self.ucp_base_url = base_url.rstrip("/")
        self.ucp_version_str = version
        self.ucp_version = Version(root=version)
        
        self.capabilities: List[DiscoveryCapability] = []
        self.payment_handlers: List[PaymentHandlerResponse] = []
        
        # Initialize default service definition
        self._services = {
            "dev.ucp.shopping": UcpService(
                version=self.ucp_version,
                spec=AnyUrl("https://ucp.dev/specification/overview"),
                rest=Rest(
                    schema=AnyUrl("https://ucp.dev/services/shopping/rest.openapi.json"),
                    endpoint=AnyUrl(self.ucp_base_url)
                )
            )
        }

        # Auto-register the manifest route
        self.add_api_route(
            "/.well-known/ucp", 
            self._handle_manifest, 
            methods=["GET"], 
            response_model=UcpDiscoveryProfile,
            response_model_exclude_none=True,
            tags=["UCP Discovery"]
        )

    def add_payment_handler(self, handler: PaymentHandlerResponse):
        """Registers a payment method (e.g. Google Pay) to be advertised in the manifest."""
        self.payment_handlers.append(handler)

    def _register_capability(self, name: str, spec: str, schema: str):
        """Internal: Adds a capability to the manifest if not already present."""
        if any(c.name == name for c in self.capabilities):
            return
        
        self.capabilities.append(DiscoveryCapability(
            name=name,
            version=self.ucp_version,
            spec=AnyUrl(spec),
            schema_=AnyUrl(schema) # Note: field alias is schema_ in pydantic model
        ))

    def _create_ucp_context(self, context_type: str = "checkout"):
        """Internal: Generates the 'ucp' field required in responses."""
        active_caps = [
            Response(name=c.name, version=c.version) 
            for c in self.capabilities
        ]
        
        if context_type == "order":
            return ResponseOrder(version=self.ucp_version, capabilities=active_caps)
        return ResponseCheckout(version=self.ucp_version, capabilities=active_caps)

    def _handle_manifest(self) -> UcpDiscoveryProfile:
        """Serves the dynamic Discovery Profile."""
        return UcpDiscoveryProfile(
            ucp=DiscoveryProfile(
                version=self.ucp_version,
                services=Services(root=self._services),
                capabilities=self.capabilities
            ),
            payment=Payment(handlers=self.payment_handlers) if self.payment_handlers else None
        )

    # --- Decorators ---

    def checkout(self, path: str = "/checkout-sessions"):
        """
        Decorator for the Checkout Creation/Update endpoint.
        Registers 'dev.ucp.shopping.checkout' capability automatically.
        """
        self._register_capability(
            name="dev.ucp.shopping.checkout",
            spec="https://ucp.dev/specs/checkout",
            schema="https://ucp.dev/schemas/shopping/checkout.json"
        )
        
        def decorator(func: Callable):
            # We use standard FastAPI routing. The return type validation 
            # handles the serialization.
            self.add_api_route(
                path, 
                func, 
                methods=["POST"], 
                response_model_exclude_none=True,
                tags=["UCP Shopping"]
            )
            return func
        return decorator

    def update_checkout(self, path: str = "/checkout-sessions/{id}"):
        """Decorator for PATCH requests to update checkout."""
        def decorator(func: Callable):
            self.add_api_route(
                path, 
                func, 
                methods=["PATCH"], 
                response_model_exclude_none=True,
                tags=["UCP Shopping"]
            )
            return func
        return decorator

    def complete_checkout(self, path: str = "/checkout-sessions/{id}/complete"):
        """
        Decorator for Order Completion.
        Registers 'dev.ucp.shopping.order' capability automatically.
        """
        self._register_capability(
            name="dev.ucp.shopping.order",
            spec="https://ucp.dev/specs/order",
            schema="https://ucp.dev/schemas/shopping/order.json"
        )
        
        def decorator(func: Callable):
            self.add_api_route(
                path, 
                func, 
                methods=["POST"], 
                response_model_exclude_none=True,
                tags=["UCP Shopping"]
            )
            return func
        return decorator