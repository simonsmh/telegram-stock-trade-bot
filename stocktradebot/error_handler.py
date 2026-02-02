"""
全局错误处理器模块
当机器人发生错误时通过 Telegram 通知用户
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    全局错误处理器 - 当机器人发生错误时通过 Telegram 通知用户
    """
    logger.error(f"处理更新时发生错误: {context.error}", exc_info=context.error)
    
    # 构建详细的错误信息
    error_type = type(context.error).__name__
    error_message = str(context.error)
    
    # 格式化错误通知消息
    notification = f"""⚠️ *机器人发生错误*

*错误类型:* `{error_type}`
*错误消息:* `{error_message[:200]}`
*发生时间:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    # 获取用户聊天 ID
    chat_id = None
    if update and update.effective_chat:
        chat_id = update.effective_chat.id
    elif update and update.callback_query:
        chat_id = update.callback_query.message.chat.id
    
    if chat_id:
        try:
            # 发送错误通知到用户
            await context.bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="Markdown"
            )
            logger.info(f"已发送错误通知到聊天 ID: {chat_id}")
        except Exception as e:
            logger.error(f"发送错误通知失败: {e}")
    else:
        logger.warning("无法获取聊天 ID，无法发送错误通知")
