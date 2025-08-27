# Configuration settings for AI Contract Review application
import os

# Deployment Configuration
RENDER_URL = "https://ai-contract-review.onrender.com"
TELEGRAM_WEBHOOK_URL = f"{RENDER_URL}/telegram_webhook"

# Environment variables with fallbacks
def get_render_url():
    """Get the Render deployment URL"""
    return os.getenv("RENDER_EXTERNAL_URL", RENDER_URL)

def get_telegram_webhook_url():
    """Get the complete Telegram webhook URL"""
    base_url = get_render_url()
    return f"{base_url}/telegram_webhook"