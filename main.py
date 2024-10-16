import requests
import json
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import InputFile
import os

# Set your user ID as the bot owner (replace with your actual Telegram user ID)
OWNER_ID = 6905063305  # Replace with your actual Telegram user ID
sudo_users = []

# File to store sudo users
SUDO_FILE = 'sudo_users.json'

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Load sudo users from the file if it exists
def load_sudo_users():
    global sudo_users
    try:
        with open(SUDO_FILE, 'r') as f:
            sudo_users = json.load(f)
    except FileNotFoundError:
        sudo_users = []

# Save sudo users to the file
def save_sudo_users():
    with open(SUDO_FILE, 'w') as f:
        json.dump(sudo_users, f)

# Check if the user is the owner or a sudo user
def is_authorized(user_id):
    return user_id == OWNER_ID or user_id in sudo_users

# /start command handler (only for authorized users)
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_authorized(user_id):
        update.message.reply_text("Welcome to the VLC Streaming Bot! Send me a video and reply with /gen to get the streaming link.")
    else:
        update.message.reply_text("You are not authorized to use this bot.")

# /addsudo command to add a sudo user (only for owner)
def add_sudo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("Only the bot owner can add sudo users.")
        return

    if len(context.args) != 1:
        update.message.reply_text("Usage: /addsudo <user_id>")
        return

    try:
        new_sudo_id = int(context.args[0])
        if new_sudo_id in sudo_users:
            update.message.reply_text("This user is already a sudo user.")
        else:
            sudo_users.append(new_sudo_id)
            save_sudo_users()
            update.message.reply_text(f"User {new_sudo_id} has been added as a sudo user.")
    except ValueError:
        update.message.reply_text("Please provide a valid user ID.")

# /gen command handler to generate a VLC link (only for authorized users)
def gen(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not is_authorized(user_id):
        update.message.reply_text("You are not authorized to use this command.")
        return

    if update.message.reply_to_message and update.message.reply_to_message.video:
        video_file = update.message.reply_to_message.video.get_file()
        video_file.download(f"/path/to/your/videos/{video_file.file_id}.mp4")

        # Create a VLC streaming link
        link = f"http://yourserver.com/video/{video_file.file_id}.mp4"
        update.message.reply_text(f"Here is your VLC Streaming Link: {link}")
    else:
        update.message.reply_text("Please reply to a video with the /gen command to get the streaming link.")

# /l or /leech command to download and upload a file
def leech(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not is_authorized(user_id):
        update.message.reply_text("You are not authorized to use this command.")
        return

    if len(context.args) == 0:
        update.message.reply_text("Please provide a direct download link. Usage: /leech <url>")
        return

    # Get the download link from the command
    download_url = context.args[0]
    file_name = download_url.split('/')[-1]  # Extract file name from URL

    try:
        # Download the file
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            file_path = f"/path/to/your/downloads/{file_name}"  # Temporary storage

            # Save the file locally
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Send the file to the user
            with open(file_path, 'rb') as f:
                update.message.reply_document(document=InputFile(f), filename=file_name)

            # Optionally: Delete the file after uploading to save space
            os.remove(file_path)

        else:
            update.message.reply_text(f"Failed to download the file. Status code: {response.status_code}")

    except Exception as e:
        update.message.reply_text(f"Error occurred while downloading the file: {str(e)}")

# Handler for receiving videos (only for authorized users)
def video_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if is_authorized(user_id):
        update.message.reply_text("Video received! Now, reply to this video with the /gen command to generate a streaming link.")
    else:
        update.message.reply_text("You are not authorized to send videos to this bot.")

# Main function to start the bot
def main():
    # Load sudo users from the file
    load_sudo_users()

    # Create the Updater and pass it your bot's token
    updater = Updater('7703993140:AAEuUQDfAFCp_lXDfmfcxwgEH1k9oC_m3Oc', use_context=True)
    dp = updater.dispatcher

    # Register command handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('addsudo', add_sudo))
    dp.add_handler(CommandHandler('gen', gen))
    dp.add_handler(CommandHandler(['l', 'leech'], leech))

    # Register handler to receive videos
    dp.add_handler(MessageHandler(Filters.video, video_handler))

    # Start the bot
    updater.start_polling()
    
    # Log a message that the bot has started
    logger.info("Bot started succesfully")

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

if __name__ == "__main__":
    main()
