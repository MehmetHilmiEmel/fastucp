from typing import List, Optional, Any, Dict
from pydantic import AnyUrl
from .core import FastUCP
from .types import (
    CheckoutResponse, LineItemResponse, ItemResponse, TotalResponse, 
    PaymentResponse, Message, MessageError, Order, Fulfillment, 
    ResponseOrder
)

class CheckoutBuilder:
    def __init__(self, app: FastUCP, session_id: str, currency: str = "USD"):
        self.app = app
        self.id = session_id
        self.currency = currency
        self.line_items = []
        self.messages = []
        self.buyer = None
        self.subtotal = 0
        
    def add_item(self, item_id: str, title: str, price: int, quantity: int, img_url: str):
        line_total = price * quantity
        self.subtotal += line_total
        
        self.line_items.append(LineItemResponse(
            id=f"li_{len(self.line_items) + 1}",
            item=ItemResponse(
                id=item_id, 
                title=title, 
                price=price, 
                image_url=AnyUrl(img_url)
            ),
            quantity=quantity,
            totals=[
                TotalResponse(type="subtotal", amount=line_total),
                TotalResponse(type="total", amount=line_total)
            ]
        ))
        return self

    def set_buyer(self, buyer_data: Optional[Any]):
        self.buyer = buyer_data
        
        if not buyer_data or not getattr(buyer_data, 'email', None):
            self.add_error(
                code="missing", 
                path="$.buyer.email", 
                message="Buyer email is required."
            )
        return self

    def add_error(self, code: str, path: str, message: str):
        self.messages.append(Message(root=MessageError(
            type="error", code=code, path=path, 
            severity="requires_buyer_input", content=message
        )))
        return self

    def build(self) -> CheckoutResponse:
        status = "incomplete" if self.messages else "ready_for_complete"
        
        return CheckoutResponse(
            ucp=self.app.get_context("checkout"),
            id=self.id,
            status=status,
            line_items=self.line_items,
            currency=self.currency,
            totals=[
                TotalResponse(type="subtotal", amount=self.subtotal),
                TotalResponse(type="total", amount=self.subtotal)
            ],
            messages=self.messages if self.messages else None,
            links=[],
            payment=PaymentResponse(handlers=self.app._payment_handlers),
            buyer=self.buyer
        )