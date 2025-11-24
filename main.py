import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped

# Load environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")
OWNER_ID = int(os.getenv("OWNER_ID"))
DEFAULT_VOLUME = int(os.getenv("DEFAULT_VOLUME", 50))

# Initialize Pyrogram client (userbot)
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)

# Initialize PyTgCalls client
pytgcalls = PyTgCalls(app)

# Filter to respond only to OWNER_ID
owner_filter = filters.user(OWNER_ID)

@app.on_message(filters.command("play") & owner_filter)
async def play_audio(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /play <audio_file_path>")
        return
    
    audio_path = message.command[1]
    chat_id = message.chat.id
    
    try:
        # Check if already in a call; if not, join
        if not pytgcalls.is_connected(chat_id):
            await pytgcalls.join_group_call(chat_id, AudioPiped(audio_path), stream_type=1)  # 1 for audio
        else:
            # If already in call, change the stream
            await pytgcalls.change_stream(chat_id, AudioPiped(audio_path))
        
        # Set volume
        await pytgcalls.change_volume_call(chat_id, DEFAULT_VOLUME)
        
        await message.reply(f"Playing audio from {audio_path} at volume {DEFAULT_VOLUME}%")
    except Exception as e:
        await message.reply(f"Error playing audio: {str(e)}")

async def main():
    await app.start()
    await pytgcalls.start()
    print("Bot is running...")
    await asyncio.Future()  # Keep running

if __name__ == "__main__":
    asyncio.run(main())
