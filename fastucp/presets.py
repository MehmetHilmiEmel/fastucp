from typing import Dict, Any, Optional
from pydantic import AnyUrl
from .models.schemas.shopping.types.payment_handler_resp import PaymentHandlerResponse
from .models._internal import Version

class GooglePay(PaymentHandlerResponse):
    def __init__(
        self, 
        merchant_name: str, 
        merchant_id: str, 
        gateway: str, 
        gateway_merchant_id: str,
        environment: str = "TEST",
        auth_jwt: Optional[str] = None
    ):
        base_config = {
            "api_version": 2,
            "api_version_minor": 0,
            "environment": environment,
            "merchant_info": {
                "merchant_name": merchant_name,
                "merchant_id": merchant_id,
                "merchant_origin": "checkout.merchant.com"
            },
            "allowed_payment_methods": [
                {
                    "type": "CARD",
                    "parameters": {
                        "allowed_auth_methods": ["PAN_ONLY", "CRYPTOGRAM_3DS"],
                        "allowed_card_networks": ["VISA", "MASTERCARD"]
                    },
                    "tokenization_specification": {
                        "type": "PAYMENT_GATEWAY",
                        "parameters": {
                            "gateway": gateway,
                            "gatewayMerchantId": gateway_merchant_id
                        }
                    }
                }
            ]
        }
        
        if auth_jwt:
            base_config["merchant_info"]["auth_jwt"] = auth_jwt

        super().__init__(
            id="gpay",
            name="com.google.pay",
            version=Version(root="2026-01-11"),
            spec=AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/"),
            config_schema=AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/schemas/config.json"),
            instrument_schemas=[AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/schemas/card_payment_instrument.json")],
            config=base_config
        )

class ShopPay(PaymentHandlerResponse):
    def __init__(self, shop_id: str):
        super().__init__(
            id="shop_pay",
            name="com.shopify.shop_pay",
            version=Version(root="2025-12-08"),
            spec=AnyUrl("https://shopify.dev/ucp/shop_pay"),
            config_schema=AnyUrl("https://shopify.dev/ucp/handlers/shop_pay/config.json"),
            instrument_schemas=[AnyUrl("https://shopify.dev/ucp/handlers/shop_pay/instrument.json")],
            config={"shop_id": shop_id}
        )