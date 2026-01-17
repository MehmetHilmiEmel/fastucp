# FastUCP ⚡️

**The "FastAPI" for the Universal Commerce Protocol (UCP).**

FastUCP is a high-performance, developer-friendly Python framework for building UCP-compliant Merchant Servers and Commerce Agents. It combines the strict compliance of **Google's Official UCP SDK models** with the intuitive developer experience of **FastAPI**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)]()

## 🌟 Why FastUCP?

The Universal Commerce Protocol involves complex JSON schemas, rigorous validation rules, and deep object nesting. **FastUCP** abstracts this complexity away.

* **🧱 Official Models:** Built directly on top of Google's auto-generated Pydantic models for 100% protocol compliance.
* **🚀 Developer Experience:** Write standard Python logic. FastUCP handles the protocol headers and routing.
* **🔍 Auto-Discovery:** Automatically generates the `/.well-known/ucp` manifest based on your registered endpoints (e.g., Discovery, Checkout).
* **🔌 Facade Pattern:** Access all complex UCP types from a single, clean import: `fastucp.types`.

## 📦 Installation

*Requires Python 3.10+*

```bash
# Using pip
pip install fastucp-python

# Using uv (Recommended)
uv add fastucp-python
```

## ⚡️ Quick Start
Here is a minimal Merchant Server ("Hello World") that implements Product Discovery. FastUCP automatically detects the @app.discovery route and adds the capability to your UCP Manifest.
```python
# main.py
from fastucp import FastUCP

# 1. Initialize the App
app = FastUCP(
    title="Hello World Store", 
    base_url="[http://127.0.0.1:8000](http://127.0.0.1:8000)"
)

# Mock Database
PRODUCTS = {
    "sku_pixel": {
        "id": "sku_pixel",
        "title": "Google Pixel 9 Pro",
        "description": "The latest AI-powered smartphone from Google.",
        "price": 99900,  # $999.00
        "image_url": "[https://store.google.com/pixel.jpg](https://store.google.com/pixel.jpg)",
        "weight": 0.5
    }
}

# 2. Register a Discovery Endpoint
@app.discovery("/products/search")
def search_products(query: str = ""):
    """Search products."""
    results = []
    print(f"🔎 Server: Searching for '{query}'...")
    
    for item in PRODUCTS.values():
        # Simple case-insensitive search
        if query.lower() in item["title"].lower():
            results.append({
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "image_url": item["image_url"]
            })
            
    return {"items": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Run the Server
```bash
python main.py
```

## 🚀 Verifying Compliance
1. The UCP Manifest
FastUCP automatically generates the entry point for the protocol. Open http://127.0.0.1:8000/.well-known/ucp to see the auto-generated manifest:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
        "spec": "[https://ucp.dev/specification/overview](https://ucp.dev/specification/overview)",
        "rest": {
          "schema": "[https://ucp.dev/services/shopping/rest.openapi.json](https://ucp.dev/services/shopping/rest.openapi.json)",
          "endpoint": "[http://127.0.0.1:8000/](http://127.0.0.1:8000/)"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.discovery",
        "version": "2026-01-11",
        "spec": "[https://ucp.dev/specs/discovery](https://ucp.dev/specs/discovery)",
        "schema_": "[https://ucp.dev/schemas/shopping/discovery.json](https://ucp.dev/schemas/shopping/discovery.json)"
      }
    ]
  }
}
```
2. Interactive Docs (Swagger UI)
Because this is built on FastAPI, you get free interactive documentation.

* Go to http://127.0.0.1:8000/docs.
* Click GET /products/search.
* Click Try it out and enter "pixel" in the query field.
* Execute to see the response:

```json
{
  "items": [
    {
      "id": "sku_pixel",
      "title": "Google Pixel 9 Pro",
      "price": 99900,
      "image_url": "[https://store.google.com/pixel.jpg](https://store.google.com/pixel.jpg)"
    }
  ]
}
```

## 🧩 Key Features
1. The Builder Pattern For complex workflows like Checkout, FastUCP provides helper classes (like CheckoutBuilder) so you don't have to manually nest Pydantic models.

2. Payment Presets Easily integrate supported payment handlers without digging into schema details:
```python
from fastucp.presets import GooglePay

app.add_payment_handler(
    GooglePay(merchant_id="123", gateway="stripe", ...)
)
```
3. AI Agent Ready (MCP) FastUCP servers are designed to be easily consumed by LLM Agents (Claude, Gemini, OpenAI) via the Model Context Protocol (MCP), bridging the gap between traditional e-commerce and AI Agents.

## 📄 License
This project is licensed under the terms of the MIT License.