
class Order:
    def __init__(self, username, order_id, side: str, size: int, price: float):
        # Test version, only support XBT
        self.username = username
        self.symbol = "XBTUSD"
        self.order_id = order_id
        self.side = side
        self.size = size
        self.price = price

    def info(self):
        return f"{self.symbol}, {self.order_id}, {self.side}, {self.size}, {self.price}"