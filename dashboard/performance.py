"""Simple performance metrics for the paper broker's one-position-at-a-time trades."""


def calculate_performance(trades, cash, quantity, latest_price, starting_cash):
    """Calculate realized and unrealized P&L from chronological BUY/SELL rows."""
    position_quantity = 0.0
    average_entry = 0.0
    realized_pnl = 0.0
    closed_trades = 0
    winning_trades = 0
    losing_trades = 0

    for trade in sorted(trades, key=lambda item: item.get("id", 0)):
        side = str(trade["side"]).upper()
        price = float(trade["price"])
        qty = float(trade["quantity"])
        if side == "BUY" and qty > 0:
            new_quantity = position_quantity + qty
            average_entry = (
                (position_quantity * average_entry + qty * price) / new_quantity
            )
            position_quantity = new_quantity
        elif side == "SELL" and qty > 0 and position_quantity > 0:
            sold_quantity = min(qty, position_quantity)
            trade_pnl = sold_quantity * (price - average_entry)
            realized_pnl += trade_pnl
            closed_trades += 1
            if trade_pnl > 0:
                winning_trades += 1
            elif trade_pnl < 0:
                losing_trades += 1
            position_quantity -= sold_quantity
            if position_quantity <= 1e-12:
                position_quantity = 0.0
                average_entry = 0.0

    unrealized_pnl = (
        float(quantity) * (float(latest_price) - average_entry)
        if quantity and latest_price is not None and position_quantity > 0
        else 0.0
    )
    equity = float(cash) + float(quantity) * float(latest_price or 0.0)
    total_pnl = equity - float(starting_cash)
    win_rate = (winning_trades / closed_trades * 100.0) if closed_trades else 0.0

    return {
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "closed_trades": closed_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
    }
