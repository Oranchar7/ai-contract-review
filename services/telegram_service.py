import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramService:
    """Service for handling Telegram bot interactions with RAG system"""
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram functionality will be unavailable.")
            self.available = False
        else:
            self.available = True
            logger.info("Telegram service initialized successfully")
    
    async def send_typing_action(self, chat_id: int) -> Dict[str, Any]:
        """Send typing indicator to show bot is processing"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/sendChatAction"
            payload = {
                "chat_id": chat_id,
                "action": "typing"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        return {"success": True}
                    else:
                        return {"success": False, "error": result.get("description", "Unknown error")}
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Send a message to a Telegram chat"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text[:4096],  # Telegram message limit
                "parse_mode": parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        logger.info(f"Message sent successfully to chat {chat_id}")
                        return {"success": True, "message_id": result["result"]["message_id"]}
                    else:
                        error_msg = result.get("description", "Unknown error")
                        logger.error(f"Failed to send message: {error_msg}")
                        return {"success": False, "error": error_msg}
                        
        except Exception as e:
            logger.error(f"Exception sending Telegram message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def edit_message(self, chat_id: int, message_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Edit an existing message"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text[:4096],
                "parse_mode": parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        return {"success": True}
                    else:
                        error_msg = result.get("description", "Unknown error")
                        logger.error(f"Failed to edit message: {error_msg}")
                        return {"success": False, "error": error_msg}
                        
        except Exception as e:
            logger.error(f"Exception editing message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set the webhook URL for the Telegram bot"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/setWebhook"
            payload = {"url": webhook_url}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        logger.info(f"Webhook set successfully to {webhook_url}")
                        return {"success": True, "webhook_url": webhook_url}
                    else:
                        error_msg = result.get("description", "Unknown error")
                        logger.error(f"Failed to set webhook: {error_msg}")
                        return {"success": False, "error": error_msg}
                        
        except Exception as e:
            logger.error(f"Exception setting webhook: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/getWebhookInfo"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        webhook_info = result["result"]
                        logger.info(f"Webhook info retrieved: {webhook_info.get('url', 'No webhook set')}")
                        return {"success": True, "webhook_info": webhook_info}
                    else:
                        error_msg = result.get("description", "Unknown error")
                        return {"success": False, "error": error_msg}
                        
        except Exception as e:
            logger.error(f"Exception getting webhook info: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def extract_message_data(self, telegram_update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant data from Telegram webhook update"""
        try:
            if "message" not in telegram_update:
                return None
            
            message = telegram_update["message"]
            
            # Extract user and chat information
            user = message.get("from", {})
            chat = message.get("chat", {})
            
            message_data = {
                "message_id": message.get("message_id"),
                "chat_id": chat.get("id"),
                "chat_type": chat.get("type"),
                "user_id": user.get("id"),
                "username": user.get("username", ""),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "text": message.get("text", ""),
                "date": message.get("date"),
                "timestamp": datetime.now().isoformat(),
                
                # Placeholders for future RAG integration
                "jurisdiction": "unspecified",
                "contract_type": "unspecified",
                "user_context": {
                    "telegram_user_id": user.get("id"),
                    "telegram_username": user.get("username", ""),
                    "chat_type": chat.get("type", "private")
                }
            }
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error extracting message data: {str(e)}")
            return None
    
    def format_rag_response(self, rag_result: Dict[str, Any], user_query: str) -> str:
        """Format RAG response for Telegram display"""
        try:
            if rag_result.get("error"):
                return f"❌ *Error*: {rag_result['error']}"
            
            # Handle different response formats
            if "response" in rag_result:
                # Simple chat response
                response = rag_result["response"]
                return f"🤖 *AI Assistant*:\n\n{response}"
            
            elif "summary" in rag_result:
                # RAG analysis response
                summary = rag_result.get("summary", "")
                risk_score = rag_result.get("overall_risk_score", 0)
                retrieved_chunks = rag_result.get("retrieved_chunks", 0)
                
                formatted_response = f"📋 *Contract Analysis*\n\n"
                
                if risk_score > 0:
                    risk_emoji = "🔴" if risk_score >= 7 else "🟡" if risk_score >= 4 else "🟢"
                    formatted_response += f"{risk_emoji} *Risk Score*: {risk_score}/10\n\n"
                
                formatted_response += f"*Analysis*:\n{summary}"
                
                if retrieved_chunks > 0:
                    formatted_response += f"\n\n📄 *Sources*: {retrieved_chunks} document sections analyzed"
                
                # Add citations if available
                citations = rag_result.get("source_citations", [])
                if citations:
                    formatted_response += f"\n\n🔗 *References*: {', '.join(citations[:3])}"
                
                return formatted_response
            
            else:
                # Fallback for unexpected format
                return f"🤖 *Response*:\n\n{str(rag_result)}"
                
        except Exception as e:
            logger.error(f"Error formatting RAG response: {str(e)}")
            return f"❌ *Error formatting response*: {str(e)}"
    
    def get_dummy_responses(self) -> Dict[str, str]:
        """Get predefined dummy responses for testing"""
        return {
            "hello": "👋 Hello! I'm your AI Contract Assistant. I can help you analyze contracts and answer legal questions. Try asking me about contract terms or upload a document for analysis!",
            
            "help": "🔍 *Available Commands*:\n\n• Ask me about contract terms\n• Request contract analysis\n• Ask legal questions\n• Type 'test' for a sample analysis\n\n💡 *Tip*: I work best when you upload contract documents first!",
            
            "test": """📋 *Sample Contract Analysis*
            
🟡 *Risk Score*: 5/10

*Analysis*:
This is a test response showing how contract analysis would work. Key areas identified:

• **Payment Terms**: 30-day payment terms are standard
• **Liability**: Limited liability clauses present
• **Termination**: Standard 30-day notice required

📄 *Sources*: 3 document sections analyzed (dummy data)

🔗 *References*: [Source: doc_abc123, chunk_001], [Source: doc_abc123, chunk_002]""",
            
            "default": "🤖 I understand you're asking about contracts. While I'm ready to help, I'm currently operating in test mode. Once document ingestion is complete, I'll be able to provide detailed analysis based on your uploaded contracts!\n\n💡 Try typing 'help' to see what I can do!"
        }
    
    async def send_generating_response(self, chat_id: int, user_query: str) -> Dict[str, Any]:
        """Send typing indicator and a 'generating response' message"""
        # Send typing indicator first
        await self.send_typing_action(chat_id)
        
        # Send generating message
        generating_text = f"🤔 *Analyzing your question...*\n\n"
        
        # Add context based on query type
        if any(term in user_query.lower() for term in ['contract', 'nda', 'agreement', 'clause']):
            generating_text += "💼 Reviewing contract knowledge and legal precedents..."
        elif any(term in user_query.lower() for term in ['risk', 'analyze', 'review']):
            generating_text += "⚖️ Conducting risk assessment and analysis..."
        else:
            generating_text += "📚 Consulting legal knowledge base..."
        
        generating_text += "\n\n⏳ *This may take a few moments*"
        
        result = await self.send_message(chat_id, generating_text)
        return result
    
    async def send_response_with_progress(self, chat_id: int, user_query: str, response_text: str) -> Dict[str, Any]:
        """Send a generating message first, then replace it with the actual response"""
        # Send generating message
        generating_result = await self.send_generating_response(chat_id, user_query)
        
        if not generating_result.get("success"):
            # If generating message failed, just send the response normally
            return await self.send_message(chat_id, response_text)
        
        # Wait a moment for better UX
        await asyncio.sleep(1.5)
        
        # Edit the generating message with the actual response
        message_id = generating_result.get("message_id")
        if message_id:
            edit_result = await self.edit_message(chat_id, message_id, response_text)
            if edit_result.get("success"):
                return {"success": True, "method": "edited"}
            else:
                # If edit failed, send new message
                return await self.send_message(chat_id, response_text)
        else:
            # If no message_id, send new message
            return await self.send_message(chat_id, response_text)
    
    def is_available(self) -> bool:
        """Check if Telegram service is available"""
        return self.available