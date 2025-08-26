import discord
from discord.ext import tasks
import asyncio
import os  # نحتاجها لقراءة متغير البيئة

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)

# قنوات لحذف الرسائل منها (فارغة تعني كل القنوات)
channels_to_clean = []

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    delete_old_messages.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # اقتباس الرد على الشخص نفسه
    await message.reply(f'لقد استلمت رسالتك: "{message.content}"')

# مهمة حذف الرسائل القديمة كل دقيقة
@tasks.loop(minutes=1)
async def delete_old_messages():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channels_to_clean and channel.id not in channels_to_clean:
                continue
            try:
                async for msg in channel.history(limit=200):
                    if msg.pinned:
                        continue
                    if msg.author == bot.user:
                        await msg.delete()
            except Exception as e:
                print(f"Failed to clean {channel.name}: {e}")

# قراءة التوكن من Environment Variable
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    raise ValueError("يرجى تحديد متغير البيئة DISCORD_BOT_TOKEN")

bot.run(TOKEN)
