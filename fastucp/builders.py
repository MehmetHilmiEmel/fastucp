# fastucp/builders.py
from typing import List, Optional, Any
from pydantic import AnyUrl
from .types import (
    CheckoutResponse, LineItemResponse, ItemResponse, TotalResponse, 
    PaymentResponse, Message, MessageError, ResponseCheckout, Response, Version
)

class CheckoutBuilder:
    """
    Builder pattern to construct a valid UCP CheckoutResponse without
    dealing with nested Pydantic models manually.
    """
    def __init__(self, session_id: str, app_context: Any, currency: str = "USD"):
        self.id = session_id
        self.currency = currency
        self.app = app_context # FastUCP instance referansı
        
        self.line_items: List[LineItemResponse] = []
        self.messages: List[Message] = []
        self.buyer: Optional[Any] = None
        self.subtotal = 0
        self.links = []

    def add_item(
        self, 
        item_id: str, 
        title: str, 
        price: int, 
        quantity: int, 
        img_url: str,
        description: str = None
    ) -> "CheckoutBuilder":
        """Adds a line item and auto-calculates totals."""
        
        line_total = price * quantity
        self.subtotal += line_total
        
        # Line Item Total Breakdown
        li_totals = [
            TotalResponse(type="subtotal", amount=line_total),
            TotalResponse(type="total", amount=line_total)
        ]

        self.line_items.append(LineItemResponse(
            id=f"li_{len(self.line_items) + 1}",
            item=ItemResponse(
                id=item_id, 
                title=title, 
                price=price, 
                image_url=AnyUrl(img_url)
            ),
            quantity=quantity,
            totals=li_totals
        ))
        return self

    def set_buyer(self, buyer_data: Optional[Any]) -> "CheckoutBuilder":
        """Sets the buyer and performs basic validation checks."""
        self.buyer = buyer_data
        
        # Example Validation: Require Email
        if not buyer_data or not getattr(buyer_data, 'email', None):
            self.add_error(
                code="missing", 
                path="$.buyer.email", 
                message="Email address is required to checkout."
            )
        return self

    def add_error(self, code: str, path: str, message: str) -> "CheckoutBuilder":
        """Adds a UCP compliant error message to the response."""
        self.messages.append(Message(root=MessageError(
            type="error", code=code, path=path, 
            severity="requires_buyer_input", content=message
        )))
        return self

    def build(self) -> CheckoutResponse:
        """Constructs the final Pydantic model."""
        
        # 1. Determine Status based on messages
        status = "incomplete" if self.messages else "ready_for_complete"
        
        # 2. Cart Totals
        cart_totals = [
            TotalResponse(type="subtotal", amount=self.subtotal),
            TotalResponse(type="total", amount=self.subtotal)
        ]

        # 3. Construct the UCP Context Wrapper automatically
        # This accesses the parent app to get version/capabilities
        ucp_context = self.app._create_ucp_context(context_type="checkout")

        return CheckoutResponse(
            ucp=ucp_context,
            id=self.id,
            status=status,
            line_items=self.line_items,
            currency=self.currency,
            totals=cart_totals,
            messages=self.messages if self.messages else None,
            links=self.links,
            payment=PaymentResponse(handlers=self.app.payment_handlers),
            buyer=self.buyer
        )