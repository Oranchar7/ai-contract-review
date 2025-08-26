# Render Deployment Guide
## AI Contract Review RAG System

### 🚀 Quick Deployment Steps

#### 1. **Prepare Repository**
- Ensure all files are committed to your Git repository
- Files needed: `main.py`, `render.yaml`, `requirements.txt`, `/services`, `/models`, `/templates`, `/static`

#### 2. **Create Render Service**
1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub/GitLab repository
4. Select this repository
5. Configure deployment:
   - **Name**: `ai-contract-review`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

#### 3. **Set Environment Variables**
In Render dashboard, add these variables:

**REQUIRED:**
```
OPENAI_API_KEY = your_openai_api_key
TELEGRAM_BOT_TOKEN = your_telegram_bot_token  
PINECONE_API_KEY = your_pinecone_api_key
FIREBASE_PROJECT_ID = your_firebase_project_id
FIREBASE_APP_ID = your_firebase_app_id
FIREBASE_API_KEY = your_firebase_api_key
```

**OPTIONAL:**
```
NOTIFICATION_WEBHOOK_URL = your_n8n_webhook_url
```

#### 4. **Deploy**
- Click **"Create Web Service"**
- Wait for build completion (~3-5 minutes)
- Note your public URL: `https://your-app-name.onrender.com`

#### 5. **Configure Telegram Webhook**
Replace `<YOUR_TOKEN>` and `<YOUR_RENDER_URL>`:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://<YOUR_RENDER_URL>/telegram_webhook"}'
```

Example:
```bash
curl -X POST "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://ai-contract-review.onrender.com/telegram_webhook"}'
```

#### 6. **Verify Deployment**

**Test Health Endpoint:**
```bash
curl https://your-app-name.onrender.com/health
```

**Expected Response:**
```json
{"status":"healthy","service":"ai-contract-review","firebase_connected":true}
```

**Test Telegram Webhook:**
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo"
```

**Expected Response:**
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app-name.onrender.com/telegram_webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

### 🧪 Testing Mode

#### Send Test Messages:
1. **"hello"** - Basic bot response
2. **"test"** - System status check
3. **Upload a PDF/DOCX** - Full contract analysis
4. **"chat: What is a liability clause?"** - RAG chat functionality

#### Expected Bot Responses:
- **Processing messages** with "Generating response..." indicators
- **Contract analysis** with risk scores and recommendations
- **Document chat** with context-aware answers
- **File upload support** for PDF/DOCX documents

### 🔧 Troubleshooting

**Build Fails:**
- Check `requirements.txt` contains all dependencies
- Verify Python version compatibility

**Webhook Issues:**
- Confirm webhook URL uses HTTPS
- Check Telegram bot token is valid
- Verify `/telegram_webhook` endpoint exists

**Environment Variables:**
- All required variables must be set in Render dashboard
- No spaces around `=` in variable values
- Check Firebase credentials are correct

**Runtime Errors:**
- Check Render logs in dashboard
- Verify Pinecone index exists and is accessible
- Confirm OpenAI API key has sufficient credits

### ✅ System Ready Checklist

- [ ] FastAPI server running on Render
- [ ] Health endpoint returns `{"status":"healthy"}`
- [ ] Telegram webhook set and verified
- [ ] Environment variables configured
- [ ] Pinecone RAG system connected
- [ ] Firebase integration active
- [ ] n8n workflows receiving triggers

### 🚀 Production Ready Features

Once deployed, your system supports:
- **24/7 Telegram bot** with real-time responses
- **RAG-powered contract analysis** using Pinecone
- **Document upload** and processing (PDF/DOCX)
- **Firebase data persistence** 
- **n8n workflow integration** for notifications
- **Web interface** at your Render URL
- **Auto-scaling** and SSL termination by Render