import discord
from discord.ext import commands, tasks
import os
import requests
import pandas as pd
import difflib
import asyncio

# ----- إعدادات البوت -----
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ----- المتغيرات -----
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
GAMEPASS_CSV_URL = "https://docs.google.com/spreadsheets/d/1_XZeLcypMWq2FKuRCBQ6UWFcSX_vdTR51P63AqtbhCQ/export?format=csv"

# ----- تحميل قائمة Game Pass -----
def load_gamepass():
    df = pd.read_csv(GAMEPASS_CSV_URL)
    return df

gamepass_df = load_gamepass()

# ----- التحقق من أقرب اسم للعبة -----
def find_closest_game(name, game_list):
    match = difflib.get_close_matches(name, game_list, n=1, cutoff=0.5)
    return match[0] if match else None

# ----- مهمة حذف الرسائل القديمة -----
@tasks.loop(minutes=1)
async def delete_old_messages():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            async for msg in channel.history(limit=100):
                if msg.pinned:
                    continue
                if msg.author != bot.user:
                    await msg.delete()

# ----- حدث تشغيل البوت -----
@bot.event
async def on_ready():
    print(f"{bot.user} جاهز للعمل")
    delete_old_messages.start()

# ----- حدث استقبال الرسائل -----
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_content = message.content.strip()

    # التحقق إذا اللعبة متوفرة على Game Pass
    game_name = find_closest_game(user_content, gamepass_df['Game'].tolist())
    if game_name:
        row = gamepass_df[gamepass_df['Game'] == game_name].iloc[0]
        if row['Available'] == 'Yes':
            color = discord.Color.green()
        else:
            color = discord.Color.red()
        embed = discord.Embed(title=f"أفضل سعر للعبة: {game_name}", description=f"{user_content}", color=color)
    else:
        embed = discord.Embed(title="لعبة غير موجودة", description="لم أتمكن من العثور على اللعبة التي تبحث عنها.", color=discord.Color.red())

    # اقتباس الرد على المستخدم
    await message.reply(embed=embed, mention_author=True)

    await bot.process_commands(message)

# ----- تشغيل البوت -----
bot.run(DISCORD_BOT_TOKEN)
