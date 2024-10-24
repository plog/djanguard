import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events

# Load environment variables from .env
load_dotenv()

# Get API credentials from .env
API_ID    = os.getenv('API_ID')
API_HASH  = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Initialize the Telegram bot client
bot = TelegramClient('bot', API_ID, API_HASH)

# Start the bot
async def start_bot():
    await bot.start(bot_token=BOT_TOKEN)

# Command to start the conversation with the user
@bot.on(events.NewMessage(pattern='/start'))
async def handle_start(event):
    chat_id  = event.chat_id
    sender   = await event.get_sender()
    username = sender.username

    # Respond to the user with the chat_id and instructions
    # Respond to the user with the chat_id and a detailed explanation
    await event.respond(f"Hello {username}, your Telegram chat ID is: {chat_id}.\n\n"
                        f"Please copy this ID and add it to your profile.\n\n"
                        f"By providing this chat ID, we ensure that only you will receive important notifications and alerts "
                        f"regarding your account. This guarantees the privacy and security of your notifications, "
                        f"making sure they are sent directly to you and no one else. If you ever want to update your preferences, "
                        f"you can do so at the same profile page.")


# Keep the bot running indefinitely
async def main():
    await start_bot()
    await bot.run_until_disconnected()

# Start the bot
if __name__ == '__main__':
    asyncio.run(main())
