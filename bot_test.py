from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

import sys
import re
import pandas as pd
import os
import pytz
from openai import OpenAI
from datetime import datetime

from prompt_firefly1 import prompt_firefly
import sys
import random

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # 从环境变量读取
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
MODEL_TEMP = float(os.environ.get("MODEL_TEMP"))
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

messages = [
    {
        "role": "system",
        "content": prompt_firefly
    },
]

def re_reply(text):
    text = re.sub(r'\（[^)]*\）', '', text)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\"[^)]*\"', '', text)
    text = re.sub(r'\“[^)]*\”', '', text)
    text = re.sub(r'\s+', '', text)
    
    return text

def get_reply(user_message):
    global messages

    # 获取当前北京时间
    now_utc = datetime.now(pytz.utc)
    beijing_time = now_utc.astimezone(pytz.timezone('Asia/Shanghai'))
    
    messages.append({"role": "user", "content": f"【当前时间：{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}】{user_message}"})

    # 生成多条回复
    reply_count = random.randint(1, 3)  # 随机N条回复
    all_replies = []
    
    for i in range(1,reply_count+1):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=MODEL_TEMP,
            stream=False
        )
        auto_reply = response.choices[0].message.content
        auto_reply = re_reply(auto_reply)
        all_replies.append(auto_reply)
        messages.append({"role": "assistant", "content": auto_reply})  # 每条都记录到历史
        if reply_count-i>0:
            messages.append({"role": "user", "content": "请继续说下去"})  # 继续回复
            
    return all_replies


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('来聊聊天吧，开拓者~')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    messages = get_reply(user_input)
    for msg in messages:
        await update.message.reply_text(msg)
        await asyncio.sleep(1)  # 避免触发速率限制


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """移除已存在的任务"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def start_auto_messaging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """启动自动消息服务"""
    if context.job_queue is None:
        await update.message.reply_text("❌ 无法启动定时消息")
        return
    
    chat_id = update.message.chat.id
    interval = random.randint(600, 1800)  # 测试用短时间，实际可用 1800-7200（30-120分钟）
    
    # 移除旧的（如果有）
    remove_job_if_exists("auto_message_job", context)
    
    # 添加新的
    context.job_queue.run_repeating(
        auto_message,
        interval=interval,
        first=10,
        name="auto_message_job",
        chat_id=chat_id,  # 传递给回调
    )
    
    await update.message.reply_text("在干嘛呀？")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """安全移除任务"""
    if not hasattr(context, 'job_queue') or context.job_queue is None:
        return False
    
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    
    for job in current_jobs:
        job.schedule_removal()
    return True


async def auto_message(context: ContextTypes.DEFAULT_TYPE):
    """自动发送消息"""
    job = context.job
    chat_id = job.chat_id  # 获取运行时的 chat_id
    messages = get_reply("有什么想要分享的嘛？")
    for msg in messages:
        await context.bot.send_message(chat_id=chat_id, text=msg)
        await asyncio.sleep(1)
    

async def on_startup(application: Application):
    """应用启动时执行"""
    await start_auto_messaging(application)

from telegram.request import HTTPXRequest
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # 添加启动时的任务
    application.add_handler(CommandHandler("start_auto", start_auto_messaging))
    application.add_handler(CommandHandler("stop_auto", 
        lambda u, c: remove_job_if_exists("auto_message_job", c)))
    
    # 设置启动时执行
    # application.run_polling(on_startup=on_startup)
    application.run_polling()

if __name__ == '__main__':
    main()
