import os
import io
import logging
import requests
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from io import BytesIO

# --- Configuration ---
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Global State (user temp data) ---
user_data = {}

# --- Helper Functions ---
def compress_image(image_bytes, quality=85):
    """Compress image to reduce size"""
    img = Image.open(BytesIO(image_bytes))
    buffer = BytesIO()
    img.save(buffer, format=img.format or 'JPEG', quality=quality, optimize=True)
    return buffer.getvalue()

def convert_image_format(image_bytes, target_format):
    """Convert image to different format"""
    img = Image.open(BytesIO(image_bytes))
    buffer = BytesIO()
    
    # Handle RGBA for JPEG conversion
    if target_format.upper() == 'JPEG' and img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    
    img.save(buffer, format=target_format)
    return buffer.getvalue()

def shorten_url(url):
    """Shorten URL using TinyURL API"""
    try:
        response = requests.get(f'https://tinyurl.com/api-create.php?url={url}', timeout=10)
        if response.status_code == 200 and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        logger.error(f"URL shortening error: {e}")
        return None

def generate_ai_image(prompt):
    """Generate image using a free AI API (Pollinations.ai)"""
    try:
        # Using Pollinations.ai - free image generation API
        encoded_prompt = requests.utils.quote(prompt)
        url = f'https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512'
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logger.error(f"AI image generation error: {e}")
        return None

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with inline keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🖼️ Convert Image", callback_data='convert'),
            InlineKeyboardButton("🎨 Generate Image", callback_data='generate')
        ],
        [
            InlineKeyboardButton("🔗 Shorten URL", callback_data='shorten'),
            InlineKeyboardButton("📖 Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **Welcome to PixFlipbot!**\n\n"
        "I can help you with:\n"
        "🖼️ **Image Conversion** - Convert PNG to JPG, WebP, etc.\n"
        "🎨 **AI Image Generation** - Create images from text prompts\n"
        "🔗 **URL Shortening** - Shorten long links instantly\n\n"
        "Select an option below or send me a file/link directly!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    await update.message.reply_text(
        "📖 **PixFlipbot Help**\n\n"
        "*Commands:*\n"
        "/start - Show main menu\n"
        "/help - Show this help\n"
        "/convert - Convert an image\n"
        "/generate - Generate AI image\n"
        "/shorten - Shorten a URL\n\n"
        "*How to use:*\n"
        "• Send me an image to convert or compress\n"
        "• Send me a URL (starting with http) to shorten\n"
        "• Use /generate followed by your prompt\n\n"
        "*Example:*\n"
        "/generate a beautiful sunset over mountains",
        parse_mode='Markdown'
    )

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start image conversion process"""
    user_data[update.effective_user.id] = {'action': 'convert'}
    await update.message.reply_text(
        "🖼️ **Image Conversion Mode**\n\n"
        "Send me an image and I'll convert it!\n"
        "Supported formats: JPG, PNG, WebP, BMP, GIF\n\n"
        "You can also send me a photo directly from your gallery.",
        parse_mode='Markdown'
    )

async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate AI image from prompt"""
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text(
            "🎨 **AI Image Generation**\n\n"
            "Usage: `/generate [your prompt]`\n\n"
            "Example: `/generate a cat riding a unicorn in space`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(f"🎨 Generating: *{prompt}*\n\n⏳ This may take a few seconds...", parse_mode='Markdown')
    
    try:
        image_data = generate_ai_image(prompt)
        if image_data:
            await update.message.reply_photo(
                photo=BytesIO(image_data),
                caption=f"🎨 Generated Image\n\nPrompt: {prompt}"
            )
        else:
            await update.message.reply_text("❌ Failed to generate image. Please try again later.")
    except Exception as e:
        logger.error(f"Generate error: {e}")
        await update.message.reply_text("❌ An error occurred while generating the image.")

async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shorten a URL"""
    url = ' '.join(context.args)
    if not url:
        await update.message.reply_text(
            "🔗 **URL Shortener**\n\n"
            "Usage: `/shorten [your_url]`\n\n"
            "Example: `/shorten https://example.com/very/long/url`",
            parse_mode='Markdown'
        )
        return
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    await update.message.reply_text(f"🔗 Shortening: `{url}`", parse_mode='Markdown')
    
    short_url = shorten_url(url)
    if short_url:
        await update.message.reply_text(
            f"✅ **URL Shortened!**\n\n"
            f"🔗 Original: {url}\n"
            f"✂️ Short: {short_url}"
        )
    else:
        await update.message.reply_text("❌ Failed to shorten URL. Please check the URL and try again.")

# --- Message Handlers ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image messages"""
    user_id = update.effective_user.id
    action = user_data.get(user_id, {}).get('action', 'convert')
    
    await update.message.reply_text("🔄 Processing your image...")
    
    try:
        # Get the image file
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Compress the image
        compressed = compress_image(image_bytes, quality=80)
        
        # Send both original and compressed
        await update.message.reply_text(
            f"✅ **Image Processed!**\n\n"
            f"📊 Original size: {len(image_bytes) // 1024} KB\n"
            f"📊 Compressed: {len(compressed) // 1024} KB\n"
            f"💾 Saved: {((len(image_bytes) - len(compressed)) / len(image_bytes) * 100):.1f}%"
        )
        
        await update.message.reply_photo(photo=BytesIO(compressed))
        
        # Show conversion options
        keyboard = [
            [
                InlineKeyboardButton("🔄 Convert to JPG", callback_data='to_jpg'),
                InlineKeyboardButton("🔄 Convert to PNG", callback_data='to_png')
            ],
            [
                InlineKeyboardButton("🔄 Convert to WebP", callback_data='to_webp'),
                InlineKeyboardButton("🔄 Convert to BMP", callback_data='to_bmp')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Choose a format to convert this image:",
            reply_markup=reply_markup
        )
        
        # Store original for conversion
        user_data[user_id]['original_image'] = image_bytes
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        await update.message.reply_text("❌ Failed to process image. Please try again.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (detect URLs)"""
    text = update.message.text.strip()
    
    # Check if it's a URL
    if text.startswith(('http://', 'https://')):
        await update.message.reply_text("🔗 Detected a URL! Shortening...")
        short_url = shorten_url(text)
        if short_url:
            await update.message.reply_text(
                f"✅ **URL Shortened!**\n\n"
                f"✂️ Short: {short_url}"
            )
        else:
            await update.message.reply_text("❌ Failed to shorten URL.")
    else:
        await update.message.reply_text(
            "I didn't understand that. Use /help to see what I can do!\n\n"
            "💡 Tip: Send me an image, a URL, or use a command."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document files (images)"""
    document = update.message.document
    if document.mime_type and document.mime_type.startswith('image/'):
        await update.message.reply_text("🔄 Processing your image...")
        try:
            file = await context.bot.get_file(document.file_id)
            image_bytes = await file.download_as_bytearray()
            
            # Compress
            compressed = compress_image(image_bytes, quality=80)
            await update.message.reply_document(document=BytesIO(compressed), filename=f"compressed_{document.file_name}")
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            await update.message.reply_text("❌ Failed to process image.")
    else:
        await update.message.reply_text("⚠️ Please send an image file.")

# --- Callback Query Handlers ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'convert':
        await query.edit_message_text(
            "🖼️ **Image Conversion**\n\n"
            "Send me an image and I'll convert it to:\n"
            "• JPG (smaller, web-friendly)\n"
            "• PNG (transparent background)\n"
            "• WebP (modern, super compressed)\n"
            "• BMP (high quality)\n\n"
            "You can send photos directly from your gallery!",
            parse_mode='Markdown'
        )
        user_data[user_id] = {'action': 'convert'}
        
    elif data == 'generate':
        await query.edit_message_text(
            "🎨 **AI Image Generation**\n\n"
            "Usage: `/generate [your prompt]`\n\n"
            "Example prompts:\n"
            "• a cyberpunk city at night\n"
            "• a cute cat astronaut\n"
            "• a mystical forest with glowing mushrooms\n\n"
            "Be creative and descriptive!",
            parse_mode='Markdown'
        )
        
    elif data == 'shorten':
        await query.edit_message_text(
            "🔗 **URL Shortener**\n\n"
            "Usage: `/shorten [your_url]`\n"
            "or just send me a link directly!\n\n"
            "Examples:\n"
            "/shorten https://very-long-url.com/12345\n"
            "https://another-long-link.com/abcdef",
            parse_mode='Markdown'
        )
        
    elif data == 'help':
        await query.edit_message_text(
            "📖 **PixFlipbot Help**\n\n"
            "*Features:*\n"
            "🖼️ Image Compression & Conversion\n"
            "🎨 AI Image Generation (via Pollinations.ai)\n"
            "🔗 URL Shortening (via TinyURL)\n\n"
            "*Quick Start:*\n"
            "• Send an image → auto compress + convert\n"
            "• Send a URL → auto shorten\n"
            "• /generate [prompt] → AI image\n\n"
            "Made with ❤️",
            parse_mode='Markdown'
        )
    
    # Image format conversion
    elif data.startswith('to_'):
        format_map = {
            'to_jpg': 'JPEG',
            'to_png': 'PNG',
            'to_webp': 'WEBP',
            'to_bmp': 'BMP'
        }
        
        target_format = format_map.get(data)
        if target_format and user_id in user_data and 'original_image' in user_data[user_id]:
            try:
                image_bytes = user_data[user_id]['original_image']
                converted = convert_image_format(image_bytes, target_format)
                
                # Determine file extension
                ext = target_format.lower()
                if ext == 'jpeg':
                    ext = 'jpg'
                
                await query.edit_message_text(f"✅ Converted to {target_format}!")
                await query.message.reply_document(
                    document=BytesIO(converted),
                    filename=f"converted.{ext}"
                )
                
            except Exception as e:
                logger.error(f"Conversion error: {e}")
                await query.edit_message_text("❌ Failed to convert image. Please try again.")

# --- Main Application ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("convert", convert_command))
    app.add_handler(CommandHandler("generate", generate_command))
    app.add_handler(CommandHandler("shorten", shorten_command))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Callback handler (for inline buttons)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🤖 PixFlipbot is starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
