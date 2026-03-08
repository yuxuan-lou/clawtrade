"""Broker factory — instantiate the configured broker."""
from brokers.base import BaseBroker


def create_broker(broker_type: str) -> BaseBroker:
    broker_type = broker_type.lower().strip()

    if broker_type == "ibkr":
        from brokers.ibkr import IBKRBroker
        return IBKRBroker()
    elif broker_type == "alpaca":
        from brokers.alpaca_broker import AlpacaBroker
        return AlpacaBroker()
    elif broker_type == "longbridge":
        from brokers.longbridge_broker import LongbridgeBroker
        return LongbridgeBroker()
    elif broker_type == "tiger":
        from brokers.tiger_broker import TigerBrokerClient
        return TigerBrokerClient()
    else:
        raise ValueError(
            f"Unsupported broker: '{broker_type}'. "
            f"Supported: ibkr, alpaca, longbridge, tiger"
        )
