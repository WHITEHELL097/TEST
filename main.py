import os
import asyncio
import time
import ffmpeg
from collections import deque
from dotenv import load_dotenv

from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls import GroupCallFactory

load_dotenv()

API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
STRING_SESSION = os.getenv("STRING_SESSION") or ""
OWNER_ID = int(os.getenv("OWNER_ID") or 0)  # optional; 0 = no restriction
DEFAULT_VOLUME = int(os.getenv("DEFAULT_VOLUME") or 400)
AUDIO_FOLDER = "voice_notes"

if not API_ID or not API_HASH or not STRING_SESSION:
    raise SystemExit("Please set API_ID, API_HASH and STRING_SESSION in environment variables.")

app = Client(session_name=STRING_SESSION, api_id=API_ID, api_hash=API_HASH)
calls = PyTgCalls(app)

queue = deque()
current_chat_id = None
is_playing = False
volume = DEFAULT_VOLUME

# Helpers
def ensure_folder():
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)

async def convert_voice_to_mp3(file_path: str):
    # file_path is path to downloaded ogg/voice
    base = os.path.splitext(os.path.basename(file_path))[0]
    out = os.path.join(AUDIO_FOLDER, f"{base}.mp3")
    try:
        ffmpeg.input(file_path).output(out, ar=48000, ac=2).run(overwrite_output=True, quiet=True)
        # remove original if desired
        try:
            os.remove(file_path)
        except:
            pass
        return out
    except Exception as e:
        print("ffmpeg convert error:", e)
        return None

def get_duration(path: str) -> float:
    try:
        info = ffmpeg.probe(path)
        return float(info["format"]["duration"])
    except Exception:
        return 5.0

async def play_next():
    global is_playing, volume, current_chat_id
    if not queue or not current_chat_id:
        is_playing = False
        return

    file_path = queue.popleft()
    try:
        await calls.change_stream(current_chat_id, AudioPiped(file_path, volume=volume))
        is_playing = True
        duration = get_duration(file_path)
        await asyncio.sleep(duration + 0.7)
        # stop stream (mute)
        await calls.change_stream(current_chat_id, None)
        is_playing = False
        # continue if queue not empty
        await play_next()
    except Exception as exc:
        print("Playback error:", exc)
        is_playing = False

def owner_only(func):
    async def wrapper(client, message: Message):
        global OWNER_ID
        if OWNER_ID and message.from_user and message.from_user.id != OWNER_ID:
            await message.reply_text("❌ You are not authorized to use this command.")
            return
        return await func(client, message)
    return wrapper

# Commands

@app.on_message(filters.command("ping") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def ping(_, message: Message):
    start = time.time()
    m = await message.reply_text("🏓 Pinging...")
    latency = (time.time() - start) * 1000
    await m.edit_text(f"🏓 Pong!\n⚡ `{latency:.2f} ms`")

@app.on_message(filters.command("joinvc") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def joinvc(_, message: Message):
    global current_chat_id
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: /joinvc <group_chat_id>\nExample: /joinvc -1001234567890")

    try:
        chat_id = int(message.command[1])
        current_chat_id = chat_id
        # Join silently with no stream initially
        await calls.join_group_call(chat_id, None)
        await message.reply_text(f"✅ Joined VC of {chat_id}")
    except Exception as e:
        await message.reply_text(f"❌ Error joining voice chat: {e}")

@app.on_message(filters.command("leavevc") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def leavevc(_, message: Message):
    global is_playing, current_chat_id
    try:
        chat_id = int(message.command[1]) if len(message.command) > 1 else current_chat_id
        await calls.leave_group_call(chat_id)
        is_playing = False
        await message.reply_text("✅ Left voice chat.")
    except Exception as e:
        await message.reply_text(f"❌ Error leaving: {e}")

@app.on_message(filters.command("play") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def play_cmd(_, message: Message):
    """
    Usage:
    /play (reply to an audio/voice) OR
    /play <url>  (direct mp3/ogg url)
    """
    global is_playing, current_chat_id

    if not current_chat_id:
        return await message.reply_text("❌ I am not in any group VC. Use /joinvc <group_id> first.")

    # If it's a reply to a voice or audio
    if message.reply_to_message and (message.reply_to_message.voice or message.reply_to_message.audio or message.reply_to_message.document):
        ensure_folder()
        fname = f"{AUDIO_FOLDER}/audio_{message.reply_to_message.message_id}"
        downloaded = await message.reply_to_message.download(file_name=fname)
        # convert to mp3 (ffmpeg)
        mp3 = await convert_voice_to_mp3(downloaded)
        if not mp3:
            return await message.reply_text("❌ Conversion failed.")
        queue.append(mp3)
        await message.reply_text("📥 Added to queue (from reply).")
    elif len(message.command) > 1:
        url = message.command[1]
        # play remote url (AudioPiped supports url too)
        queue.append(url)
        await message.reply_text(f"📥 Added URL to queue: {url}")
    else:
        return await message.reply_text("❌ Usage: /play <url> OR reply /play to a voice message")

    if not is_playing:
        await play_next()

@app.on_message(filters.command("stop") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def stop_cmd(_, message: Message):
    global is_playing
    try:
        await calls.change_stream(current_chat_id, None)
        queue.clear()
        is_playing = False
        await message.reply_text("⛔ Stopped and cleared queue.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("skip") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def skip_cmd(_, message: Message):
    # skip current by forcing next
    if queue:
        await message.reply_text("⏭ Skipping...")
        await play_next()
    else:
        await message.reply_text("⚠ Queue is empty.")

@app.on_message(filters.command("volume") & (filters.user(OWNER_ID) if OWNER_ID else filters.me))
async def volume_cmd(_, message: Message):
    """
    /volume <value>
    value typical 50..1000. 100 = normal, 200 = 2x
    """
    global volume, current_chat_id, is_playing
    if len(message.command) < 2:
        return await message.reply_text(f"🔊 Current volume: {volume}")

    try:
        new_v = int(message.command[1])
        if new_v < 1:
            new_v = 1
        if new_v > 2000:
            new_v = 2000
        volume = new_v
        # if currently playing, restart stream with new volume (re-play same file)
        if is_playing and current_chat_id:
            # change_stream only takes new AudioPiped — reapply last stream as None to mute
            await calls.change_stream(current_chat_id, None)
            await asyncio.sleep(0.5)
            # start next if any
            await play_next()
        await message.reply_text(f"🔊 Volume set to {volume}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# Pyrogram lifecycle & start
async def start_bot():
    await app.start()
    await calls.start()
    print("✅ Bot started")
    # keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Stopping...")
