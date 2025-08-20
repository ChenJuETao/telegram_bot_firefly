from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

import sys
import re
import pandas as pd
import os
from openai import OpenAI

from prompt_firefly1 import prompt_firefly
import sys
import random

client = OpenAI(api_key="sk-fac4f17d57db4120bfb12e9474c5149c", base_url="https://api.deepseek.com")

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
    messages.append({"role": "user", "content": user_message})

    # 生成多条回复
    reply_count = random.randint(1, 3)  # 随机N条回复
    all_replies = []
    
    for i in range(1,reply_count+1):
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        auto_reply = response.choices[0].message.content
        auto_reply = re_reply(auto_reply)
        all_replies.append(auto_reply)
        messages.append({"role": "assistant", "content": auto_reply})  # 每条都记录到历史
        if reply_count-i>0:
            messages.append({"role": "user", "content": "请继续说下去"})  # 继续回复
            
    return all_replies

TOKEN = "8177031461:AAFU_d1jwBUPfbJ9foBBUJ0t1IWbVZsdEqo"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('来聊聊天吧，开拓者~')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    messages = get_reply(user_input)
    for msg in messages:
        await update.message.reply_text(msg)
        await asyncio.sleep(1)  # 避免触发速率限制


# async def auto_message(context: ContextTypes.DEFAULT_TYPE):
#     """自动发送消息的函数"""
#     messages = get_reply("有什么想要分享的嘛？")
#     for msg in messages:
#         await update.message.reply_text(msg)
#         await asyncio.sleep(1)  # 避免触发速率限制


async def auto_message(context: ContextTypes.DEFAULT_TYPE):
    """自动发送消息的函数"""
    chat_id = context.job.chat_id
    messages = get_reply("有什么想要分享的嘛？")
    for msg in messages:
        await context.bot.send_message(chat_id=chat_id, text=msg)
        await asyncio.sleep(1)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """移除已存在的任务"""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


# async def start_auto_messaging(application: Application):
#     """启动自动消息任务"""
#     # 随机间隔时间（30-120分钟）
#     interval = random.randint(10, 10)  # 30-120分钟的秒数
#     application.job_queue.run_repeating(
#         auto_message, 
#         interval=interval,
#         first=10,  # 10秒后开始第一次发送
#         name="auto_message_job"
#     )


async def start_auto_messaging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """作为命令处理器时应该这样定义"""
    # 获取 application 实例
    application = context.application
    
    # 随机间隔时间（30-120分钟）
    interval = random.randint(1800, 7200)
    
    # 先移除可能存在的同名任务
    remove_job_if_exists("auto_message_job", context)
    
    # 添加新任务
    context.job_queue.run_repeating(
        auto_message, 
        interval=interval,
        first=10,
        name="auto_message_job"
    )
    
    await update.message.reply_text('已启动自动消息服务')
    

async def on_startup(application: Application):
    """应用启动时执行"""
    await start_auto_messaging(application)

from telegram.request import HTTPXRequest
def main():
    application = Application.builder().token(TOKEN).build()
    # application = (
    #     Application.builder()
    #     .token(TOKEN)
    #     .get_updates_request(HTTPXRequest(proxy_url="http://127.0.0.1:10808"))
    #     .build()
    # )

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # # 添加启动时的任务
    # application.add_handler(CommandHandler("start_auto", start_auto_messaging))
    # application.add_handler(CommandHandler("stop_auto", 
    #     lambda u, c: remove_job_if_exists("auto_message_job", c)))
    
    # 设置启动时执行
    # application.run_polling(on_startup=on_startup)
    application.run_polling()

if __name__ == '__main__':
    main()
