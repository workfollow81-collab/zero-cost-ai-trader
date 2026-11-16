import random

class MarketSimulator:
    def __init__(self, start_price=60000.0):
        self.price = float(start_price)

    def next_price(self):
        self.price *= (1 + random.uniform(-0.003, 0.003))
        return round(self.price, 2)
