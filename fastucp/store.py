from typing import Dict, Any, Optional

class InMemoryStore:
    """
    Simple, memory-based data store.
    In a real application, this would be a Redis or PostgreSQL connection.
    """
    def __init__(self):
       
        self._products: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, Any] = {}
        self._orders: Dict[str, Any] = {}

    # --- PRODUCT MANAGEMENT ---
    def add_product(self, sku: str, title: str, price: int, img: str, desc: str = ""):
        self._products[sku] = {
            "title": title,
            "price": price,
            "image": img,
            "desc": desc
        }

    def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        return self._products.get(sku)

    def list_products(self) -> Dict[str, Dict[str, Any]]:
        return self._products

 
    def save_session(self, session_id: str, cart_data: Any):
        """Saves the CheckoutResponse object or its dict representation."""
        self._sessions[session_id] = cart_data
        print(f"💾 STORE: Cart Saved -> {session_id}")

    def get_session(self, session_id: str) -> Optional[Any]:
        return self._sessions.get(session_id)


    def create_order(self, order_id: str, order_data: Any):
        self._orders[order_id] = order_data
        print(f"💾 STORE: Order Created -> {order_id}")

    def get_order(self, order_id: str) -> Optional[Any]:
        return self._orders.get(order_id)