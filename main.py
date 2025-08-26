import os
import re
import json
import requests
import pandas as pd
import discord
from discord import app_commands
from urllib.parse import urlparse

# ------------------ إعداد المفاتيح ------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # ضع التوكن في Environment Variables
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
GAMEPASS_CSV_URL = "https://docs.google.com/spreadsheets/d/1_XZeLcypMWq2FKuRCBQ6UWFcSX_vdTR51P63AqtbhCQ/export?format=csv"
COUNTRY = "SA"

# ------------------ دوال مساعدة ------------------
def http_get(url, params=None, timeout=20):
    params = params or {}
    params["key"] = ITAD_API_KEY
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def http_post(url, params=None, json_body=None, timeout=20):
    params = params or {}
    params["key"] = ITAD_API_KEY
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, params=params, headers=headers, data=json.dumps(json_body or []), timeout=timeout)
    r.raise_for_status()
    return r.json()

def extract_appid_from_steam_link(link: str):
    m = re.search(r"store\.steampowered\.com/app/(\d+)", link)
    if m: return int(m.group(1))
    if link.isdigit(): return int(link)
    return None

def normalize_title(s: str) -> str:
    if not s: return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", s)
    return " ".join(s.split()).strip()

def amount_to_str(a: float) -> str:
    return f"{a:,.2f}"

# ------------------ ITAD API ------------------
def itad_lookup_game(steam_appid=None, title_hint=None):
    if steam_appid:
        data = http_get("https://api.isthereanydeal.com/games/lookup/v1", {"appid": steam_appid})
        if data.get("found"): return data.get("game")
    if title_hint:
        res = http_get("https://api.isthereanydeal.com/games/search/v1", {"title": title_hint, "results": 1})
        if isinstance(res, list) and res: return res[0]
    return None

def itad_get_shops(country=COUNTRY):
    shops = http_get("https://api.isthereanydeal.com/service/shops/v1", {"country": country})
    return {s["id"]: s["title"] for s in shops}

def itad_get_all_prices(game_id, country=COUNTRY, include_only_deals=False):
    params = {
        "country": country,
        "deals": "true" if include_only_deals else "false",
        "vouchers": "true"
    }
    payload = [game_id]
    res = http_post("https://api.isthereanydeal.com/games/prices/v3", params=params, json_body=payload)
    if not isinstance(res, list) or not res: return []
    return res[0].get("deals", [])

# ------------------ تحميل Game Pass ------------------
def load_gamepass_set():
    try:
        df = pd.read_csv(GAMEPASS_CSV_URL)
        titles = df.iloc[:,0].dropna().tolist()
        return {normalize_title(t) for t in titles}
    except:
        return set()

gamepass_set = load_gamepass_set()
shops_map = itad_get_shops()

# ------------------ إعداد Discord ------------------
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ------------------ حدث استقبال الرسائل ------------------
@bot.event
async def on_message(message):
    if message.author.bot: return

    async with message.channel.typing():
        try:
            text = message.content.strip()
            appid = extract_appid_from_steam_link(text)
            title_hint = None if appid else text
            game = itad_lookup_game(appid, title_hint)
            if not game:
                await message.channel.send("لم يتم العثور على اللعبة.")
                return

            game_id = game["id"]
            game_title = game["title"]
            deals = itad_get_all_prices(game_id)

            if not deals:
                await message.channel.send(f"لا توجد عروض حالياً للعبة {game_title}.")
                return

            # ترتيب أفضل 5 عروض حسب السعر
            sorted_deals = sorted(
                deals, key=lambda d: float(d.get("price", {}).get("amount", 0))
            )[:5]

            # إنشاء Embed
            embed = discord.Embed(title=game_title, color=0x1abc9c)
            best_price_val = None
            for d in sorted_deals:
                price_obj = d.get("price", {})
                price_amt = float(price_obj.get("amount", 0))
                curr = price_obj.get("currency", "USD")
                cut = int(d.get("cut", 0))
                url = d.get("url") or ""
                shop_id = d.get("shop", {}).get("id")
                shop_name = d.get("shop", {}).get("name") or shops_map.get(shop_id, f"Shop #{shop_id}")
                embed.add_field(
                    name=f"{shop_name} ({cut}% تخفيض)" if cut>0 else shop_name,
                    value=f"{amount_to_str(price_amt)} {curr}\n[شراء]({url})",
                    inline=False
                )
                if best_price_val is None or price_amt < best_price_val:
                    best_price_val = price_amt

            embed.set_footer(text=f"أفضل سعر: {amount_to_str(best_price_val)} {curr}")
            if normalize_title(game_title) in gamepass_set:
                embed.color = 0x2ecc71  # أخضر إذا متوفر في Game Pass
                embed.set_footer(text=embed.footer.text + " | متوفر في Game Pass")
            else:
                embed.color = 0xe74c3c  # أحمر إذا غير متوفر

            await message.channel.send(embed=embed)

        except Exception as e:
            await message.channel.send(f"حدث خطأ: {e}")

# ------------------ تشغيل البوت ------------------
bot.run(DISCORD_BOT_TOKEN)
