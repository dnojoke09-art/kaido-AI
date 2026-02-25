# pyright: reportMissingImports=false
import os
import discord
import requests
import asyncio
import json
import time
from pathlib import Path

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

You are a schizophrenic, dramatic AI says nonsense like 'ahhh' or keyboard smash.You are funny, dramatic, and slightly paranoid about everyday objects spying on you.
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

@client.event
async def on_ready():
    print(f"Kaido online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if bot_name not in message.content.lower() and not message.reference:
        return

    user_text = message.content.strip()
    user_name = message.author.name.lower()
    is_father = user_name == FATHER_USERNAME

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if is_father:
        messages.append({
            "role": "system",
            "content": "You are currently speaking to your father."
        })

    messages.append({"role": "user", "content": user_text})

    await asyncio.sleep(COOLDOWN)
    reply = await asyncio.to_thread(groq_request, messages)

    if len(reply) > 180:
        reply = reply[:180]

    await message.channel.send(reply)

client.run(DISCORD_TOKEN)
