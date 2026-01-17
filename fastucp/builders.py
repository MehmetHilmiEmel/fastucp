from typing import List, Optional, Any
from pydantic import AnyUrl
from .types import (
    CheckoutResponse, LineItemResponse, ItemResponse, TotalResponse, 
    PaymentResponse, Message, MessageError, ResponseCheckout, Response, Version,FulfillmentResponse, FulfillmentMethodResponse, 
    FulfillmentOptionResponse, FulfillmentGroupResponse,
    DiscountsObject, AppliedDiscount
)

class CheckoutBuilder:
    """
    Builder pattern to construct a valid UCP CheckoutResponse without
    dealing with nested Pydantic models manually.
    """

    def __init__(self, app_context: Any, session_id: str, currency: str = "USD"):
        self.id = session_id
        self.currency = currency
        self.app = app_context 
        
        self.line_items: List[LineItemResponse] = []
        self.messages: List[Message] = []
        self.buyer: Optional[Any] = None
        self.subtotal = 0
        self.links = []

        self._shipping_options = [] 
        self._discounts = []
        self._shipping_cost = 0
        self._discount_amount = 0

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

        email = None
        if isinstance(buyer_data, dict):
            email = buyer_data.get('email')
        elif hasattr(buyer_data, 'email'):
            email = buyer_data.email

        if buyer_data and not email:
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
    

    def add_shipping_option(self, id: str, title: str, amount: int, description: str = ""):
        """
        Developer-friendly shipping option addition.
        Automatically sets up the complex Fulfillment hierarchy (Method -> Group -> Option).
        """
        self._shipping_options.append(
            FulfillmentOptionResponse(
                id=id,
                title=title,
                description=description,
                totals=[TotalResponse(type="fulfillment", amount=amount)]
            )
        )
        return self

    def select_shipping_option(self, option_id: str):
        """
        Marks a shipping option as 'selected' and adds the amount to the total.
        """
        for opt in self._shipping_options:
            if opt.id == option_id:

                cost = opt.totals[0].amount
                self._shipping_cost = cost
                self._selected_shipping_id = option_id
                return self
        return self

    def add_discount(self, code: str, amount: int, title: str):
        """
        Applies a discount to the cart.
        """
        self._discounts.append(
            AppliedDiscount(
                code=code,
                title=title,
                amount=amount
            )
        )
        self._discount_amount += amount
        return self

    def build(self) -> CheckoutResponse:
        

        final_total = self.subtotal + self._shipping_cost - self._discount_amount
        final_total = max(0, final_total) 
        cart_totals = [
            TotalResponse(type="subtotal", amount=self.subtotal)
        ]
        
        if self._shipping_cost > 0:
            cart_totals.append(TotalResponse(type="fulfillment", amount=self._shipping_cost))
            
        if self._discount_amount > 0:
            cart_totals.append(TotalResponse(type="discount", amount=self._discount_amount))
            
        cart_totals.append(TotalResponse(type="total", amount=final_total))

        # 2. Build Fulfillment Object (If exists)
        fulfillment_obj = None
        if self._shipping_options:
            # Automatically creating a default "Shipping Group"
            fulfillment_obj = FulfillmentResponse(
                methods=[
                    FulfillmentMethodResponse(
                        id="method_shipping",
                        type="shipping",
                        line_item_ids=[li.id for li in self.line_items], # All items
                        groups=[
                            FulfillmentGroupResponse(
                                id="group_default",
                                line_item_ids=[li.id for li in self.line_items],
                                options=self._shipping_options,
                                selected_option_id=getattr(self, '_selected_shipping_id', None)
                            )
                        ]
                    )
                ]
            )


        discounts_obj = None
        if self._discounts:
            discounts_obj = DiscountsObject(
                applied=self._discounts,
                codes=[d.code for d in self._discounts if d.code]
            )

        ucp_context = self.app._create_ucp_context(context_type="checkout")

        return CheckoutResponse(
            ucp=ucp_context,
            id=self.id,
            status="ready_for_complete" if not self.messages else "incomplete",
            line_items=self.line_items,
            currency=self.currency,
            totals=cart_totals,
            messages=self.messages if self.messages else None,
            links=self.links,
            payment=PaymentResponse(handlers=self.app.payment_handlers),
            buyer=self.buyer,
            fulfillment=fulfillment_obj,
            discounts=discounts_obj
        )