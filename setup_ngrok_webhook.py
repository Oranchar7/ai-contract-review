#!/usr/bin/env python3
"""
Setup ngrok tunnel and configure Telegram webhook
"""
import os
import time
import requests
import subprocess
import signal
import json
from threading import Thread

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
FASTAPI_PORT = 5000
NGROK_PATH = "./ngrok"

class NgrokTelegramSetup:
    def __init__(self):
        self.ngrok_process = None
        self.public_url = None
        
    def start_ngrok(self):
        """Start ngrok tunnel"""
        print("🚀 Starting ngrok tunnel...")
        
        # Start ngrok in background
        cmd = [NGROK_PATH, "http", str(FASTAPI_PORT), "--log=stdout"]
        self.ngrok_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for ngrok to start and get URL
        time.sleep(3)
        
        try:
            # Get ngrok API info
            response = requests.get("http://localhost:4040/api/tunnels", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("tunnels"):
                    self.public_url = data["tunnels"][0]["public_url"]
                    print(f"✅ Ngrok tunnel active: {self.public_url}")
                    return True
        except Exception as e:
            print(f"❌ Failed to get ngrok URL: {e}")
            
        return False
    
    def set_telegram_webhook(self):
        """Set Telegram webhook to ngrok URL"""
        if not self.public_url:
            print("❌ No public URL available")
            return False
            
        webhook_url = f"{self.public_url}/telegram_webhook"
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        
        print(f"🔗 Setting webhook: {webhook_url}")
        
        try:
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
                    return True
                else:
                    print(f"❌ Webhook failed: {result.get('description', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            
        return False
    
    def verify_webhook(self):
        """Verify webhook status"""
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        
        try:
            response = requests.get(telegram_api_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    webhook_info = result.get("result", {})
                    print("\n📊 Webhook Status:")
                    print(f"  URL: {webhook_info.get('url', 'Not set')}")
                    print(f"  Pending updates: {webhook_info.get('pending_update_count', 0)}")
                    print(f"  Last error: {webhook_info.get('last_error_message', 'None')}")
                    return True
        except Exception as e:
            print(f"❌ Error checking webhook: {e}")
            
        return False
    
    def cleanup(self):
        """Cleanup ngrok process"""
        if self.ngrok_process:
            print("\n🧹 Cleaning up ngrok...")
            self.ngrok_process.terminate()
            self.ngrok_process.wait()
    
    def run(self):
        """Main setup flow"""
        try:
            if not TELEGRAM_BOT_TOKEN:
                print("❌ TELEGRAM_BOT_TOKEN not found in environment")
                return False
                
            print("🤖 Setting up Telegram webhook with ngrok...")
            
            # Start ngrok
            if not self.start_ngrok():
                print("❌ Failed to start ngrok")
                return False
            
            # Set webhook
            if not self.set_telegram_webhook():
                print("❌ Failed to set webhook")
                return False
            
            # Verify setup
            self.verify_webhook()
            
            print(f"\n🎉 Setup complete! Send a message to your bot to test.")
            print(f"📱 Bot should receive messages at: {self.public_url}/telegram_webhook")
            print(f"🔍 Monitor logs in this window for incoming messages")
            print(f"\n⚠️  Keep this terminal open - ngrok tunnel will close if this script stops")
            
            # Keep running
            print("\n⏱️  Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Stopping ngrok tunnel...")
                
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
        finally:
            self.cleanup()

if __name__ == "__main__":
    setup = NgrokTelegramSetup()
    setup.run()