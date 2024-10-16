import os
import time
import threading
from flask import Flask, send_file
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import boto3
from datetime import datetime, timedelta

# Configuration
TEMP_FOLDER = "./videos"
EXPIRY_TIME = 12 * 60 * 60  # 12 hours in seconds

# Flask app for streaming
app = Flask(__name__)
stored_videos = {}

# Initialize S3
s3_client = boto3.client('s3')
BUCKET_NAME = 'your-s3-bucket-name'

@app.route('/stream/<video_id>')
def stream(video_id):
    if video_id in stored_videos:
        return send_file(stored_videos[video_id], mimetype='video/mp4')
    return "Video not found", 404

# Clean up after 12 hours
def cleanup_file(file_path, video_id):
    time.sleep(EXPIRY_TIME)
    if os.path.exists(file_path):
        os.remove(file_path)
        stored_videos.pop(video_id, None)

# Telegram bot handlers
async def start(update: Update, context):
    await update.message.reply_text("Send a video and use /gen to create a streaming link.")

async def handle_video(update: Update, context):
    video = update.message.video
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    
    video_file = await update.message.bot.get_file(video.file_id)
    video_path = os.path.join(TEMP_FOLDER, f"{video.file_id}.mp4")
    
    # Download the video file
    await video_file.download_to_drive(video_path)
    
    context.user_data['video_path'] = video_path
    await update.message.reply_text(f"Video uploaded. Use /gen to create a streaming link.")

async def generate_link(update: Update, context):
    if 'video_path' not in context.user_data:
        await update.message.reply_text("Please upload a video first.")
        return
    
    video_path = context.user_data['video_path']
    video_id = os.path.basename(video_path).split(".")[0]
    stored_videos[video_id] = video_path
    
    # Start cleanup in a separate thread
    threading.Thread(target=cleanup_file, args=(video_path, video_id)).start()
    
    stream_link = f"http://31.220.49.82:5000/stream/{video_id}"
    
    await update.message.reply_text(f"Your streaming link: {stream_link}\n"
                                    f"Link will expire in 12 hours.")
    
# Main function to run the bot
def main():
    # Create the bot
    application = ApplicationBuilder().token("6264504776:AAFPKj38UwNcA_ARSk0ZlLfc2nlJtxfPbGU").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(CommandHandler("gen", generate_link))
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    # Start the Telegram bot in a separate thread
    bot_thread = threading.Thread(target=main)
    bot_thread.start()
    
    # Start Flask app to serve the video files
    app.run(host='0.0.0.0', port=5000)
