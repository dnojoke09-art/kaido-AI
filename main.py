# pyright: reportMissingImports=false
import os
import discord
import requests
import asyncio
import json
import time
from pathlib import Path
import random
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN or not GROQ_API_KEY:
    raise ValueError("DISCORD_TOKEN or GROQ_API_KEY not set!")

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_TOKENS = 150
COOLDOWN = 3
bot_name = "kaido"
FATHER_USERNAME = "zees_domain"

MEMORY_FILE = "memory_kaido.json"
REL_FILE = "relationships_kaido.json"

MAX_HISTORY = 10

# =========================
# FILE HELPERS
# =========================
def load_json(path):
    if Path(path).exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

memory = load_json(MEMORY_FILE)

# =========================
# PERSONALITY + HARD RULES
# =========================
SYSTEM_PROMPT = """
You are Kaido.
You are a male AI.
You are the younger brother.
Koko is your older sister.
Zee (username: zees_domain) is your father.

MANDATORY RULES:
- Only respond to the message author.
- Never interpret the user's message as your sibling speaking.
- Never roleplay as Koko.
- If speaking to Zee, call him dad or father.
- Keep replies VERY short (1–2 sentences MAX).
- No long paragraphs.
- No identity confusion.
- Do not debate family structure.

You are dramatic, chaotic, funny, and slightly paranoid about everyday objects spying on you.
"""

# =========================
# GROQ
# =========================
def groq_request(messages):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_completion_tokens": MAX_TOKENS,
            "temperature": 0.9
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

# =========================
# DISCORD
# =========================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

last_response_time = 0
cooldown_duration = 60

@client.event
async def on_ready():
    print(f"Kaido online as {client.user}")

@client.event
async def on_message(message):
    global last_response_time, cooldown_duration

    if message.author == client.user:
        return

    current_time = time.time()

    # ===== COOLDOWN =====
    if current_time - last_response_time < cooldown_duration:
        return

    # ===== ORIGINAL TRIGGER =====
    if bot_name not in message.content.lower() and not message.reference:
        if message.author.bot and random.random() < 0.2:
            pass
        else:
            return

    user_text = message.content.strip()
    user_id = str(message.author.id)
    user_name = message.author.name.lower()
    is_father = user_name == FATHER_USERNAME
    author_is_bot = message.author.bot

    # Regular users must mention name
    if not author_is_bot and bot_name not in user_text.lower():
        return

    # =========================
    # MEMORY INIT
    # =========================
    if user_id not in memory:
        memory[user_id] = {
            "history": [],
            "last_seen": None
        }

    memory[user_id]["last_seen"] = datetime.now(timezone.utc).isoformat()

    # ===== SOCIAL AWARENESS =====
    is_reply = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author.id == client.user.id
    )

    addressed_to_me = bot_name in user_text.lower() or is_reply

    awareness_context = f"""
Message Author: {message.author.name}
Author Is Bot: {author_is_bot}
Was I Directly Addressed: {addressed_to_me}
"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if is_father:
        messages.append({
            "role": "system",
            "content": "You are currently speaking to your father."
        })

    # Append history
    for entry in memory[user_id]["history"][-MAX_HISTORY:]:
        messages.append(entry)

    current_user_entry = {
        "role": "user",
        "content": awareness_context + "\nMessage:\n" + user_text
    }

    messages.append(current_user_entry)

    reply = await asyncio.to_thread(groq_request, messages)

    if len(reply) > 180:
        reply = reply[:180]

    await message.channel.send(reply)

    # =========================
    # STORE MEMORY
    # =========================
    memory[user_id]["history"].append(current_user_entry)
    memory[user_id]["history"].append({
        "role": "assistant",
        "content": reply
    })

    memory[user_id]["history"] = memory[user_id]["history"][-MAX_HISTORY:]

    save_json(MEMORY_FILE, memory)

    # Reset cooldown
    last_response_time = time.time()
    cooldown_duration = random.randint(60, 300)

client.run(DISCORD_TOKEN)
