import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramService:
    """Service for handling Telegram bot interactions with RAG system"""
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Persistent conversation storage 
        self.conversation_file = "conversation_history.json"
        self.conversation_history = self.load_conversations()
        self.max_history_length = 10  # Keep last 10 messages for context
        
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
    
    def split_long_message(self, text: str, max_length: int = 4096) -> list[str]:
        """Split long messages intelligently at sentence boundaries"""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        current_message = ""
        
        # Split by paragraphs first, then sentences
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_message + paragraph) <= max_length:
                if current_message:
                    current_message += "\n\n" + paragraph
                else:
                    current_message = paragraph
            else:
                # Save current message if it has content
                if current_message:
                    messages.append(current_message.strip())
                    current_message = ""
                
                # Handle long paragraphs by splitting at sentences
                if len(paragraph) > max_length:
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_message + sentence) <= max_length:
                            if current_message:
                                current_message += ". " + sentence
                            else:
                                current_message = sentence
                        else:
                            if current_message:
                                messages.append(current_message.strip())
                            current_message = sentence
                else:
                    current_message = paragraph
        
        # Add remaining content
        if current_message:
            messages.append(current_message.strip())
        
        return messages

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Send a message to a Telegram chat, splitting long messages properly"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        # Split long messages
        message_parts = self.split_long_message(text)
        
        try:
            results = []
            async with aiohttp.ClientSession() as session:
                for i, part in enumerate(message_parts):
                    url = f"{self.base_url}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": part
                    }
                    
                    async with session.post(url, json=payload) as response:
                        result = await response.json()
                        
                        if response.status == 200 and result.get("ok"):
                            results.append({
                                "success": True, 
                                "message_id": result["result"]["message_id"],
                                "part": i + 1,
                                "total_parts": len(message_parts)
                            })
                        else:
                            error_msg = result.get("description", "Unknown error")
                            logger.error(f"Failed to send message part {i+1}: {error_msg}")
                            results.append({
                                "success": False, 
                                "error": error_msg,
                                "part": i + 1
                            })
                    
                    # Small delay between parts to avoid rate limiting
                    if i < len(message_parts) - 1:
                        await asyncio.sleep(0.5)
            
            # Return success if all parts sent successfully
            all_success = all(r["success"] for r in results)
            if all_success:
                logger.info(f"All {len(message_parts)} message parts sent successfully to chat {chat_id}")
                return {"success": True, "parts": len(message_parts), "results": results}
            else:
                return {"success": False, "parts": len(message_parts), "results": results}
                        
        except Exception as e:
            logger.error(f"Exception sending Telegram message: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_to_conversation_history(self, chat_id: int, role: str, content: str):
        """Add a message to conversation history"""
        if chat_id not in self.conversation_history:
            self.conversation_history[chat_id] = []
        
        self.conversation_history[chat_id].append({
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent messages to avoid memory bloat
        if len(self.conversation_history[chat_id]) > self.max_history_length:
            self.conversation_history[chat_id] = self.conversation_history[chat_id][-self.max_history_length:]
        
        # Save to file after each addition
        self.save_conversations()
    
    def get_conversation_context(self, chat_id: int, max_messages: int = 6) -> str:
        """Get recent conversation history as context string"""
        if chat_id not in self.conversation_history:
            return ""
        
        recent_messages = self.conversation_history[chat_id][-max_messages:]
        context_parts = []
        
        for msg in recent_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def get_legal_disclaimer(self) -> str:
        """Get standard legal disclaimer for all responses"""
        return "\n\n**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*"
    
    def load_conversations(self) -> Dict[int, list]:
        """Load conversation history from file"""
        try:
            if Path(self.conversation_file).exists():
                with open(self.conversation_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to integers
                    return {int(k): v for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"Error loading conversations: {e}")
            return {}
    
    def save_conversations(self):
        """Save conversation history to file"""
        try:
            # Convert int keys to strings for JSON serialization
            data = {str(k): v for k, v in self.conversation_history.items()}
            with open(self.conversation_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversations: {e}")
    
    async def edit_message(self, chat_id: int, message_id: int, text: str) -> Dict[str, Any]:
        """Edit an existing message"""
        if not self.available:
            return {"success": False, "error": "Telegram service not available"}
        
        try:
            url = f"{self.base_url}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text[:4096]
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
            # EMERGENCY FILTER: Check user query directly for non-contract topics
            query_lower = user_query.lower().strip()
            non_contract_words = ["weather", "joke", "recipe", "cook", "food", "movie", "music", "game", "sports", "news"]
            contract_words = ["contract", "agreement", "legal", "sla", "msa", "nda", "clause", "terms", "service level"]
            
            # Only block if contains non-contract words AND no contract words
            has_non_contract = any(word in query_lower for word in non_contract_words)
            has_contract = any(word in query_lower for word in contract_words)
            
            if has_non_contract and not has_contract:
                return """I can definitely chat about that, but remember I'm here mainly to help with contracts and legal info! 😊

**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*"""
            
            # Check for filtered non-contract queries first
            if rag_result.get("error") == "FILTERED_NON_CONTRACT_QUERY":
                return rag_result.get("purpose_statement", "Hi there! 👋 I'm Lexi, your friendly legal assistant. I can help explain contracts, review clauses, and answer general legal questions. How can I assist you today?")
            
            if rag_result.get("error"):
                return f"❌ Error: {rag_result['error']}"
            
            # Handle different response formats
            if "response" in rag_result:
                # Simple chat response
                response = rag_result["response"].replace("*", "").replace("**", "")
                retrieved_chunks = rag_result.get("retrieved_chunks", 0)
                
                # Add no documents indicator if no documents available
                formatted_response = ""
                if retrieved_chunks == 0:
                    formatted_response += "📝 *No documents uploaded yet*\n\n"
                
                formatted_response += f"💡 {response}\n\n"
                
                # Always add detailed analysis section for contract responses
                formatted_response += "📋 For detailed analysis:\n"
                formatted_response += "• Upload contract documents\n"
                formatted_response += "• Ask specific legal questions"
                
                # Add legal disclaimer
                formatted_response += self.get_legal_disclaimer()
                
                return formatted_response
            
            elif "summary" in rag_result:
                # RAG analysis response
                summary = rag_result.get("summary", "")
                retrieved_chunks = rag_result.get("retrieved_chunks", 0)
                notes = rag_result.get("notes", [])
                
                # Clean up the summary text
                summary = summary.replace("*", "").replace("**", "")
                
                # Check if this is a "no documents" response
                if retrieved_chunks == 0:
                    # Always add no documents indicator at beginning
                    formatted_response = "📝 *No documents uploaded yet*\n\n"
                    
                    # Extract the main answer from summary (remove the "No documents uploaded yet." part if present)
                    main_answer = summary.replace("No documents uploaded yet.", "").strip()
                    
                    # Add the main response
                    formatted_response += f"💡 {main_answer}\n\n"
                    
                    # Always add detailed analysis section
                    formatted_response += "📋 For detailed analysis:\n"
                    formatted_response += "• Upload contract documents\n"
                    formatted_response += "• Ask specific legal questions"
                    
                    # Add legal disclaimer
                    formatted_response += self.get_legal_disclaimer()
                    
                    return formatted_response
                
                # Regular analysis with documents
                else:
                    risk_score = rag_result.get("overall_risk_score", 0)
                    formatted_response = f"📋 Contract Analysis\n\n"
                    
                    if risk_score > 0:
                        risk_emoji = "🔴" if risk_score >= 7 else "🟡" if risk_score >= 4 else "🟢"
                        formatted_response += f"{risk_emoji} Risk Score: {risk_score}/10\n\n"
                    
                    formatted_response += f"Analysis:\n{summary}"
                    
                    if retrieved_chunks > 0:
                        formatted_response += f"\n\n📄 Sources: {retrieved_chunks} document sections analyzed"
                    
                    # Add citations if available
                    citations = rag_result.get("source_citations", [])
                    if citations:
                        formatted_response += f"\n\n🔗 References: {', '.join(citations[:3])}"
                    
                    # Always add detailed analysis section
                    formatted_response += "\n\n📋 For detailed analysis:\n"
                    formatted_response += "• Upload contract documents\n"
                    formatted_response += "• Ask specific legal questions"
                    
                    # Add legal disclaimer
                    formatted_response += self.get_legal_disclaimer()
                    
                    return formatted_response
            
            else:
                # Fallback for unexpected format
                return f"🤖 Response:\n\n{str(rag_result)}"
                
        except Exception as e:
            logger.error(f"Error formatting RAG response: {str(e)}")
            return f"❌ Error formatting response: {str(e)}"
    
    def get_dummy_responses(self) -> Dict[str, str]:
        """Get predefined dummy responses for testing"""
        return {
            "hello": "Hi there! 👋 I'm Lexi, your friendly legal assistant. I can help explain contracts, review clauses, and answer general legal questions. How can I assist you today?\n\n**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*",
            
            "help": "🔍 Available Commands:\n\n• Ask me about contract terms\n• Request contract analysis\n• Ask legal questions\n• Type 'test' for a sample analysis\n\n💡 Tip: I work best when you upload contract documents first!\n\n**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*",
            
            "test": """📋 *Sample Contract Analysis*
            
🟡 *Risk Score*: 5/10

*Analysis*:
This is a test response showing how contract analysis would work. Key areas identified:

• **Payment Terms**: 30-day payment terms are standard
• **Liability**: Limited liability clauses present
• **Termination**: Standard 30-day notice required

📄 *Sources*: 3 document sections analyzed (dummy data)

🔗 *References*: [Source: doc_abc123, chunk_001], [Source: doc_abc123, chunk_002]

**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*""",
            
            "default": "🤖 I understand you're asking about contracts. While I'm ready to help, I'm currently operating in test mode. Once document ingestion is complete, I'll be able to provide detailed analysis based on your uploaded contracts!\n\n💡 Try typing 'help' to see what I can do!\n\n**Disclaimer:** *This service provides legal insights for informational purposes only; consult a qualified attorney for advice on your situation.*"
        }
    
    async def send_generating_response(self, chat_id: int, user_query: str) -> Dict[str, Any]:
        """Send typing indicator and a 'generating response' message"""
        # Send typing indicator first
        await self.send_typing_action(chat_id)
        
        # Send generating message
        generating_text = "🤔 Analyzing your question...\n\n"
        
        # Add context based on query type
        if any(term in user_query.lower() for term in ['contract', 'nda', 'agreement', 'clause']):
            generating_text += "💼 Reviewing contract knowledge and legal precedents..."
        elif any(term in user_query.lower() for term in ['risk', 'analyze', 'review']):
            generating_text += "⚖️ Conducting risk assessment and analysis..."
        else:
            generating_text += "📚 Consulting legal knowledge base..."
        
        generating_text += "\n\n⏳ This may take a few moments"
        
        result = await self.send_message(chat_id, generating_text.replace("*", ""))  # Remove markdown
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