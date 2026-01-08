# Stock Trade Bot

股票/期货技术指标监控 Telegram Bot

## 功能

- 📊 多周期支持：1分钟、5分钟、15分钟、30分钟、60分钟、120分钟、日线
- 📈 多指标支持：MACD、KDJ、MA均线
- 🔔 实时信号推送：金叉、死叉
- 🥇 支持沪金AU9999、沪银、A股

## 安装

```bash
uv sync
```

## 配置

```bash
# Windows
set TELEGRAM_BOT_TOKEN=your_bot_token

# Linux/Mac
export TELEGRAM_BOT_TOKEN=your_bot_token
```

## 运行

```bash
uv run python main.py
```

## Bot命令

| 命令 | 说明 |
|------|------|
| `/start` | 开始使用 |
| `/add <品种> <周期> <指标>` | 添加监控任务 |
| `/remove <任务ID>` | 移除任务 |
| `/tasks` | 查看我的任务 |
| `/list_type` | 查看支持的周期和指标 |
| `/help` | 帮助信息 |

## 示例

```
/add Au99.99 60min MACD
/add Au99.99 60min KDJ
/add 000001 daily MACD
```

## 支持的周期

- `1min` - 1分钟线
- `5min` - 5分钟线
- `15min` - 15分钟线
- `30min` - 30分钟线
- `60min` - 60分钟线
- `120min` - 120分钟线
- `daily` - 日线

## 支持的指标

- `MACD` - DIF/DEA金叉死叉
- `KDJ` - K/D金叉死叉
- `MA` - MA5/MA10金叉死叉

## Docker部署

```bash
# 1. 创建.env文件
cp .env.example .env
# 编辑.env填入Bot Token

# 2. 启动
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

用户配置会持久化保存在 `./data/users.json`

