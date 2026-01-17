
import uvicorn
import uuid
from typing import List, Dict, Any
from fastucp import FastUCP, CheckoutBuilder

from fastucp.types import (
    CheckoutCreateRequest, 
    CheckoutUpdateRequest,
    Order, 
    Fulfillment, 
    TotalResponse,
    ResponseOrder,
    Response,
    Version
)
from fastucp.models.schemas.shopping.types.order_line_item import OrderLineItem, Quantity

# Import handling
try:
    from .inventory import PRODUCTS
except ImportError:
    from inventory import PRODUCTS

app = FastUCP(
    title="FastUCP Tech Store",
    base_url="http://127.0.0.1:8000",
    enable_mcp=True,
    version="2026-01-11"
)

# --- SIMPLE DATABASE SIMULATION ---
SESSIONS = {} 

# --- 1. Discovery ---
@app.discovery("/products/search")
def search_products(query: str = ""):
    """Search products."""
    results = []
    print(f"🔎 Server: Searching for '{query}'...")
    for item in PRODUCTS.values():
        if query.lower() in item["title"].lower():
            results.append({
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "image_url": item["image_url"]
            })
    return {"items": results}

# --- 2. Create Checkout ---
@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    # Generate a new Session ID
    session_id = str(uuid.uuid4())
    
    builder = CheckoutBuilder(app, session_id=session_id)
    
    # Mandatory Links
    builder.links = [
        {"type": "privacy_policy", "url": "https://example.com/privacy"},
        {"type": "terms_of_service", "url": "https://example.com/terms"}
    ]

    # Add items
    for req_item in payload.line_items:
        product = PRODUCTS.get(req_item.item.id)
        if product:
            builder.add_item(
                item_id=product["id"],
                title=product["title"],
                price=product["price"],
                quantity=req_item.quantity,
                img_url=product["image_url"]
            )
    
    if payload.buyer:
        builder.set_buyer(payload.buyer)

    response = builder.build()
    
    # Save Session (Needed during Complete phase)
    SESSIONS[session_id] = response
    print(f"💾 Session Created: {session_id}")
    
    return response

# --- 3. Update Checkout ---
@app.update_checkout("/checkout-sessions/{id}")
def update_session(id: str, payload: CheckoutUpdateRequest):
    # We could retrieve old session data, but here we rebuild it using the Builder pattern.
    # In a real scenario, fetch the current state from SESSIONS[id] and pass it to the builder.
    builder = CheckoutBuilder(app, session_id=id)

    product = PRODUCTS["sku_pixel"]
    builder.add_item(product["id"], product["title"], product["price"], 1, product["image_url"])

    builder.links = [
        {"type": "privacy_policy", "url": "https://example.com/privacy"},
        {"type": "terms_of_service", "url": "https://example.com/terms"}
    ]
    
    builder.set_buyer(payload.buyer)

    # Shipping Logic
    if payload.buyer and payload.buyer.email:
        builder.add_shipping_option("ship_std", "Standard Shipping", 500, "5-7 Days")
        builder.select_shipping_option("ship_std")
    else:
        builder.add_error("missing", "$.buyer.email", "Email required for shipping.")

    response = builder.build()
    SESSIONS[id] = response # Save updated state
    return response


@app.complete_checkout("/checkout-sessions/{id}/complete")
def complete_session(id: str, payment: Dict[str, Any]):
    """
    Finalizes the order and returns an Order object.
    """
    print(f"💰 Payment Received: {payment}")

    # 1. Session Check
    checkout_session = SESSIONS.get(id)
    if not checkout_session:
        # Error can be raised (using UCPException)
        return {"error": "Session not found"}

    # 2. Payment Verification (Mock)
    # In real life, verify 'payment' token with Stripe/Iyzico/etc.
    if not payment.get("token"):
        pass

    
    order_line_items = []
    for li in checkout_session.line_items:
        order_line_items.append(
            OrderLineItem(
                id=li.id,
                item=li.item,
                quantity=Quantity(total=li.quantity, fulfilled=0),
                totals=li.totals,
                status="processing"
            )
        )

    # 4. Create Order Object
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    
    # Creating UCP Context (Capabilities)
    ucp_context = ResponseOrder(
        version=Version(root="2026-01-11"),
        capabilities=[
            # Which capabilities are active post-order
            Response(name="dev.ucp.shopping.order", version=Version(root="2026-01-11"))
        ]
    )

    order = Order(
        ucp=ucp_context,
        id=order_id,
        checkout_id=id,
        permalink_url=f"https://example.com/orders/{order_id}",
        line_items=order_line_items,
        totals=checkout_session.totals, 
        fulfillment=Fulfillment(
            expectations=[], # Fulfillment expectations can be added here
            events=[]
        )
    )

    print(f"🎉 Order Created: {order_id}")
    return order

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)