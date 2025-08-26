# ngrok Authentication Setup

## Steps to Enable ngrok:

1. **Sign up for ngrok account**: https://dashboard.ngrok.com/signup
2. **Get your authtoken**: https://dashboard.ngrok.com/get-started/your-authtoken
3. **Set up authentication in Replit**:
   ```bash
   ./ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
   ```
4. **Run the setup script**:
   ```bash
   python simple_ngrok_setup.py
   ```

## Quick Alternative - Test with Current Setup:

Since your app is fully functional, you can test the Telegram bot by:
1. Deploy the app using the deployment button above
2. Use the deployment URL to set the webhook
3. Test end-to-end Telegram functionality

Your webhook URL will be: `https://[deployment-url]/telegram_webhook`