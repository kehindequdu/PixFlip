import os
import logging
import json
from datetime import datetime
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import io

from utils.image_processor import ImageProcessor
from utils.filters import FILTERS, EFFECTS

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables. Please set TELEGRAM_BOT_TOKEN in .env file")

# Initialize image processor
image_processor = ImageProcessor()

# Store user sessions
user_sessions: Dict[int, Dict[str, Any]] = {}

# Keyboard layouts
MAIN_MENU = [
    [
        InlineKeyboardButton("🔄 Flip", callback_data="menu_flip"),
        InlineKeyboardButton("🔄 Rotate", callback_data="menu_rotate"),
        InlineKeyboardButton("🎨 Filters", callback_data="menu_filters"),
    ],
    [
        InlineKeyboardButton("✨ Effects", callback_data="menu_effects"),
        InlineKeyboardButton("🎯 Adjust", callback_data="menu_adjust"),
        InlineKeyboardButton("🖼️ Border", callback_data="menu_border"),
    ],
    [
        InlineKeyboardButton("💾 Download", callback_data="download"),
        InlineKeyboardButton("↩️ Reset", callback_data="reset"),
        InlineKeyboardButton("ℹ️ Info", callback_data="info"),
    ],
]

FLIP_MENU = [
    [
        InlineKeyboardButton("↔️ Horizontal", callback_data="flip_h"),
        InlineKeyboardButton("↕️ Vertical", callback_data="flip_v"),
        InlineKeyboardButton("🔄 Both", callback_data="flip_b"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

ROTATE_MENU = [
    [
        InlineKeyboardButton("↺ 90°", callback_data="rotate_90"),
        InlineKeyboardButton("↻ 180°", callback_data="rotate_180"),
        InlineKeyboardButton("↺ 270°", callback_data="rotate_270"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

FILTER_MENU = [
    [
        InlineKeyboardButton("🌫️ Blur", callback_data="filter_blur"),
        InlineKeyboardButton("✨ Sharpen", callback_data="filter_sharpen"),
        InlineKeyboardButton("🎯 Contour", callback_data="filter_contour"),
    ],
    [
        InlineKeyboardButton("🏛️ Emboss", callback_data="filter_emboss"),
        InlineKeyboardButton("🌊 Smooth", callback_data="filter_smooth"),
        InlineKeyboardButton("🔍 Detail", callback_data="filter_detail"),
    ],
    [
        InlineKeyboardButton("🎨 Edge Enhance", callback_data="filter_edge"),
        InlineKeyboardButton("🌓 Find Edges", callback_data="filter_find_edges"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

EFFECTS_MENU = [
    [
        InlineKeyboardButton("🎨 Sepia", callback_data="effect_sepia"),
        InlineKeyboardButton("⚫ Grayscale", callback_data="effect_grayscale"),
        InlineKeyboardButton("🔵 Invert", callback_data="effect_invert"),
    ],
    [
        InlineKeyboardButton("🌀 Posterize", callback_data="effect_posterize"),
        InlineKeyboardButton("🌈 Solarize", callback_data="effect_solarize"),
        InlineKeyboardButton("🎭 Equalize", callback_data="effect_equalize"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

ADJUST_MENU = [
    [
        InlineKeyboardButton("☀️ Brightness +", callback_data="adjust_brightness_up"),
        InlineKeyboardButton("🌙 Brightness -", callback_data="adjust_brightness_down"),
    ],
    [
        InlineKeyboardButton("🌓 Contrast +", callback_data="adjust_contrast_up"),
        InlineKeyboardButton("🌓 Contrast -", callback_data="adjust_contrast_down"),
    ],
    [
        InlineKeyboardButton("🎨 Saturation +", callback_data="adjust_saturation_up"),
        InlineKeyboardButton("🎨 Saturation -", callback_data="adjust_saturation_down"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

BORDER_MENU = [
    [
        InlineKeyboardButton("⬛ Black", callback_data="border_black"),
        InlineKeyboardButton("⬜ White", callback_data="border_white"),
        InlineKeyboardButton("🔴 Red", callback_data="border_red"),
    ],
    [
        InlineKeyboardButton("🟢 Green", callback_data="border_green"),
        InlineKeyboardButton("🔵 Blue", callback_data="border_blue"),
        InlineKeyboardButton("🟡 Yellow", callback_data="border_yellow"),
    ],
    [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
]

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    welcome_message = (
        f"👋 *Welcome to PixVisionBot, {user.first_name}!*\n\n"
        f"🎨 *Your Advanced Image Editing Assistant*\n\n"
        f"I can help you transform your images with powerful editing tools:\n\n"
        f"🔄 *Flip* - Horizontal, Vertical, or Both\n"
        f"🔄 *Rotate* - 90°, 180°, or 270°\n"
        f"🎨 *Filters* - Blur, Sharpen, Contour, and more\n"
        f"✨ *Effects* - Sepia, Grayscale, Invert, and more\n"
        f"🎯 *Adjust* - Brightness, Contrast, Saturation\n"
        f"🖼️ *Border* - Add colorful borders\n\n"
        f"📤 *Send me an image to get started!*\n"
        f"Type /help for more commands."
    )
    
    keyboard = InlineKeyboardMarkup(MAIN_MENU)
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🤖 *PixVisionBot Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/info - Bot information\n"
        "/effects - All available effects\n"
        "/cancel - Cancel current operation\n\n"
        "*How to use:*\n"
        "1️⃣ Send me an image\n"
        "2️⃣ Use the buttons to edit\n"
        "3️⃣ Download your creation\n\n"
        "*Tips:*\n"
        "• You can apply multiple effects\n"
        "• Use 'Reset' to start over\n"
        "• Download anytime to save\n"
        "• High quality images supported"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command"""
    info_text = (
        "📊 *PixVisionBot Information*\n\n"
        "🤖 *Name:* PixVisionBot\n"
        "📝 *Description:* Advanced Image Editor\n"
        "👨‍💻 *Developer:* Your Name\n"
        "📅 *Created:* 2024\n"
        "🔄 *Version:* 2.0.0\n\n"
        "*Features:*\n"
        "• 10+ filters and effects\n"
        "• Real-time preview\n"
        "• High quality output\n"
        "• Batch processing support\n"
        "• Advanced color adjustments\n\n"
        "*Stats:*\n"
        f"• Active Users: {len(user_sessions)}\n"
        "• Uptime: 24/7\n\n"
        "🔗 *Links:*\n"
        "GitHub: https://github.com/yourusername/pixvision-bot"
    )
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("✅ Operation cancelled. Send a new image to start over.")

async def effects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available effects"""
    effects_list = (
        "🎨 *Available Effects:*\n\n"
        "*Filters:*\n"
        "• Blur - Soften image\n"
        "• Sharpen - Enhance details\n"
        "• Contour - Outline edges\n"
        "• Emboss - 3D effect\n"
        "• Smooth - Reduce noise\n"
        "• Detail - Enhance texture\n"
        "• Edge Enhance - Emphasize edges\n"
        "• Find Edges - Edge detection\n\n"
        "*Effects:*\n"
        "• Sepia - Vintage look\n"
        "• Grayscale - Black & white\n"
        "• Invert - Negative effect\n"
        "• Posterize - Reduce colors\n"
        "• Solarize - Solarization\n"
        "• Equalize - Enhance contrast\n\n"
        "*Adjustments:*\n"
        "• Brightness - Light/Dark\n"
        "• Contrast - Difference\n"
        "• Saturation - Color intensity\n\n"
        "*Transformations:*\n"
        "• Flip - Mirror image\n"
        "• Rotate - Change orientation\n"
        "• Border - Add frame\n\n"
        "📤 Send an image to start editing!"
    )
    await update.message.reply_text(effects_list, parse_mode='Markdown')

# Message Handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos"""
    user_id = update.effective_user.id
    
    try:
        # Get the photo file
        photo = update.message.photo[-1]
        file = await photo.get_file()
        
        # Download image
        image_bytes = await file.download_as_bytearray()
        
        # Store in session
        user_sessions[user_id] = {
            'original': image_bytes,
            'current': image_bytes,
            'operations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Send confirmation with menu
        await update.message.reply_text(
            "✅ *Image received!*\n\nChoose an editing option below:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(MAIN_MENU)
        )
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Error processing image. Please try again.")

# Callback Handlers
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Check if user has an image
    if user_id not in user_sessions:
        await query.edit_message_text(
            "❌ No image found. Please send an image first!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Send Image", callback_data="upload")]])
        )
        return
    
    # Handle navigation
    if data == "back_main":
        await query.edit_message_text(
            "🎨 *Main Menu*\nChoose an editing option:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(MAIN_MENU)
        )
        return
    
    # Handle menu navigation
    if data == "menu_flip":
        await query.edit_message_text(
            "🔄 *Flip Options*\nChoose flip direction:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(FLIP_MENU)
        )
        return
    
    if data == "menu_rotate":
        await query.edit_message_text(
            "🔄 *Rotate Options*\nChoose rotation angle:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(ROTATE_MENU)
        )
        return
    
    if data == "menu_filters":
        await query.edit_message_text(
            "🎨 *Filters*\nChoose a filter to apply:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(FILTER_MENU)
        )
        return
    
    if data == "menu_effects":
        await query.edit_message_text(
            "✨ *Effects*\nChoose an effect to apply:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(EFFECTS_MENU)
        )
        return
    
    if data == "menu_adjust":
        await query.edit_message_text(
            "🎯 *Adjustments*\nAdjust image properties:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(ADJUST_MENU)
        )
        return
    
    if data == "menu_border":
        await query.edit_message_text(
            "🖼️ *Border Options*\nChoose border color:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(BORDER_MENU)
        )
        return
    
    # Handle operations
    try:
        session = user_sessions[user_id]
        current_image = session['current']
        operations = session.get('operations', [])
        
        # Process the operation
        if data.startswith('flip_'):
            mode = data.split('_')[1]
            result = image_processor.flip(current_image, mode)
            operations.append(f"Flip {mode}")
            
        elif data.startswith('rotate_'):
            angle = int(data.split('_')[1])
            result = image_processor.rotate(current_image, angle)
            operations.append(f"Rotate {angle}°")
            
        elif data.startswith('filter_'):
            filter_name = data.split('_')[1]
            result = image_processor.apply_filter(current_image, filter_name)
            operations.append(f"Filter: {filter_name.title()}")
            
        elif data.startswith('effect_'):
            effect = data.split('_')[1]
            result = image_processor.apply_effect(current_image, effect)
            operations.append(f"Effect: {effect.title()}")
            
        elif data.startswith('adjust_'):
            parts = data.split('_')
            adjustment = parts[1]
            direction = parts[2] if len(parts) > 2 else 'up'
            
            if adjustment == 'brightness':
                factor = 1.2 if direction == 'up' else 0.8
                result = image_processor.adjust_brightness(current_image, factor)
                operations.append(f"Brightness {'+' if direction == 'up' else '-'}")
            elif adjustment == 'contrast':
                factor = 1.2 if direction == 'up' else 0.8
                result = image_processor.adjust_contrast(current_image, factor)
                operations.append(f"Contrast {'+' if direction == 'up' else '-'}")
            elif adjustment == 'saturation':
                factor = 1.2 if direction == 'up' else 0.8
                result = image_processor.adjust_saturation(current_image, factor)
                operations.append(f"Saturation {'+' if direction == 'up' else '-'}")
                
        elif data.startswith('border_'):
            color = data.split('_')[1]
            result = image_processor.add_border(current_image, color=color, width=30)
            operations.append(f"Border: {color.title()}")
            
        elif data == "reset":
            result = session['original']
            operations = []
            session['operations'] = []
            await query.edit_message_text(
                "🔄 Image reset to original!",
                reply_markup=InlineKeyboardMarkup(MAIN_MENU)
            )
            # Update session and exit
            session['current'] = result
            return
            
        elif data == "download":
            # Send the processed image
            await query.message.reply_photo(
                photo=InputFile(io.BytesIO(current_image), filename="edited_image.png"),
                caption="✅ *Here's your edited image!*\n\nShare your creation with others!",
                parse_mode='Markdown'
            )
            return
            
        elif data == "info":
            await info_command(update, context)
            return
            
        elif data == "upload":
            await query.edit_message_text("📤 Please send me an image to edit!")
            return
            
        else:
            await query.edit_message_text("❌ Unknown operation. Please try again.")
            return
        
        # Update session
        session['current'] = result
        session['operations'] = operations
        
        # Send the processed image with menu
        await query.message.reply_photo(
            photo=InputFile(io.BytesIO(result), filename="processed_image.png"),
            caption=(
                f"✅ *Image processed!*\n"
                f"Operations applied: {', '.join(operations) if operations else 'None'}\n\n"
                f"Choose another option:"
            ),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(MAIN_MENU)
        )
        
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await query.edit_message_text(
            "❌ Error processing image. Please try again or send a new image.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Try Again", callback_data="reset")]])
        )

# Error Handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        await update.message.reply_text(
            "❌ An error occurred. Please try again later or send a new image."
        )
    except:
        pass

def main():
    """Main function"""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("effects", effects_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("🤖 PixVisionBot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
