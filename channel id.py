import yaml
from telethon.sync import TelegramClient

# Load configuration from config.yml
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

api_id = config['api_id']
api_hash = config['api_hash']
phone_number = config['phone_number']

client = TelegramClient('session_name', api_id, api_hash)

async def list_dialogs():
    await client.start(phone_number)
    dialogs = await client.get_dialogs()  # Get all dialogs (chats)
    for dialog in dialogs:
        print(f"Name: {dialog.name}, ID: {dialog.id}")

with client:
    client.loop.run_until_complete(list_dialogs())
