from fastapi import FastAPI
from typing import List, Callable, Dict, Any, Optional
from pydantic import AnyUrl

from .models._internal import (
    DiscoveryProfile, UcpService, Rest, Version, 
    Discovery as DiscoveryCapability, Services
)
from .models.discovery.profile_schema import Payment, UcpDiscoveryProfile
from .models.schemas.shopping.types.payment_handler_resp import PaymentHandlerResponse

class FastUCP(FastAPI):
    def __init__(
        self, 
        base_url: str, 
        title: str = "FastUCP Business",
        version: str = "2026-01-11",
        **kwargs
    ):
        super().__init__(title=title, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.ucp_version = Version(root=version)
        
        self._capabilities: List[DiscoveryCapability] = []
        self._payment_handlers: List[PaymentHandlerResponse] = []
        
        self._services = {
            "dev.ucp.shopping": UcpService(
                version=self.ucp_version,
                spec=AnyUrl("https://ucp.dev/specification/overview"),
                rest=Rest(
                    schema=AnyUrl("https://ucp.dev/services/shopping/rest.openapi.json"),
                    endpoint=AnyUrl(self.base_url)
                )
            )
        }
        
        self.add_api_route(
            "/.well-known/ucp", 
            self._handle_manifest, 
            methods=["GET"], 
            response_model=UcpDiscoveryProfile,
            response_model_exclude_none=True
        )

    def get_context(self, context_type: str = "checkout"):
        """
        Automatically creates the 'ucp' object for responses.
        Prevents the developer from manually dealing with Version and Capability objects.
        """
        from .models._internal import ResponseCheckout, ResponseOrder, Version, Response

        caps = []
        for c in self._capabilities:
            caps.append(Response(name=c.name, version=c.version))

        version_obj = self.ucp_version

        if context_type == "order":
            return ResponseOrder(version=version_obj, capabilities=caps)
        
        return ResponseCheckout(version=version_obj, capabilities=caps)

    def _register_capability(self, name: str, spec: str, schema: str, extends: Optional[str] = None):
        """
        Registers a capability to the list, preventing duplicates.
        """
        if any(c.name == name for c in self._capabilities):
            return

        self._capabilities.append(DiscoveryCapability(
            name=name,
            version=self.ucp_version,
            spec=AnyUrl(spec),
            schema=AnyUrl(schema),
            extends=extends
        ))

    def add_custom_capability(self, name: str, spec_url: str, schema_url: str, extends: Optional[str] = None):
        """
        Allows developers to add their own custom (Vendor) capabilities.
        E.g.: app.add_custom_capability("com.company.loyalty", ...)
        """
        self._register_capability(name, spec_url, schema_url, extends)

    def add_payment_handler(self, handler: PaymentHandlerResponse):
        self._payment_handlers.append(handler)

    def _handle_manifest(self) -> UcpDiscoveryProfile:
        return UcpDiscoveryProfile(
            ucp=DiscoveryProfile(
                version=self.ucp_version,
                services=Services(root=self._services),
                capabilities=self._capabilities
            ),
            payment=Payment(handlers=self._payment_handlers) if self._payment_handlers else None
        )

    def checkout(self, path: str = "/checkout-sessions"):
        """
        When the developer uses this decorator, the 'checkout' capability is automatically added.
        """
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["POST"], response_model_exclude_none=True)
            
            self._register_capability(
                name="dev.ucp.shopping.checkout",
                spec="https://ucp.dev/specs/checkout",
                schema="https://ucp.dev/schemas/shopping/checkout.json"
            )
            return func
        return decorator

    def complete_checkout(self, path: str = "/checkout-sessions/{id}/complete"):
        """
        This decorator represents the 'dev.ucp.shopping.order' capability.
        """
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["POST"], response_model_exclude_none=True)
            
            self._register_capability(
                name="dev.ucp.shopping.order",
                spec="https://ucp.dev/specs/order",
                schema="https://ucp.dev/schemas/shopping/order.json"
            )
            return func
        return decorator
        
    def update_checkout(self, path: str = "/checkout-sessions/{id}"):
            """
            Decorator for the checkout update (PATCH) operation.
            """
            def decorator(func: Callable):
                self.add_api_route(
                    path, 
                    func, 
                    methods=["PATCH"], 
                    response_model_exclude_none=True
                )
                return func
            return decorator