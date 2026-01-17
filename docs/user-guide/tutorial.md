This file uses your `examples/simple_store` code to teach the user.

# Tutorial: Building a Tech Store

In this tutorial, we will build a fully functional UCP Merchant Server that sells tech products (Pixel phones, Buds, etc.). We will implement product search, checkout creation, and shipping logic.

## 1. Define Inventory

First, let's define a simple in-memory inventory. In a real app, this would come from a database.

```python title="inventory.py"
PRODUCTS = {
    "sku_pixel": {
        "id": "sku_pixel",
        "title": "Google Pixel 9 Pro",
        "description": "The latest AI-powered smartphone.",
        "price": 99900,  # Prices are in cents ($999.00)
        "image_url": "[https://store.google.com/pixel.jpg](https://store.google.com/pixel.jpg)",
    },
    "sku_buds": {
        "id": "sku_buds",
        "title": "Pixel Buds Pro 2",
        "description": "Noise cancelling wireless earbuds.",
        "price": 19900,  # $199.00
        "image_url": "[https://store.google.com/buds.jpg](https://store.google.com/buds.jpg)",
    }
}
```
## 2. Initialize the Server
Create a server.py file. We initialize FastUCP with enable_mcp=True to allow AI Agents to interact with our store.
```python title="server.py"
from fastucp import FastUCP, CheckoutBuilder
from fastucp.types import CheckoutCreateRequest, CheckoutUpdateRequest
from inventory import PRODUCTS

app = FastUCP(
    title="FastUCP Tech Store",
    base_url="[http://127.0.0.1:8000](http://127.0.0.1:8000)",
    enable_mcp=True, 
    version="2026-01-11"
)
```

## 3. Implement Product Search (Discovery)
UCP Discovery allows agents to search your catalog. We use the @app.discovery decorator.
```python title="server.py"
@app.discovery("/products/search")
def search_products(query: str = ""):
    """Search the mock inventory for products."""
    results = []
    print(f"Server: Searching for '{query}'...")
    
    for item in PRODUCTS.values():
        if query.lower() in item["title"].lower():
            results.append({
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "image_url": item["image_url"]
            })
    return {"items": results}
```


## 4. Implement Checkout Creation
When a user (or agent) clicks "Buy", a session is created. We use the CheckoutBuilder to easily construct the complex UCP response.
```python title="server.py"
@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    # In a real app, generate a unique ID
    session_id = "session_abc123" 
    
    builder = CheckoutBuilder(app, session_id=session_id)
    
    # Add mandatory legal links
    builder.links = [
        {"type": "privacy_policy", "url": "[https://example.com/privacy](https://example.com/privacy)"},
        {"type": "terms_of_service", "url": "[https://example.com/terms](https://example.com/terms)"}
    ]

    # Add items from payload
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
            
    return builder.build()
```
## 5. Handle Updates (Shipping Logic)
The update_checkout endpoint is called when the buyer enters their email or address. This is where we calculate shipping.
```python title="server.py"
@app.update_checkout("/checkout-sessions/{id}")
def update_session(id: str, payload: CheckoutUpdateRequest):
    builder = CheckoutBuilder(app, session_id=id)
    
    # ... (Re-add items logic would go here) ...
    # For simplicity, we assume the cart state is maintained or re-fetched
    
    # Dynamic Shipping Calculation
    if payload.buyer and payload.buyer.email:
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
        builder.select_shipping_option("ship_standard")
    else:
        # Request email if missing
        builder.add_error(
            code="missing_field", 
            path="$.buyer.email", 
            message="Please provide an email for shipping calculation."
        )

    return builder.build()
```
## 6. Running the Server
Run your server using Uvicorn:

```bash
python server.py
```
Your server is now UCP compliant!

Manifest: http://127.0.0.1:8000/.well-known/ucp
MCP Endpoint: http://127.0.0.1:8000/mcp