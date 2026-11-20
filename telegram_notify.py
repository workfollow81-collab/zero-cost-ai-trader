"""Send completed virtual-strategy trade reports to Telegram."""
import os
import urllib.parse
import urllib.request

import database.db as db
from strategies.portfolio import STRATEGIES


def _format_price(value):
    return f"{float(value):.5f}"


def send_pending_strategy_reports():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    pending = db.load_pending_strategy_notifications()
    if not pending:
        return
    if not token or not chat_id:
        print(f"Telegram is not configured; {len(pending)} closed-trade report(s) remain queued.")
        return

    names = {item["id"]: item["name"] for item in STRATEGIES}
    for trade in pending:
        closed_count = int(trade["prior_closed"] or 0)
        if closed_count:
            win_rate = f"{int(trade['prior_wins']) / closed_count * 100:.1f}% ({closed_count} صفقة مغلقة سابقاً)"
        else:
            win_rate = "غير متاح — لا توجد صفقات مغلقة سابقة كافية"

        pnl = float(trade["pnl"] or 0.0)
        result = "صفقة رابحة ✅" if pnl > 0 else ("صفقة خاسرة ❌" if pnl < 0 else "تعادل")
        entry_note = trade.get("entry_note") or "غير مسجل"
        message = (
            "📊 تقرير إغلاق صفقة افتراضية\n"
            f"الاستراتيجية: {names.get(trade['strategy_id'], trade['strategy_id'])}\n"
            "الاتجاه: BUY 🟢\n"
            f"سعر الدخول: {_format_price(trade['entry_price'] or 0)}\n"
            f"سعر الإغلاق: {_format_price(trade['price'])}\n"
            f"نسبة النجاح التاريخية قبل هذه الصفقة: {win_rate}\n"
            f"أسباب الدخول: {entry_note}\n"
            f"سبب الإغلاق: {trade['note'] or 'غير مسجل'}\n"
            f"النتيجة: {result}\n"
            f"الربح/الخسارة الافتراضية: {pnl:.2f} USD"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
        if '"ok":true' not in response_body.replace(" ", "").lower():
            raise RuntimeError(f"Telegram did not confirm message delivery: {response_body[:300]}")
        db.mark_strategy_trade_notified(trade["id"])
        print(f"Telegram report sent for {trade['strategy_id']} closed trade #{trade['id']}.")
