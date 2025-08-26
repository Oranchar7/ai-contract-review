#!/usr/bin/env python3
"""
Simple ngrok tunnel setup using pyngrok
"""
import os
import time
import requests
import signal
import sys
from pyngrok import ngrok

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
FASTAPI_PORT = 5000

def setup_webhook():
    """Setup ngrok tunnel and Telegram webhook"""
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return False
    
    print("🚀 Starting ngrok tunnel...")
    
    try:
        # Start ngrok tunnel
        public_tunnel = ngrok.connect(FASTAPI_PORT)
        public_url = public_tunnel.public_url
        
        print(f"✅ Ngrok tunnel active: {public_url}")
        
        # Configure Telegram webhook
        webhook_url = f"{public_url}/telegram_webhook"
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        
        print(f"🔗 Setting webhook: {webhook_url}")
        
        response = requests.post(
            telegram_api_url,
            json={"url": webhook_url},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                print("✅ Webhook set successfully!")
                print(f"📝 Response: {result.get('description', 'Success')}")
                
                # Verify webhook status
                verify_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
                verify_response = requests.get(verify_url, timeout=10)
                
                if verify_response.status_code == 200:
                    webhook_info = verify_response.json().get("result", {})
                    print("\n📊 Webhook Status:")
                    print(f"  URL: {webhook_info.get('url', 'Not set')}")
                    print(f"  Pending updates: {webhook_info.get('pending_update_count', 0)}")
                    
                print(f"\n🎉 Setup complete!")
                print(f"📱 Bot will receive messages at: {webhook_url}")
                print(f"🔍 Send a test message to your bot now!")
                print(f"\n⚠️  Keep this script running - tunnel will close when stopped")
                
                # Keep running
                print("\n⏱️  Press Ctrl+C to stop...")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 Stopping tunnel...")
                    
                return True
            else:
                print(f"❌ Webhook failed: {result.get('description', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    finally:
        # Cleanup
        ngrok.disconnect(public_url)
        ngrok.kill()

if __name__ == "__main__":
    setup_webhook()