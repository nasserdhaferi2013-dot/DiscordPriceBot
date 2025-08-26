import discord
import pandas as pd
import requests
import asyncio
from difflib import get_close_matches
import os

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GAMEPASS_CSV_URL = "https://docs.google.com/spreadsheets/d/1_XZeLcypMWq2FKuRCBQ6UWFcSX_vdTR51P63AqtbhCQ/export?format=csv"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = discord.Client(intents=intents)

# تحميل CSV من Google Sheets
def load_gamepass_csv():
    response = requests.get(GAMEPASS_CSV_URL)
    csv_data = response.content.decode('utf-8')
    df = pd.read_csv(pd.compat.StringIO(csv_data))
    return df

gamepass_df = load_gamepass_csv()

# دالة لإيجاد أقرب اسم لعبة
def find_closest_game(query, game_list):
    matches = get_close_matches(query, game_list, n=1, cutoff=0.5)
    return matches[0] if matches else None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # بدء مهمة حذف الرسائل كل دقيقة في كل القنوات
    bot.loop.create_task(periodic_cleanup())

async def periodic_cleanup():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    async for message in channel.history(limit=100):
                        if not message.pinned and message.author != bot.user:
                            await message.delete()
                except:
                    pass
        await asyncio.sleep(60)  # كل دقيقة

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_content = message.content.strip()
    closest_game = find_closest_game(user_content, gamepass_df['Game'].tolist())

    if closest_game:
        reply_text = f"{message.author.mention} أفضل سعر موجود للعبة: **{closest_game}**"
    else:
        reply_text = f"{message.author.mention} لم أتمكن من العثور على اللعبة."

    await message.reply(reply_text)

bot.run(DISCORD_BOT_TOKEN)
