# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock Trade Bot is a Chinese stock/futures technical indicator monitoring Telegram bot. It monitors multiple asset types (A-shares, gold/silver futures, cryptocurrency) and sends real-time alerts when technical indicators generate signals (golden cross, death cross, divergences).

## Common Commands

### Development

```bash
# Install dependencies
uv sync

# Run the bot locally (requires TELEGRAM_BOT_TOKEN env var)
uv run python -m stocktradebot

# Run a specific test
uv run python tests/test_data_fetch.py

# Run all tests in tests directory
uv run python -m pytest tests/ -v 2>/dev/null || find tests -name "*.py" -exec uv run python {} \;
```

### Docker Deployment

```bash
# Build and run with docker-compose
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Architecture Overview

### High-Level Flow

1. **Entry Point** (`__main__.py`): Initializes the bot, sets up scheduled polling via APScheduler, and starts the Telegram bot polling loop.

2. **Bot Layer** (`bot.py`): `StockBot` class handles Telegram commands (/add, /remove, /tasks, /backtest, /optimize) and formats alert messages. Uses `python-telegram-bot` library.

3. **Monitor Layer** (`__main__.py` - `StockMonitor`): `StockMonitor` class orchestrates periodic checking of all user tasks. Fetches data, detects signals, and sends alerts via the bot.

4. **Data Layer**:
   - `stock_data.py`: `DataFetcher` - A-shares and gold/silver futures via akshare library
   - `crypto_data.py`: `CryptoDataFetcher` - Cryptocurrency data via OKEx API

5. **Indicator Layer** (`indicators.py`): `TechnicalIndicators` class with static methods for calculating:
   - MACD (with divergence detection)
   - KDJ (with divergence detection)
   - MA (Moving Average)
   - RSI
   - Divergences (top/bottom detection with configurable window)

6. **Config Layer** (`config.py`): `ConfigManager` persists user tasks to JSON (`data/users.json`).

### Key Data Structures

**MonitorTask** (in `config.py`):
```python
@dataclass
class MonitorTask:
    task_id: str       # {symbol}_{period}_{indicator}
    symbol: str        # e.g., "Au99.99", "000001", "BTC-USDT"
    name: str          # Display name
    period: str        # "1min", "5min", ..., "60min", "daily"
    indicator: str     # "MACD", "KDJ", "MA", "RSI", "MACD_DIV", "KDJ_COMBO", etc.
    enabled: bool
    last_signal: str   # Prevents duplicate alerts
    params: dict       # e.g., {"window": 5} for divergence sensitivity
```

### Signal Detection Flow

1. **Poll Loop** (`StockMonitor.poll_all`): Runs every `POLL_INTERVAL` seconds (default 60)
2. **A-Share Trading Time Check**: `is_a_share_trading_time()` - skips non-trading hours for A-shares/ETFs
3. **Data Fetching**: Per-symbol type routing to appropriate fetcher
4. **Signal Detection**: `detect_signal()` in `__main__.py` - calls indicator-specific logic
5. **Alert Deduplication**: Checks `task.last_signal` to avoid spam
6. **Message Formatting**: `format_signal_message()` builds Markdown message with current prices and indicator values

### Supported Indicators

| Indicator | Description | Signal Types |
|-----------|-------------|--------------|
| MACD | DIF/DEA golden/death cross | MACD_GOLDEN, MACD_DEATH |
| KDJ | K/D line cross | KDJ_GOLDEN, KDJ_DEATH |
| MA | MA5/MA10 cross | MA_GOLDEN, MA_DEATH |
| RSI | Oversold/overbought breakout | RSI_GOLDEN, RSI_DEATH |
| MACD_DIV | MACD divergence (peak/trough) | MACD_DIV_BULLISH, MACD_DIV_BEARISH |
| KDJ_DIV | KDJ divergence using J value | KDJ_DIV_BULLISH, KDJ_DIV_BEARISH |
| MACD_COMBO | MACD divergence + golden cross | MACD_COMBO_BULLISH, MACD_COMBO_BEARISH |
| KDJ_COMBO | KDJ divergence + golden cross | KDJ_COMBO_BULLISH, KDJ_COMBO_BEARISH |

## Configuration & Environment

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from @BotFather |
| `POLL_INTERVAL` | No | 60 | Seconds between signal checks |
| `LOG_LEVEL` | No | INFO | DEBUG, INFO, WARNING, ERROR |
| `ENABLE_LOG_FILE` | No | false | Write logs to file |

### Data Persistence

User configurations (tasks) are stored in `data/users.json` (mounted as Docker volume). The `ConfigManager` class handles JSON serialization of `UserConfig` and `MonitorTask` dataclasses.

## Testing

Tests are in the `tests/` directory and are standalone scripts rather than using a test framework. Run individually:

```bash
# Test data fetching for Au99.99
uv run python tests/test_data_fetch.py

# Test MACD divergence detection
uv run python tests/test_gold_macd.py

# Test window sensitivity for divergence detection
uv run python tests/test_window_sensitivity.py
```

## Common Development Tasks

### Adding a New Indicator

1. Add calculation method to `TechnicalIndicators` class in `indicators.py`
2. Add signal detection logic in `detect_signal()` in `__main__.py`
3. Add indicator to `INDICATOR_TYPES` dict in `config.py`
4. Add message formatting in `format_signal_message()` in `__main__.py`
5. Add backtest support in `_detect_signals()` in `bot.py`

### Adding a New Data Source

1. Create fetcher class similar to `CryptoDataFetcher` or `DataFetcher`
2. Implement `get_<source>_history()`, `get_<source>_minute()`, `get_<source>_realtime()` methods
3. Add routing logic in `StockBot._is_<source>_symbol()` and `StockMonitor.get_data_for_task()`

## Important Notes

- **A-Share Trading Hours**: The bot automatically skips signal checks outside A-share trading hours (9:30-11:30, 13:00-15:00 Beijing time, weekdays only) for A-shares and ETFs only. Gold/silver and crypto are checked 24/7.

- **Rate Limiting**: OKEx API has rate limits. The default `POLL_INTERVAL=60` is conservative. If you increase the number of monitored tasks significantly, consider increasing the interval.

- **Data Dependencies**: This project uses `akshare` for Chinese market data. This library scrapes public data sources which may change. If data fetching fails, check for `akshare` updates.

- **Task Concurrency**: The `StockMonitor.poll_all()` method uses `asyncio.Semaphore(5)` to limit concurrent data fetching to 5 simultaneous requests. This prevents overwhelming data sources and hitting rate limits.

- **Divergence Detection Window**: The `window` parameter (default 2) in divergence indicators (`MACD_DIV`, `KDJ_DIV`, etc.) controls sensitivity. Lower values (1-2) detect more subtle divergences but may produce false positives. Higher values (3-5) are more conservative. Users can set this via `/add Au99.99 60min MACD_DIV Window=5`.
