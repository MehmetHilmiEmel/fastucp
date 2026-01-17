import uvicorn
from typing import List, Dict, Any
from fastucp import FastUCP, CheckoutBuilder
from fastucp.types import CheckoutCreateRequest, CheckoutUpdateRequest


try:
    from .inventory import PRODUCTS
except ImportError:
    from inventory import PRODUCTS

# Initialize App with MCP Enabled
app = FastUCP(
    title="FastUCP Tech Store",
    base_url="http://127.0.0.1:8000",
    enable_mcp=True,  # Enables /mcp endpoint for Agents
    version="2026-01-11"
)

@app.discovery("/products/search")
def search_products(query: str = ""):
    """Search the mock inventory for products."""
    results = []
    print(f"Server: Searching for '{query}'...")
    
    for item in PRODUCTS.values():
        if query.lower() in item["title"].lower() or query.lower() in item["description"].lower():
            results.append({
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "image_url": item["image_url"]
            })
    return {"items": results}


@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    """Initialize a cart/checkout session."""

    session_id = "session_abc123" 

    builder = CheckoutBuilder(app, session_id=session_id)
    

    builder.links = [
        {"type": "privacy_policy", "url": "https://example.com/privacy"},
        {"type": "terms_of_service", "url": "https://example.com/terms"}
    ]

    # Add requested items from inventory
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
    
    # If buyer info was sent initially, set it
    if payload.buyer:
        builder.set_buyer(payload.buyer)

    return builder.build()

@app.update_checkout("/checkout-sessions/{id}")
def update_session(id: str, payload: CheckoutUpdateRequest):
    """
    Handle updates (e.g., buyer enters address).
    We dynamically calculate shipping based on item count/weight here.
    """
    builder = CheckoutBuilder(app, session_id=id)
    

    builder.links = [
        {"type": "privacy_policy", "url": "https://example.com/privacy"},
        {"type": "terms_of_service", "url": "https://example.com/terms"}
    ]

    product = PRODUCTS["sku_pixel"]
    builder.add_item(
        item_id=product["id"],
        title=product["title"],
        price=product["price"],
        quantity=1,
        img_url=product["image_url"]
    )

    # Set Buyer
    builder.set_buyer(payload.buyer)

    # Calculate Shipping Logic
    if payload.buyer and payload.buyer.email:
        # Simulate logic: If address is known, show shipping options
        builder.add_shipping_option(
            id="ship_standard",
            title="Standard Shipping",
            amount=500, # $5.00
            description="Arrives in 5-7 days"
        )
        builder.add_shipping_option(
            id="ship_express",
            title="Express Shipping",
            amount=2500, # $25.00
            description="Arrives tomorrow"
        )
        # Default select standard
        builder.select_shipping_option("ship_standard")
    else:
        # Require Email to calculate shipping
        builder.add_error("missing_field", "$.buyer.email", "Please provide an email for shipping calculation.")

    return builder.build()

@app.complete_checkout("/checkout-sessions/{id}/complete")
def complete_session(id: str, payment: Dict[str, Any]):
    """Finalize the order."""
    return {
        "ucp": {"version": "2026-01-11", "capabilities": []},
        "id": "order_999",
        "checkout_id": id,
        "permalink_url": "https://example.com/orders/999",
        "status": "confirmed",
        "line_items": [], 
        "fulfillment": {"expectations": []},
        "totals": []
    }

if __name__ == "__main__":
    print("🚀 Starting FastUCP Merchant Server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)