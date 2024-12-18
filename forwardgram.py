import requests
import yaml
import logging
import re
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from bs4 import BeautifulSoup

# Load configuration from config.yml
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)

API_ID = config['api_id']
API_HASH = config['api_hash']
DISCORD_WEBHOOK_URL = config['discord_webhook_url']
PHONE_NUMBER = config['phone_number']  # Your phone number with country code (e.g., +123456789)
CHANNEL_IDS = config['channel_ids']

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telethon client
client = TelegramClient('session_name', API_ID, API_HASH)

# Function to send messages to Discord via webhook
def send_to_discord(message, image_url=None, channel_name=None):
    embed = {
        "embeds": [
            {
                "title": "New Course Alert!",
                "description": message,
                "color": 3447003,  # Blue color
            }
        ]
    }
    
    # Add image if available
    if image_url:
        embed["embeds"][0]["image"] = {"url": image_url}

    response = requests.post(DISCORD_WEBHOOK_URL, json=embed)
    if response.status_code != 204:
        logger.error(f"Failed to send message to Discord: {response.status_code} - {response.text}")
    else:
        logger.info("Message sent to Discord successfully.")

# Function to parse the Telegram message and extract course details
def parse_course_details(message):
    # Regular expressions to extract details from the message
    title_pattern = r"^(.*)\n"  # Extracts the first line (course title)
    language_pattern = r"Language: #(\w+)"
    students_pattern = r"Students: (\d+)"
    rating_pattern = r"Rating: (\d+) / (\d+\.\d+)"
    category_pattern = r"Category: #(\w+)"
    enroll_link_pattern = r"(https?://\S+)"  # Extracts any URL (ENROLL NOW link)

    title = re.search(title_pattern, message)
    language = re.search(language_pattern, message)
    students = re.search(students_pattern, message)
    rating = re.search(rating_pattern, message)
    category = re.search(category_pattern, message)
    enroll_link = re.search(enroll_link_pattern, message)

    # Format the extracted data
    formatted_message = ""
    if title:
        formatted_message += f"**{title.group(1)}**\n\n"
    if language:
        formatted_message += f"**Language**: {language.group(1)}\n"
    if students:
        formatted_message += f"**Students**: {students.group(1)}\n"
    if rating:
        formatted_message += f"**Rating**: {rating.group(1)} / {rating.group(2)}\n"
    if category:
        formatted_message += f"**Category**: {category.group(1)}\n"

    # Add the "GET IN THIS COURSE FOR FREE NOW!" part with the extracted link
    if enroll_link:
        formatted_message += f"\n:point_right: [**GET IN THIS COURSE FOR FREE NOW!**]({enroll_link.group(1)}"

    return formatted_message, enroll_link.group(1) if enroll_link else None

# Function to extract the thumbnail image from the link
def extract_thumbnail_from_url(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for the meta tag with the property 'og:image' (common for thumbnails)
        og_image = soup.find('meta', property='og:image')
        if og_image:
            return og_image.get('content')
        else:
            logger.warning("No thumbnail found in the URL.")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching thumbnail from URL: {e}")
        return None

# Function to handle new messages from the Telegram channel
@client.on(events.NewMessage(chats=CHANNEL_IDS))
async def handler(event):
    message = event.message.text
    channel_name = event.chat.username if event.chat else None

    # Parse the message and format it for Discord
    formatted_message, enroll_link = parse_course_details(message)

    # Extract the thumbnail image from the course URL
    image_url = None
    if enroll_link:
        image_url = extract_thumbnail_from_url(enroll_link)

    # Send the formatted message to Discord
    send_to_discord(formatted_message, image_url=image_url, channel_name=channel_name)

# Function to log in to Telegram using phone number
async def login():
    # Start the client
    await client.start()
    logger.info("Logged in successfully.")
    
    # Check if 2FA is enabled
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(PHONE_NUMBER)
            await client.sign_in(PHONE_NUMBER, input("Enter the code you received: "))
        except SessionPasswordNeededError:
            password = input("Two-step verification is enabled. Please enter your password: ")
            await client.sign_in(password=password)

# Start the Telethon client
async def start_telegram_client():
    try:
        await login()
        logger.info(f"Listening to messages from {CHANNEL_IDS}")
        # Ensure event handler is added after successful login
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Error during Telegram client setup: {e}")

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(start_telegram_client())
    except Exception as e:
        logger.error(f"Error: {e}")
