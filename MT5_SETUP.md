# MetaTrader 5 Demo Setup

The MT5 bridge is intentionally disabled until the repository secrets below are configured.

## Required repository Actions secrets

Open the repository on GitHub, then go to **Settings → Secrets and variables → Actions → New repository secret** and add:

- `MT5_LOGIN`: numeric MetaQuotes-Demo account number.
- `MT5_PASSWORD`: the demo account's **master/trading password** (never put it in source code or chat).
- `MT5_SERVER`: exact server name shown by the terminal, normally `MetaQuotes-Demo`.
- `MT5_DEMO_TRADING_ENABLED`: exactly `true` to arm demo execution.

Optional secrets (defaults shown):

- `MT5_SYMBOL`: exact symbol name from Market Watch, default `EURUSD`.
- `MT5_VOLUME`: lot size, default `0.01`.
- `MT5_MAX_SPREAD_POINTS`: maximum spread in points, default `30`.

## Safety controls

- The bridge refuses to send orders unless explicitly enabled.
- It verifies both the MT5 account's demo trade mode and the connected server name contain `MetaQuotes-Demo`.
- It verifies the connected account number matches `MT5_LOGIN`.
- It never changes positions that do not carry this bot's magic number.
- It uses a fixed small default volume (0.01 lots), an ATR-based stop loss and take profit, a 2% daily realized-loss limit, a spread guard, and a duplicate-candle guard.
- The MT5 bridge uses the M5 timeframe and the existing EMA/RSI strategy.
- The Windows runner is temporary. It connects, checks the account, performs at most one eligible action, and exits. Open demo positions and their server-side SL/TP remain at the broker.

The workflow runs on GitHub-hosted Windows runners because the official MetaTrader 5 Python integration requires the Windows terminal. Standard GitHub-hosted runners are free for public repositories. No VPS or personal computer needs to stay on.

**Do not make this repository private without reviewing GitHub Actions billing first.**
