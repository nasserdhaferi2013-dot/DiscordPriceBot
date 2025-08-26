import os
import re
import discord
import requests
import pandas as pd
from difflib import get_close_matches
from discord.ext import commands

# --- المتغيرات البيئية ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
GAMEPASS_CSV_URL = "https://docs.google.com/spreadsheets/d/1_XZeLcypMWq2FKuRCBQ6UWFcSX_vdTR51P63AqtbhCQ/export?format=csv"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="", intents=intents)  # بدون أمر محدد

# --- تحميل Game Pass ---
def load_gamepass():
    try:
        df = pd.read_csv(GAMEPASS_CSV_URL)
        titles = df.iloc[:,0].dropna().tolist()
        return [t.lower() for t in titles]
    except Exception:
        return []

gamepass_list = load_gamepass()

# --- دوال مساعدة ---
def extract_appid(link: str):
    m = re.search(r"store\.steampowered\.com/app/(\d+)", link)
    if m:
        return int(m.group(1))
    if link.isdigit():
        return int(link)
    return None

def normalize_title(s: str) -> str:
    if not s: return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", s)
    s = " ".join(s.split())
    return s.strip()

def amount_to_str(a: float) -> str:
    return f"{a:,.2f}"

# --- استدعاء API ---
BASE = "https://api.isthereanydeal.com"

def http_get(url, params=None):
    params = params or {}
    params["key"] = ITAD_API_KEY
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def http_post(url, params=None, json_body=None):
    params = params or {}
    params["key"] = ITAD_API_KEY
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, params=params, headers=headers, json=json_body, timeout=20)
    r.raise_for_status()
    return r.json()

def itad_lookup_game(steam_appid=None, title_hint=None):
    if steam_appid:
        data = http_get(f"{BASE}/games/lookup/v1", {"appid": steam_appid})
        if data.get("found"):
            return data.get("game")
    if title_hint:
        res = http_get(f"{BASE}/games/search/v1", {"title": title_hint, "results": 5})
        if isinstance(res, list) and res:
            titles = [r["title"] for r in res]
            match = get_close_matches(title_hint.lower(), [t.lower() for t in titles], n=1)
            for r in res:
                if normalize_title(r["title"]) == normalize_title(match[0]):
                    return r
    return None

def itad_get_all_prices(game_id, country="SA"):
    payload = [game_id]
    res = http_post(f"{BASE}/games/prices/v3", params={"country": country}, json_body=payload)
    if not isinstance(res, list) or not res:
        return []
    return res[0].get("deals", [])

# --- الرد على الرسائل ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    if not text:
        return

    await message.channel.trigger_typing()

    try:
        appid = extract_appid(text)
        title_hint = None if appid else text
        game = itad_lookup_game(appid, title_hint)
        if not game:
            await message.channel.send("❌ لم يتم العثور على اللعبة.")
            return

        game_id = game["id"]
        game_title = game["title"]

        deals = itad_get_all_prices(game_id)
        if not deals:
            await message.channel.send(f"ℹ️ لا توجد أسعار حالياً للعبة **{game_title}**.")
            return

        # ترتيب أفضل 5 عروض حسب السعر
        deals_sorted = sorted(deals, key=lambda d: float(d.get("price", {}).get("amount", 999999)))[:5]

        embed = discord.Embed(title=f"أفضل الأسعار للعبة: {game_title}", color=0x1abc9c)
        min_price = float('inf')
        min_index = -1
        for i, d in enumerate(deals_sorted):
            price_amt = float(d.get("price", {}).get("amount", 0.0))
            if price_amt < min_price:
                min_price = price_amt
                min_index = i

        for i, d in enumerate(deals_sorted):
            shop_name = d.get("shop", {}).get("name", "Unknown")
            price_amt = float(d.get("price", {}).get("amount", 0.0))
            curr = d.get("price", {}).get("currency", "USD")
            cut = int(d.get("cut", 0))
            url = d.get("url", "")

            line = f"{amount_to_str(price_amt)} {curr} | {cut}% خصم\n[رابط الشراء]({url})"
            color = 0x2ecc71 if i == min_index else 0x95a5a6
            embed.add_field(name=shop_name, value=line, inline=False)

        # Game Pass
        if normalize_title(game_title) in gamepass_list:
            embed.set_footer(text="✅ متوفرة في Game Pass", icon_url=None)
        else:
            embed.set_footer(text="❌ غير متوفرة في Game Pass", icon_url=None)

        await message.channel.send(embed=embed)

    except Exception as e:
        await message.channel.send(f"حدث خطأ: {str(e)}")

# --- تشغيل البوت ---
bot.run(DISCORD_BOT_TOKEN)
