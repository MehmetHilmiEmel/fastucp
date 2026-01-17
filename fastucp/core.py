from typing import List, Callable, Dict, Any, get_type_hints, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import AnyUrl, BaseModel


from .models._internal import (
    DiscoveryProfile, UcpService, Rest, Mcp, A2a, Version, 
    Discovery as DiscoveryCapability, Services,
    ResponseCheckout, ResponseOrder, Response
)
from .models.discovery.profile_schema import Payment, UcpDiscoveryProfile
from .models.schemas.shopping.types.payment_handler_resp import PaymentHandlerResponse
from .models.schemas.shopping.types.message import Message
from .models.schemas.shopping.types.message_error import MessageError
from .exceptions import UCPException

from .protocols.mcp import MCPProtocol
from .protocols.a2a import A2AProtocol

from .security import UCPSigningMiddleware

class FastUCP(FastAPI):
    """
    FastAPI subclass customized for Universal Commerce Protocol.
    Automatically handles /.well-known/ucp discovery and protocol routing.
    """
    def __init__(
        self, 
        base_url: str, 
        title: str = "FastUCP Merchant",
        version: str = "2026-01-11", 
        enable_mcp: bool = False,        
        enable_a2a: bool = False,   
        signing_key: str = None,     
        **kwargs
    ):
        self._print_banner(version)
        super().__init__(title=title, **kwargs)
        
        self.ucp_base_url = base_url.rstrip("/")
        self.ucp_version_str = version
        self.ucp_version = Version(root=version)
        
        self.enable_mcp = enable_mcp
        self.enable_a2a = enable_a2a

        self.capabilities: List[DiscoveryCapability] = []
        self.payment_handlers: List[PaymentHandlerResponse] = []
        self._handlers: Dict[str, Callable] = {}


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


        self.add_api_route(
            "/.well-known/ucp", 
            self._handle_manifest, 
            methods=["GET"], 
            response_model=UcpDiscoveryProfile,
            response_model_exclude_none=True,
            tags=["UCP Discovery"]
        )
        self.add_exception_handler(UCPException, self._ucp_exception_handler)

       
        if self.enable_mcp:
            from .protocols.mcp import MCPProtocol
            self.mcp_protocol = MCPProtocol(self)
            
          
            self.add_api_route(
                "/mcp", 
                self.mcp_protocol.handle_request, 
                methods=["POST"], 
                tags=["UCP Protocol: MCP"]
            )
            print(f"🤖 MCP Server Ready at: {self.ucp_base_url}/mcp")

        if self.enable_a2a:
            self.a2a_protocol = A2AProtocol(self)
            self.add_api_route("/.well-known/agent-card.json", self.a2a_protocol.handle_agent_card, methods=["GET"], tags=["UCP Protocol: A2A"])
            self.add_api_route("/agent/message", self.a2a_protocol.handle_message, methods=["POST"], tags=["UCP Protocol: A2A"])
            print(f"\033[92m   ✅ A2A Protocol Enabled (/agent/message)\033[0m")
        
        if signing_key:
            self.add_middleware(UCPSigningMiddleware, private_key_json=signing_key)
            print(f"\033[92m   🔒 Response Signing Enabled (JWS)\033[0m")

    def _print_banner(self, version):
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        BOLD = "\033[1m"
        RESET = "\033[0m" 
        
        print(fr"""{CYAN}{BOLD}
        ------------------------------------------------------
               ______        _    _    _  _____ _____ 
              |  ____|      | |  | |  | |/ ____|  __ \
              | |__ __ _ ___| |__| |  | | |    | |__) |
              |  __/ _` / __| __| | |  | | |    |  ___/ 
              | | | (_| \__ \ |_| |__| | |____| |     
              |_|  \__,_|___/\__|\___/ \_____|_|     
        
        -------------------------------------------------------
              
        {RESET}
        
        {GREEN}⚡️ FastUCP v0.1.2 - Universal Commerce Protocol{RESET}
        """)

    async def _ucp_exception_handler(self, request: Request, exc: UCPException):
        error_payload = Message(root=MessageError(
            type="error", code=exc.code, path=exc.path, 
            severity=exc.severity, content=exc.message
        ))
        return JSONResponse(
            status_code=exc.status_code,
            content={"messages": [error_payload.model_dump(exclude_none=True, mode='json')]}
        )
    
    def add_payment_handler(self, handler: PaymentHandlerResponse):
        self.payment_handlers.append(handler)

    def _register_capability(self, name: str, spec: str, schema: str):
        if any(c.name == name for c in self.capabilities): return
        self.capabilities.append(DiscoveryCapability(
            name=name, version=self.ucp_version,
            spec=AnyUrl(spec), schema_=AnyUrl(schema)
        ))

    def _create_ucp_context(self, context_type: str = "checkout"):
        active_caps = [Response(name=c.name, version=c.version) for c in self.capabilities]
        if context_type == "order":
            return ResponseOrder(version=self.ucp_version, capabilities=active_caps)
        return ResponseCheckout(version=self.ucp_version, capabilities=active_caps)

    def _handle_manifest(self) -> UcpDiscoveryProfile:
        shopping_service = self._services["dev.ucp.shopping"]
        
        # Manifest update logic
        if self.enable_mcp:
            shopping_service.mcp = Mcp(
                schema=AnyUrl("https://ucp.dev/services/shopping/mcp.openrpc.json"),
                # Critical: Writing our /mcp address to the Discovery file
                endpoint=AnyUrl(f"{self.ucp_base_url}/mcp")
            )
        if self.enable_a2a:
            shopping_service.a2a = A2a(
                endpoint=AnyUrl(f"{self.ucp_base_url}/.well-known/agent-card.json")
            )

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
        self._register_capability(
            name="dev.ucp.shopping.checkout",
            spec="https://ucp.dev/specs/checkout",
            schema="https://ucp.dev/schemas/shopping/checkout.json"
        )
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["POST"], response_model_exclude_none=True, tags=["UCP Shopping"])
            self._handlers["create_checkout"] = func
            return func
        return decorator

    def update_checkout(self, path: str = "/checkout-sessions/{id}"):
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["PATCH"], response_model_exclude_none=True, tags=["UCP Shopping"])
            self._handlers["update_checkout"] = func
            return func
        return decorator

    def complete_checkout(self, path: str = "/checkout-sessions/{id}/complete"):
        self._register_capability(
            name="dev.ucp.shopping.order",
            spec="https://ucp.dev/specs/order",
            schema="https://ucp.dev/schemas/shopping/order.json"
        )
        def decorator(func: Callable):
            self.add_api_route(path, func, methods=["POST"], response_model_exclude_none=True, tags=["UCP Shopping"])
            self._handlers["complete_checkout"] = func
            return func
        return decorator

    def _call_internal_handler(self, method_name: str, session_id: Optional[str], params: Dict[str, Any]):
        """
        Bridge method for other protocols (MCP, A2A) to call internal functions.
        SMART VERSION: Analyzes function parameters and populates Pydantic models automatically.
        """
        if method_name not in self._handlers:
            raise ValueError(f"Method {method_name} not registered")

        handler_func = self._handlers[method_name]
        
 
        import inspect
        sig = inspect.signature(handler_func)
        func_params = sig.parameters
        type_hints = get_type_hints(handler_func)
        

        if session_id:
            if "checkout_id" in func_params:
                params["checkout_id"] = session_id
            elif "session_id" in func_params:
                params["session_id"] = session_id
            elif "id" in func_params and method_name != "create_checkout": 
                # In create_checkout, 'id' is usually inside the payload, avoid conflict
                params["id"] = session_id


        final_kwargs = {}
        
        for name, param in func_params.items():

            if name in params:
                value = params[name]

                if name in type_hints:
                    model_class = type_hints[name]
                    if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                        if isinstance(value, dict):
                            try:
                                value = model_class(**value)
                            except Exception as e:
                                print(f"⚠️ Model conversion warning for {name}: {e}")
                
                final_kwargs[name] = value

            elif name in type_hints:
                model_class = type_hints[name]
                if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                    try:

                        final_kwargs[name] = model_class(**params)
                    except Exception:
                        pass
        
        return handler_func(**final_kwargs)

    def discovery(self, path: str = "/products/search"):
        """
        Decorator recording Discovery capabilities such as product search.
        """

        self._register_capability(
            name="dev.ucp.shopping.discovery",
            spec="https://ucp.dev/specs/discovery",
            schema="https://ucp.dev/schemas/shopping/discovery.json"
        )

        def decorator(func: Callable):

            self.add_api_route(
                path, 
                func, 
                methods=["POST"], 
                response_model_exclude_none=True, 
                tags=["UCP Discovery"]
            )

            self._handlers[func.__name__] = func
            return func
            
        return decorator