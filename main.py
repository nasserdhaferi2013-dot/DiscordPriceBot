import discord
from discord.ext import tasks
import pandas as pd
import io
import asyncio

# إعداد البوت
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# تحميل بيانات Game Pass من CSV
csv_data = """
Game,Link,Available
# ضع بيانات الألعاب هنا
Halo Infinite,https://www.microsoft.com/store/p/halo-infinite,Yes
Forza Horizon 5,https://www.microsoft.com/store/p/forza-horizon-5,Yes
Cyberpunk 2077,https://www.microsoft.com/store/p/cyberpunk-2077,No
"""
def load_gamepass_csv():
    return pd.read_csv(io.StringIO(csv_data))

gamepass_df = load_gamepass_csv()

# دالة للبحث عن أقرب اسم لعبة
def find_closest_game(user_input, game_list):
    user_input_lower = user_input.lower()
    for game in game_list:
        if game.lower() in user_input_lower:
            return game
    return None

# المهمة الدورية لحذف الرسائل القديمة كل دقيقة (ما عدا المثبتة)
@tasks.loop(minutes=1)
async def cleanup_messages():
    for guild in client.guilds:
        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=100):
                    if not message.pinned:
                        await message.delete()
            except Exception:
                pass

@client.event
async def on_ready():
    print(f'{client.user} جاهز الآن!')
    cleanup_messages.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # اقتباس رسالة المستخدم والرد عليه
    user_content = message.content
    closest_game = find_closest_game(user_content, gamepass_df['Game'].tolist())

    embed = discord.Embed(title="سعر اللعبة", color=0xff0000)  # افتراضي أحمر
    if closest_game:
        row = gamepass_df.loc[gamepass_df['Game'] == closest_game].iloc[0]
        if row['Available'] == 'Yes':
            embed.color = 0x00ff00  # أخضر إذا متاحة
        embed.description = f"{message.author.mention} أفضل سعر لـ **{closest_game}**: {row['Link']}"
    else:
        embed.description = f"{message.author.mention} اللعبة غير موجودة في قاعدة البيانات."

    await message.reply(embed=embed)

# ضع هنا التوكن
TOKEN = "توكن_البوت_هنا"
client.run(TOKEN)
