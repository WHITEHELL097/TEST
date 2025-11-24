import os
from pyrogram import Client, filters
from pytgcalls import GroupCallFactory
from pytgcalls.types.input_stream import AudioPiped

# Environment variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
DEFAULT_VOLUME = int(os.environ.get("DEFAULT_VOLUME", 100))

# Pyrogram client
app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
)

# GroupCallFactory
group_call_factory = GroupCallFactory(app, GroupCallFactory.MTPROTO_CLIENT_TYPE.PYROGRAM)

async def start_call(chat_id, audio_file):
    group_call = group_call_factory.get_group_call()
    await group_call.start(chat_id)
    await group_call.change_stream(AudioPiped(audio_file))
    await group_call.set_volume(DEFAULT_VOLUME)
    return group_call

# Command example to play audio
@app.on_message(filters.user(OWNER_ID) & filters.command("play"))
async def play_audio(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /play <audio_file_path>")
        return
    audio_file = message.command[1]
    chat_id = message.chat.id
    await start_call(chat_id, audio_file)
    await message.reply_text(f"🎵 Playing {audio_file} in VC!")

# Start the bot
print("Userbot started...")
app.run()
