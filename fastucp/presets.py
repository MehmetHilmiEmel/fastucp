from typing import Optional
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
        environment: str = "TEST"
    ):
        config = {
            "api_version": 2,
            "api_version_minor": 0,
            "environment": environment,
            "merchant_info": {
                "merchant_name": merchant_name,
                "merchant_id": merchant_id
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
        
        super().__init__(
            id="gpay",
            name="com.google.pay",
            version=Version(root="2026-01-11"),
            spec=AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/"),
            config_schema=AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/schemas/config.json"),
            instrument_schemas=[AnyUrl("https://pay.google.com/gp/p/ucp/2026-01-11/schemas/card_payment_instrument.json")],
            config=config
        )