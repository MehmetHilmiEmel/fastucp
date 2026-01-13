# FastUCP ⚡️

**The "FastAPI" for the Universal Commerce Protocol (UCP).**

FastUCP is a high-performance, developer-friendly Python framework for building UCP-compliant Merchant Servers and Commerce Agents. It combines the strict compliance of **Google's Official UCP SDK models** with the intuitive developer experience of **FastAPI**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)]()
## 🌟 Why FastUCP?

The Universal Commerce Protocol involves complex JSON schemas, rigorous validation rules, and deep object nesting. **FastUCP** abstracts this complexity away.

* **🧱 Official Models:** Built directly on top of Google's auto-generated Pydantic models for 100% protocol compliance.
* **🚀 Developer Experience:** No more manual JSON construction. Use our `CheckoutBuilder` to write business logic, not boilerplate.
* **🔍 Auto-Discovery:** Automatically generates the `/.well-known/ucp` manifest based on your registered endpoints.
* **🔌 Facade Pattern:** Access all complex UCP types from a single, clean import: `fastucp.types`.

## 📦 Installation

*Requires Python 3.10+*

```bash
# Using pip
pip install fastucp

# Using uv (Recommended)
uv add fastucp
```

## ⚡️ Quick Start
Here is a minimal Merchant Server ("Hello World") that sells a single item. FastUCP handles the manifest generation, endpoint routing, and protocol headers automatically.
```
# main.py
from fastucp import FastUCP
from fastucp.shortcuts import CheckoutBuilder
from fastucp.types import CheckoutCreateRequest

# 1. Initialize the App
app = FastUCP(
    title="Hello World Store", 
    base_url="[http://127.0.0.1:8000](http://127.0.0.1:8000)"
)

# 2. Define a Checkout Endpoint
# The @app.checkout decorator automatically registers the capability 
# to the /.well-known/ucp manifest.
@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    
    # 3. Use the Builder (Magic happens here ✨)
    # The builder handles math (totals) and complex UCP object construction.
    cart = CheckoutBuilder(app, session_id="demo_session_1")
    
    # Add a simple item (Price is in cents: 2000 = $20.00)
    cart.add_item(
        item_id="sku_1",
        title="Hello World T-Shirt",
        price=2000, 
        quantity=1,
        img_url="[https://placehold.co/400](https://placehold.co/400)"
    )
    
    # 4. Build & Return the official UCP Response
    return cart.build()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Run the Server
```
python main.py
```
Your server is now live and UCP Compliant!

Manifest: http://127.0.0.1:8000/.well-known/ucp
Checkout: http://127.0.0.1:8000/checkout-sessions

## 🧩 Key Features
1. The Builder Pattern
Instead of dealing with nested Pydantic models like LineItemResponse(totals=[TotalResponse(...)]), you simply use:
```
cart.add_item(..., price=500, quantity=2)
```
FastUCP handles the calculations and structure for you.

2. Payment Presets
Easily integrate supported payment handlers without digging into schema details:
```
from fastucp.presets import GooglePay

app.add_payment_handler(
    GooglePay(merchant_id="123", gateway="stripe", ...)
)
```


3. AI Agent Ready (MCP)
FastUCP servers are designed to be easily consumed by LLM Agents (Claude, Gemini, OpenAI) via the Model Context Protocol (MCP), bridging the gap between traditional e-commerce and AI Agents.



📄 License
This project is licensed under the Apache 2.0 License.