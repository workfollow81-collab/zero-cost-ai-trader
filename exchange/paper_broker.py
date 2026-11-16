class PaperBroker:
    def __init__(self, starting_cash, cash=None, quantity=0.0):
        self.cash = float(starting_cash if cash is None else cash)
        self.quantity = float(quantity)

    def buy(self, price, fraction=0.10):
        budget = self.cash * fraction
        if price <= 0 or budget <= 0:
            return 0.0
        qty = budget / price
        self.cash -= budget
        self.quantity += qty
        return qty

    def sell_all(self, price):
        if self.quantity <= 0 or price <= 0:
            return 0.0
        qty = self.quantity
        self.cash += qty * price
        self.quantity = 0.0
        return qty
