import asyncio
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from configs import Config
from handlers.save_media import save_media_in_channel
from handlers.database import db
import os
import re

async def extract_metadata(message: Message):
    """Extract metadata from the message"""
    metadata = {
        'title': '',
        'file_size': '',
        'mime_type': '',
        'duration': None,
        'thumb': None
    }
    
    # Try to get title from caption or filename
    if message.caption:
        metadata['title'] = message.caption
    elif hasattr(message, 'document') and message.document:
        metadata['title'] = message.document.file_name
    elif hasattr(message, 'video') and message.video:
        metadata['title'] = message.video.file_name
    
    # Get file size
    if hasattr(message, 'document') and message.document:
        metadata['file_size'] = message.document.file_size
        metadata['mime_type'] = message.document.mime_type
    elif hasattr(message, 'video') and message.video:
        metadata['file_size'] = message.video.file_size
        metadata['mime_type'] = message.video.mime_type
        metadata['duration'] = message.video.duration
        if message.video.thumbs:
            metadata['thumb'] = message.video.thumbs[0].file_id
    
    # Convert file size to readable format
    if metadata['file_size']:
        size = metadata['file_size']
        if size < 1024:
            metadata['file_size'] = f"{size} B"
        elif size < 1024**2:
            metadata['file_size'] = f"{size/1024:.1f} KB"
        elif size < 1024**3:
            metadata['file_size'] = f"{size/(1024**2):.1f} MB"
        else:
            metadata['file_size'] = f"{size/(1024**3):.1f} GB"
            
    return metadata

async def format_post(message: Message, share_link: str, metadata: dict):
    """Create a formatted post with the file metadata"""
    
    # Format duration if available
    duration_text = ""
    if metadata['duration']:
        minutes = metadata['duration'] // 60
        seconds = metadata['duration'] % 60
        duration_text = f"\n⏱ Duration: {minutes}:{seconds:02d}"
    
    post_text = (
        f"📝 **Title:** {metadata['title']}\n"
        f"💾 **Size:** {metadata['file_size']}"
        f"{duration_text}\n\n"
        f"🔗 **Download Link:** {share_link}\n\n"
        f"🤖 **Upload By @{Config.BOT_USERNAME}**"
    )
    
    buttons = [[
        InlineKeyboardButton("📥 Download Now", url=share_link)
    ]]
    
    return post_text, InlineKeyboardMarkup(buttons)

async def handle_new_message(client: Client, message: Message):
    """Handle new messages from monitored channels"""
    try:
        # Only process messages with media
        if not message.media:
            return
            
        # Save the file and get the share link
        saved_msg = await save_media_in_channel(client, message, message)
        if not saved_msg:
            return
            
        # Extract metadata
        metadata = await extract_metadata(message)
        
        # Generate share link
        file_id = str(saved_msg.id)
        share_link = f"https://t.me/{Config.BOT_USERNAME}?start=PredatorHackerzZ_{file_id}"
        
        # Format the post
        post_text, reply_markup = await format_post(message, share_link, metadata)
        
        # Send formatted post to repost channel with thumbnail if available
        if Config.REPOST_CHANNEL:
            if metadata['thumb']:
                await client.send_photo(
                    chat_id=Config.REPOST_CHANNEL,
                    photo=metadata['thumb'],
                    caption=post_text,
                    reply_markup=reply_markup
                )
            else:
                await client.send_message(
                    chat_id=Config.REPOST_CHANNEL,
                    text=post_text,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
            
    except Exception as e:
        print(f"Error processing message: {str(e)}")