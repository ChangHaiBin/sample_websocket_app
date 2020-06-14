
class Order:
    def __init__(self, order_id, side: str, size: int, price: float):
        # Test version, only support XBT
        self.symbol = "XBTUSD"
        if isinstance(order_id, bytes):
            order_id = order_id.decode('utf-8')
        self.order_id = order_id
        self.side = side
        self.size = size
        self.price = price
