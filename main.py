import os
import time
import threading
import logging
from flask import Flask, send_file
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, PicklePersistence
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Configuration
TEMP_FOLDER = "./videos"
EXPIRY_TIME = 12 * 60 * 60  # 12 hours in seconds

# Flask app for streaming
app = Flask(__name__)
stored_videos = {}

@app.route('/stream/<video_id>')
def stream(video_id):
    """ Serve the video file for streaming """
    if video_id in stored_videos:
        return send_file(stored_videos[video_id], mimetype='video/mp4')
    return "Video not found", 404

def cleanup_file(file_path, video_id):
    """ Deletes video files after expiry """
    time.sleep(EXPIRY_TIME)
    if os.path.exists(file_path):
        os.remove(file_path)
        stored_videos.pop(video_id, None)

# Handle any video or forwarded video message
async def handle_video_message(update: Update, context):
    """ Handles video uploads and forwards, generates streaming link automatically """
    logger.info(f"Received update: {update}")
    
    # Check if the message contains a video (upload or forward)
    if update.message.video:
        video = update.message.video
        logger.info(f"Video received. File ID: {video.file_id}")

        # Download and save the video
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
        
        video_file = await context.bot.get_file(video.file_id)
        video_path = os.path.join(TEMP_FOLDER, f"{video.file_id}.mp4")
        await video_file.download_to_drive(video_path)

        # Generate and send VLC-compatible streaming link
        await generate_vlc_link(update, context, video_path)

    # Check if the message contains a document (in case video was forwarded as a document)
    elif update.message.document:
        doc = update.message.document
        logger.info(f"Document received. File name: {doc.file_name}, MIME type: {doc.mime_type}")

        # If the document is a video file, treat it as such
        if doc.mime_type.startswith('video/'):
            video_file = await context.bot.get_file(doc.file_id)
            video_path = os.path.join(TEMP_FOLDER, f"{doc.file_id}.{doc.file_name.split('.')[-1]}")
            await video_file.download_to_drive(video_path)

            # Generate and send VLC-compatible streaming link
            await generate_vlc_link(update, context, video_path)
        else:
            await update.message.reply_text("Please upload a valid video file.")

    else:
        logger.warning("No video or document found in the message.")
        await update.message.reply_text("Please upload or forward a valid video file.")

# Generate VLC-compatible streaming link for the uploaded video
async def generate_vlc_link(update: Update, context, video_path):
    """ Generates and sends a VLC-compatible streaming link for the video """
    video_id = os.path.basename(video_path).split(".")[0]
    stored_videos[video_id] = video_path

    # Start cleanup in a separate thread
    threading.Thread(target=cleanup_file, args=(video_path, video_id)).start()

    # Generate the streaming link
    stream_link = f"http://35.199.146.74:5000/stream/{video_id}"

    # Format the response with mono text for the streaming link
    response_message = (
        "Your VLC-compatible streaming link:\n\n"
        f"`{stream_link}`\n\n"
        "Link will expire in 12 hours."
    )

    # Send the formatted streaming link
    await update.message.reply_text(response_message, parse_mode="Markdown")

# Run the Flask server for streaming
def run_flask():
    """ Run Flask server for video streaming """
    app.run(host='0.0.0.0', port=5000)

# Main function to run the Telegram bot
async def main():
    """ Main function to run the Telegram bot """
    persistence = PicklePersistence(filepath="bot_data")
    application = ApplicationBuilder().token("6264504776:AAFPKj38UwNcA_ARSk0ZlLfc2nlJtxfPbGU").persistence(persistence).build()
    
    # Handle all video messages (including forwards)
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video_message))
    
    await application.run_polling()

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Run the bot in the main thread without triggering a new event loop
    asyncio.get_event_loop().run_until_complete(main())
