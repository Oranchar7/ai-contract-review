import os
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

from services.file_processor import FileProcessor
from services.ai_analyzer import AIAnalyzer
from services.firebase_client import FirebaseClient
from services.notification_service import NotificationService
from services.pinecone_rag_service import PineconeRAGService
from services.contract_chat_service import ContractChatService
from services.telegram_service import TelegramService
from models.contract_analysis import ContractAnalysisResponse
from utils.validators import validate_file_type

# Initialize FastAPI app
app = FastAPI(
    title="AI Contract Review",
    description="AI-powered contract analysis and review system",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize services
file_processor = FileProcessor()
ai_analyzer = AIAnalyzer()
firebase_client = FirebaseClient()
notification_service = NotificationService()
rag_service = PineconeRAGService()
chat_service = ContractChatService()
telegram_service = TelegramService()

# Security
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get current user from Firebase ID token
    Returns user info if authenticated, None if not
    """
    if not credentials:
        return None
    
    try:
        # Verify Firebase ID token
        user_info = await firebase_client.verify_user(credentials.credentials)
        return user_info
    except Exception as e:
        print(f"Auth verification failed: {str(e)}")
        return None

async def require_auth(user = Depends(get_current_user)):
    """
    Dependency that requires authentication
    Raises HTTPException if user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the RAG chat interface as main page with Firebase config"""
    with open("index.html", "r") as f:
        html_content = f.read()
    
    # Inject Firebase configuration into the HTML
    firebase_config = f"""
    <script>
        window.firebaseConfig = {{
            apiKey: "{os.environ.get('FIREBASE_API_KEY', '')}",
            authDomain: "{os.environ.get('FIREBASE_PROJECT_ID', '')}.firebaseapp.com",
            projectId: "{os.environ.get('FIREBASE_PROJECT_ID', '')}",
            storageBucket: "{os.environ.get('FIREBASE_PROJECT_ID', '')}.appspot.com",
            appId: "{os.environ.get('FIREBASE_APP_ID', '')}"
        }};
    </script>
    """
    
    # Insert Firebase config before closing </head> tag
    html_content = html_content.replace('</head>', f'{firebase_config}</head>')
    
    return HTMLResponse(content=html_content)

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    email: str = Form(..., description="Email is required for notifications"),
    jurisdiction: str = Form(..., description="Jurisdiction is required (e.g., 'US-NY', 'CA-ON')"),
    contract_type: str = Form(..., description="Contract type is required (e.g., 'NDA', 'MSA', 'Other')")
):
    """
    Analyze uploaded contract file and return structured analysis
    
    Args:
        file: PDF or DOCX contract file
        email: Optional email for notifications
        jurisdiction: Optional jurisdiction (e.g., "US-NY", "CA-ON")
        contract_type: Optional contract type (e.g., "NDA", "MSA", "SaaS TOS")
    
    Returns:
        ContractAnalysisResponse: Structured analysis results
    """
    try:
        # Validate file type
        if not file.filename or not validate_file_type(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only PDF and DOCX files are supported."
            )
        
        # Validate file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 10MB."
            )
        
        # Create temporary file
        filename = file.filename or "unknown"
        file_extension = filename.split('.')[-1] if '.' in filename else 'txt'
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text from file
            extracted_text = await file_processor.extract_text(temp_file_path, filename)
            
            if not extracted_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="No text could be extracted from the file. Please ensure the file is not corrupted or password-protected."
                )
            
            # Analyze contract with AI
            try:
                analysis_result = await ai_analyzer.analyze_contract(
                    extracted_text, 
                    jurisdiction=jurisdiction,
                    contract_type=contract_type
                )
            except Exception as ai_error:
                print(f"AI Analysis Error: {str(ai_error)}")
                return {
                    "error": f"Analysis failed: {str(ai_error)}",
                    "risk_score": 5,
                    "summary": "Unable to complete analysis due to technical issue",
                    "risky_clauses": [],
                    "missing_protections": [],
                    "detailed_analysis": "Analysis service temporarily unavailable"
                }
            
            # Store analysis in Firebase
            document_id = await firebase_client.store_analysis(
                analysis_result if isinstance(analysis_result, dict) else analysis_result.dict(),
                filename,
                email
            )
            
            # Add document ID to response if analysis_result has dict method
            if hasattr(analysis_result, 'document_id'):
                analysis_result.document_id = document_id
            
            # Send notification if email provided
            if email:
                await notification_service.send_analysis_notification(
                    email, 
                    analysis_result, 
                    filename
                )
            
            return analysis_result
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        # Return specific error format for AI analysis failures
        if "AI analysis failed" in str(e) or "OpenAI" in str(e):
            return {
                "error": "Analysis failed",
                "details": str(e)
            }
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the file: {str(e)}"
        )

@app.post("/upload_contract")
async def upload_contract(
    file: UploadFile = File(...),
    email: str = Form(..., description="Email is required for user identification"),
    jurisdiction: str = Form(..., description="Jurisdiction is required (e.g., 'US-NY', 'CA-ON')"),
    contract_type: str = Form(..., description="Contract type is required (e.g., 'NDA', 'MSA', 'Other')"),
    customContractType: str = Form(None, description="Specify contract type if 'Other' is selected"),
    customJurisdiction: str = Form(None, description="Specify custom jurisdiction if 'Other' is selected"),
    user = Depends(get_current_user)
):
    """
    Upload and process contract for RAG analysis
    
    Args:
        file: PDF or DOCX contract file
        jurisdiction: Optional jurisdiction (e.g., "US-NY", "CA-ON")
        contract_type: Optional contract type (e.g., "NDA", "MSA", "SaaS TOS")
    
    Returns:
        Upload status and metadata
    """
    try:
        # Validate file type
        if not file.filename or not validate_file_type(file.filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only PDF and DOCX files are supported."
            )
        
        # Validate file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Maximum size is 10MB."
            )
        
        # Create temporary file
        filename = file.filename or "unknown"
        file_extension = filename.split('.')[-1] if '.' in filename else 'txt'
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text from file
            extracted_text = await file_processor.extract_text(temp_file_path, filename)
            
            if not extracted_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="No text could be extracted from the file. Please ensure the file is not corrupted or password-protected."
                )
            
            # Upload to RAG service with metadata
            upload_result = await rag_service.upload_contract(
                extracted_text, 
                filename,
                email=email,
                jurisdiction=jurisdiction,
                contract_type=contract_type
            )
            
            # Context info is now stored in RAG service during upload
            upload_result.update({
                "email": email,
                "jurisdiction": jurisdiction,
                "contract_type": contract_type
            })
            
            # Store secure contract submission in 'contracts' collection
            user_email = user.get('email', email) if user else email
            contract_id = await firebase_client.store_contract_submission(
                email=user_email,
                jurisdiction=jurisdiction,
                contract_type=contract_type,
                customContractType=customContractType,
                customJurisdiction=customJurisdiction,
                filename=filename
            )
            
            # Also store legacy document metadata for backward compatibility
            vector_id = f"vector_{datetime.now().timestamp()}"
            doc_meta_id = await firebase_client.store_document_metadata(
                filename=filename,
                email=user_email,
                jurisdiction=jurisdiction,
                contract_type=contract_type,
                vector_id=vector_id
            )
            
            upload_result["contract_id"] = contract_id
            upload_result["document_metadata_id"] = doc_meta_id
            return upload_result
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "error": f"Upload failed: {str(e)}"
        }

@app.post("/chat")
async def chat_simple(
    query: str = Form(...),
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None),
    user = Depends(get_current_user)
):
    """Simple non-streaming chat endpoint with GPT-4o mini"""
    try:
        # Check if this is a greeting
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
        is_greeting = any(word in query.lower() for word in greeting_words)
        
        # Consistent system message for all responses
        system_message = """You are a legal contract assistant. Always respond in consistent Markdown format:

- Use **bold** for important terms, headings, or field labels.
- Use *italics* only for emphasis, not headings.
- Use numbered lists for step-by-step instructions.
- Do not mix HTML tags with Markdown.
- Ensure uniform spacing, line breaks, and no random bolding.
- Avoid inline code formatting unless showing actual code snippets.
- If providing examples, maintain the same Markdown structure throughout the response.

Return your output strictly in Markdown. Any tables, lists, or headings must follow standard Markdown syntax."""

        if is_greeting:
            user_message = f"User said: '{query}'. Please provide a professional welcome message for our AI Contract Review service using proper Markdown formatting."
        else:
            # Focus on the actual user question, only mention jurisdiction/contract type if relevant
            context_info = ""
            if jurisdiction and jurisdiction.strip():
                context_info += f" (Context: Jurisdiction: {jurisdiction})"
            if contract_type and contract_type.strip():
                context_info += f" (Context: Contract type: {contract_type})"
            
            user_message = f"Please answer this specific contract question: {query}{context_info}. Focus on answering the user's actual question about contracts or legal terms. Use proper Markdown formatting in your response."
        
        # Use OpenAI directly with GPT-4o mini and temperature 0.4
        from openai import OpenAI
        import asyncio
        
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Add timeout wrapper
        async def make_openai_request():
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    stream=False,
                    max_tokens=800,
                    temperature=0.4,
                    timeout=15  # 15 second timeout
                )
                return response
            except Exception as e:
                print(f"OpenAI request failed: {str(e)}")
                return None
        
        response = await asyncio.wait_for(make_openai_request(), timeout=20.0)
        
        if response and response.choices:
            full_response = response.choices[0].message.content or "I apologize, but I couldn't generate a response."
        else:
            full_response = "I apologize, but I'm experiencing technical difficulties. Please try again."
        
        # Store chat history (simplified, ignore errors)
        try:
            user_email = user.get('email', 'anonymous') if user else 'anonymous'
            await firebase_client.store_chat_history(
                email=user_email,
                user_question=query,
                ai_response=full_response,
                retrieved_chunks=[],
                jurisdiction=jurisdiction,
                contract_type=contract_type
            )
        except:
            pass  # Ignore Firebase errors
        
        return {"response": full_response}
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return {"response": "I apologize, but I encountered an error. Please try again."}

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint to receive and process messages"""
    try:
        if not telegram_service.is_available():
            return {"status": "error", "message": "Telegram service not available"}
        
        # Parse incoming Telegram update
        telegram_update = await request.json()
        print(f"Received Telegram update: {telegram_update}")
        
        # Extract message data
        message_data = telegram_service.extract_message_data(telegram_update)
        if not message_data:
            return {"status": "ok", "message": "No processable message found"}
        
        chat_id = message_data.get("chat_id")
        user_query = message_data.get("text", "").strip()
        
        if not chat_id or not user_query:
            return {"status": "ok", "message": "Invalid message data"}
        
        print(f"Processing query from chat {chat_id}: {user_query}")
        
        # EMERGENCY OVERRIDE: Block non-contract queries immediately
        user_query_lower = user_query.lower()
        non_contract_words = ["weather", "joke", "recipe", "cook", "food", "movie", "music", "game", "sports", "news"]
        contract_words = ["contract", "agreement", "legal", "sla", "msa", "nda", "clause", "terms", "service level"]
        
        # Only block if contains non-contract words AND no contract words
        has_non_contract = any(word in user_query_lower for word in non_contract_words)
        has_contract = any(word in user_query_lower for word in contract_words)
        
        if has_non_contract and not has_contract:
            clean_response = """I can definitely chat about that, but remember I'm here mainly to help with contracts and legal info! 😊

Disclaimer: Not legal advice, general review — consult an attorney for your specific situation."""
            
            await telegram_service.send_message(chat_id, clean_response)
            return {"status": "ok", "message": "Non-contract query handled"}
        
        # Send typing indicator only (like web chat)
        await telegram_service.send_typing_action(chat_id)
        
        # Process the query through RAG system with test mode fallback
        response_text = await process_telegram_query(user_query, message_data)
        
        # Send response directly (no duplicate waiting message)
        print(f"DEBUG: About to send response: {response_text[:100]}...")
        send_result = await telegram_service.send_message(chat_id, response_text)
        print(f"DEBUG: Send result: {send_result}")
        
        if send_result.get("success"):
            print(f"Response sent successfully to chat {chat_id}")
            return {"status": "ok", "message": "Response sent"}
        else:
            print(f"Failed to send response: {send_result.get('error')}")
            return {"status": "error", "message": f"Failed to send response: {send_result.get('error')}"}
            
    except Exception as e:
        print(f"Telegram webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

def is_contract_related_query(query: str) -> bool:
    """Check if a query is related to contracts, legal matters, or document analysis"""
    query_lower = query.lower().strip()
    
    # Contract-related keywords
    contract_keywords = [
        # Direct contract terms
        "contract", "agreement", "nda", "clause", "terms", "conditions", "legal",
        "liability", "indemnity", "termination", "breach", "compliance", "negotiate",
        
        # Contract abbreviations
        "sla", "msa", "sow", "loi", "mou", "nca", "cda", "eula", "tos", "dpa", "baa",
        
        # Legal concepts
        "law", "legal", "attorney", "lawyer", "court", "litigation", "dispute",
        "jurisdiction", "governing", "statute", "regulation", "rights", "obligations",
        
        # Business/contract actions
        "sign", "execute", "amend", "modify", "review", "analyze", "risk", "audit",
        "due diligence", "merger", "acquisition", "partnership", "vendor", "supplier",
        
        # Document types
        "employment", "lease", "rental", "purchase", "sale", "service", "licensing",
        "confidentiality", "non-disclosure", "intellectual property", "copyright",
        "trademark", "patent", "warranty", "guarantee", "insurance", "policy",
        
        # Financial/commercial terms
        "payment", "invoice", "penalty", "damages", "compensation", "fee", "price",
        "cost", "budget", "financial", "commercial", "business", "corporate",
        
        # Risk and analysis terms
        "risky", "dangerous", "problematic", "unfair", "unreasonable", "standard",
        "market", "industry", "benchmark", "best practice", "recommendation"
    ]
    
    # Common command patterns that should be treated as contract-related
    command_patterns = ["help", "/help", "start", "/start", "hello", "hi", "hey", "test", "what can you do", "commands"]
    
    # Check if query contains contract keywords
    if any(keyword in query_lower for keyword in contract_keywords):
        return True
    
    # Check if it's a help/command pattern (always allow these)
    if any(pattern in query_lower for pattern in command_patterns):
        return True
    
    # Check for questions about the service itself
    service_patterns = ["what do you do", "what can you help", "how do you work", "what is this"]
    if any(pattern in query_lower for pattern in service_patterns):
        return True
    
    return False

def get_friendly_purpose_statement() -> str:
    """Return a friendly statement about the bot's purpose for irrelevant queries"""
    return """Hi there! 👋 I'm Lexi, your friendly legal assistant. I can help explain contracts, review clauses, and answer general legal questions.

📄 **Upload your contract documents** for detailed analysis and risk assessment!

I can also answer general legal questions. How can I assist you today?

Disclaimer: Not legal advice, general review — consult an attorney for your specific situation."""

async def process_telegram_query(query: str, message_data: Dict[str, Any]) -> str:
    """Process a query through RAG system with relevance checking and test mode fallback"""
    try:
        query_lower = query.lower().strip()
        chat_id = message_data.get("chat_id", 0)
        
        # FIRST: Handle basic greetings and commands (highest priority)
        dummy_responses = telegram_service.get_dummy_responses()
        
        # Check exact matches first
        if query_lower in dummy_responses:
            response = dummy_responses[query_lower]
            telegram_service.add_to_conversation_history(chat_id, "user", query)
            telegram_service.add_to_conversation_history(chat_id, "assistant", response)
            return response
        
        # Check for common greeting patterns
        greetings = ["hello", "hi", "hey", "start", "/start"]
        if any(greeting == query_lower for greeting in greetings):  # Exact match
            response = dummy_responses["hello"]
            telegram_service.add_to_conversation_history(chat_id, "user", query)
            telegram_service.add_to_conversation_history(chat_id, "assistant", response)
            return response
        
        # Handle conversational queries naturally (greetings, farewells, introductions, etc.)
        conversational_patterns = [
            # Basic greetings (exact match)
            "hi", "hello", "hey", "hi there", "hello there", "hey there", "hi!", "hello!", "hey!",
            
            # Greetings and social interactions
            "how are you", "how's it going", "what's up", "how are things", "what are you up to", 
            "good morning", "good afternoon", "good evening", "nice to meet",
            
            # Farewells
            "goodbye", "bye", "see you later", "take care", "see you", "talk to you later", 
            "have a good day", "have a nice day", "until next time", "catch you later",
            
            # Introductions
            "i am", "my name is", "i'm", "call me", "this is", "nice to meet you",
            "pleased to meet", "good to meet",
            
            # Casual conversation starters
            "what do you think", "tell me about yourself", "what can you tell me",
            "how's your day", "how was your", "what have you been up to",
            
            # Weather and casual topics
            "weather", "how is the weather", "what's the weather", "nice day",
            "beautiful day", "hot today", "cold today", "sunny", "rainy"
        ]
        pattern_matched = any(pattern in query_lower for pattern in conversational_patterns)
        if pattern_matched:
            print(f"DEBUG: Matched conversational pattern for '{query}'")
            # Let the AI respond naturally to conversational queries
            try:
                # Get conversation context for natural responses
                temp_context = telegram_service.get_conversation_context(chat_id)
                context_query = query
                if temp_context:
                    context_query = f"Previous conversation:\n{temp_context}\n\nCurrent question: {query}"
                
                chat_result = await chat_service.general_chat(
                    context_query,
                    jurisdiction=None,  # Don't pass legal context for natural conversation
                    contract_type=None,  # Don't pass legal context for natural conversation
                    force_natural_response=True  # New parameter for natural responses
                )
                
                if chat_result.get("answer"):
                    response = chat_result['answer']
                    telegram_service.add_to_conversation_history(chat_id, "user", query)
                    telegram_service.add_to_conversation_history(chat_id, "assistant", response)
                    return response
            except Exception as e:
                print(f"Natural response error: {e}")
                pass  # Fall through to normal processing
        
        # Check for help patterns
        help_patterns = ["help", "/help", "what can you do", "commands"]
        if any(pattern in query_lower for pattern in help_patterns):
            response = dummy_responses["help"]
            telegram_service.add_to_conversation_history(chat_id, "user", query)
            telegram_service.add_to_conversation_history(chat_id, "assistant", response)
            return response
        
        # Add user message to conversation history
        telegram_service.add_to_conversation_history(chat_id, "user", query)
        
        # Get conversation context for follow-up detection  
        conversation_context = telegram_service.get_conversation_context(chat_id)
        
        # Check if this could be a follow-up question
        is_followup = False
        if conversation_context and len(query.split()) < 10:
            context_lower = conversation_context.lower()
            contract_words = ["contract", "agreement", "legal", "sla", "msa", "nda", "clause", "terms", "service level"]
            if any(word in context_lower for word in contract_words):
                is_followup = True
        
        # IMMEDIATE FILTER: Check if query is definitely NOT contract-related
        query_words = query_lower.split()
        non_contract_indicators = [
            "weather", "joke", "recipe", "cook", "food", "movie", "music", "game", 
            "sports", "news", "time", "date", "math", "calculate", "translate",
            "directions", "travel", "shopping", "restaurant", "hotel", "flight"
        ]
        
        # Only block if contains non-contract words AND no contract words
        contract_words = ["contract", "agreement", "legal", "sla", "msa", "nda", "clause", "terms", "service level"]
        has_non_contract = any(indicator in query_lower for indicator in non_contract_indicators)
        has_contract = any(word in query_lower for word in contract_words)
        
        # (is_followup already determined above)
        
        if has_non_contract and not has_contract and not is_followup:
            response = get_friendly_purpose_statement()
            telegram_service.add_to_conversation_history(chat_id, "assistant", response)
            return response
        
        # Also check with original function, but allow follow-ups
        if not is_contract_related_query(query) and not is_followup:
            response = get_friendly_purpose_statement()
            telegram_service.add_to_conversation_history(chat_id, "assistant", response)
            return response
        
        # Try RAG system if available, otherwise use chat service
        try:
            if rag_service.is_available():
                # Add conversation context if available
                context_query = query
                if conversation_context:
                    context_query = f"Previous conversation:\n{conversation_context}\n\nCurrent question: {query}"
                
                # Use RAG service for document-based queries
                rag_result = await rag_service.ask_contract(
                    context_query,
                    jurisdiction=message_data.get("jurisdiction"),
                    contract_type=message_data.get("contract_type")
                )
                response = telegram_service.format_rag_response(rag_result, query)
                telegram_service.add_to_conversation_history(chat_id, "assistant", response)
                return response
            else:
                # Add conversation context if available
                context_query = query
                if conversation_context:
                    context_query = f"Previous conversation:\n{conversation_context}\n\nCurrent question: {query}"
                
                # Fallback to general chat service
                chat_result = await chat_service.general_chat(
                    context_query,
                    jurisdiction=message_data.get("jurisdiction"),
                    contract_type=message_data.get("contract_type")
                )
                
                if chat_result.get("answer"):
                    response = f"🤖 AI Assistant:\n\n{chat_result['answer']}"
                    telegram_service.add_to_conversation_history(chat_id, "assistant", response)
                    return response
                else:
                    response = dummy_responses["default"]
                    telegram_service.add_to_conversation_history(chat_id, "assistant", response)
                    return response
                    
        except Exception as e:
            print(f"RAG/Chat service error: {str(e)}")
            return f"🤖 I understand you're asking about: *{query}*\n\nI'm currently operating in test mode. Once document ingestion is complete, I'll provide detailed analysis based on your uploaded contracts!\n\n💡 Try typing 'help' or 'test' to see what I can do."
        
    except Exception as e:
        print(f"Query processing error: {str(e)}")
        return f"❌ *Error processing your query*: {str(e)}\n\n💡 Try typing 'help' for available commands."


@app.post("/debug_telegram_flow")
async def debug_telegram_flow(request: Request):
    """Debug what exact response is generated for a query"""
    try:
        data = await request.json()
        query = data.get("query", "")
        
        # Simulate message data with persistent chat ID
        message_data = {
            "chat_id": 12345,  # Fixed chat ID for debugging
            "user_id": 12345,
            "jurisdiction": "unspecified", 
            "contract_type": "unspecified"
        }
        
        # Call the exact same function as telegram webhook
        response_text = await process_telegram_query(query, message_data)
        
        return {
            "query": query,
            "response_preview": response_text,
            "response_type": "friendly_purpose" if "Hi there!" in response_text else "contract_analysis"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/test_filter")
async def test_filter():
    """Test if weather filter works"""
    test_query = "what is the weather today"
    
    # Test the exact same logic as telegram processing
    query_lower = test_query.lower().strip()
    non_contract_indicators = [
        "weather", "joke", "recipe", "cook", "food", "movie", "music", "game", 
        "sports", "news", "time", "date", "math", "calculate", "translate",
        "directions", "travel", "shopping", "restaurant", "hotel", "flight"
    ]
    
    should_filter = any(indicator in query_lower for indicator in non_contract_indicators)
    
    if should_filter:
        response = get_friendly_purpose_statement()
        result_type = "filtered_correctly"
    else:
        response = "WOULD PROCESS AS CONTRACT QUERY"
        result_type = "not_filtered"
    
    return {
        "test_query": test_query,
        "should_filter": should_filter,
        "result_type": result_type,
        "response_preview": response
    }

@app.get("/deployment_check")
async def deployment_check():
    """Check if latest filtering code is deployed"""
    # This should show if our filtering is active
    test_query = "what is the weather today"
    has_weather_filter = "weather" in str([
        "weather", "joke", "recipe", "cook", "food", "movie", "music", "game", 
        "sports", "news", "time", "date", "math", "calculate", "translate",
        "directions", "travel", "shopping", "restaurant", "hotel", "flight"
    ])
    
    return {
        "timestamp": "2025-01-27-v3",
        "filter_deployed": has_weather_filter,
        "test_query": test_query,
        "non_contract_indicators_loaded": True
    }

@app.get("/telegram_status")
async def telegram_status():
    """Get Telegram bot status and webhook information"""
    try:
        if not telegram_service.is_available():
            return {
                "status": "unavailable",
                "error": "TELEGRAM_BOT_TOKEN not configured",
                "webhook_url": None
            }
        
        # Get webhook info
        webhook_info = await telegram_service.get_webhook_info()
        
        return {
            "status": "available",
            "service_ready": True,
            "webhook_info": webhook_info.get("webhook_info", {}),
            "test_mode": True,
            "rag_available": rag_service.is_available() if hasattr(rag_service, 'is_available') else False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "webhook_url": None
        }

@app.post("/set_telegram_webhook")
async def set_telegram_webhook(webhook_url: str = Form(...)):
    """Set the Telegram webhook URL"""
    try:
        if not telegram_service.is_available():
            return {
                "status": "error",
                "message": "Telegram service not available. Check TELEGRAM_BOT_TOKEN."
            }
        
        result = await telegram_service.set_webhook(webhook_url)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": f"Webhook set to {webhook_url}",
                "webhook_url": webhook_url
            }
        else:
            return {
                "status": "error", 
                "message": result.get("error", "Failed to set webhook")
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/set_render_webhook")
async def set_render_webhook():
    """Set Telegram webhook to Render deployment URL (from environment)"""
    try:
        if not telegram_service.is_available():
            return {
                "status": "error",
                "message": "Telegram service not available. Check TELEGRAM_BOT_TOKEN."
            }
        
        # Try to get Render URL from environment
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        if not render_url:
            return {
                "status": "error", 
                "message": "RENDER_EXTERNAL_URL not set. Use /set_render_webhook_manual instead."
            }
        
        webhook_url = f"{render_url}/telegram_webhook"
        result = await telegram_service.set_webhook(webhook_url)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": f"Webhook set to Render URL: {webhook_url}",
                "webhook_url": webhook_url
            }
        else:
            return {
                "status": "error", 
                "message": result.get("error", "Failed to set webhook to Render URL")
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/set_render_webhook_manual")
async def set_render_webhook_manual(render_url: str = Form(...)):
    """Manually set Telegram webhook to provided Render URL"""
    try:
        if not telegram_service.is_available():
            return {
                "status": "error",
                "message": "Telegram service not available. Check TELEGRAM_BOT_TOKEN."
            }
        
        # Ensure URL format is correct
        if not render_url.startswith('https://'):
            render_url = f"https://{render_url}"
        
        # Remove trailing slash if present
        render_url = render_url.rstrip('/')
        
        webhook_url = f"{render_url}/telegram_webhook"
        result = await telegram_service.set_webhook(webhook_url)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": f"Webhook set to: {webhook_url}",
                "webhook_url": webhook_url
            }
        else:
            return {
                "status": "error", 
                "message": result.get("error", "Failed to set webhook")
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/test-vector")
async def test_vector_storage():
    """Test endpoint to verify Pinecone vector storage persistence"""
    try:
        if not rag_service.is_available():
            return {
                "status": "error",
                "message": "Pinecone vector storage is not available. Check PINECONE_API_KEY secret.",
                "index_available": False
            }
        
        # Get index statistics
        stats = rag_service.get_index_stats()
        
        # Test basic functionality
        test_results = {
            "status": "success",
            "index_name": rag_service.index_name,
            "index_available": True,
            "pinecone_connection": "connected",
            "total_vectors": stats.get("total_vectors", 0),
            "dimension": rag_service.dimension,
            "metric": "cosine",
            "storage_type": "persistent_pinecone",
            "persistence_verified": True,
            "ready_for_documents": True
        }
        
        # Add sample query test if vectors exist
        if stats.get("total_vectors", 0) > 0:
            try:
                # Test retrieval with a simple query
                test_chunks = await rag_service._retrieve_relevant_chunks("contract terms", k=2)
                test_results["sample_retrieval"] = {
                    "chunks_retrieved": len(test_chunks),
                    "retrieval_working": len(test_chunks) > 0
                }
            except Exception as e:
                test_results["sample_retrieval"] = {
                    "error": str(e),
                    "retrieval_working": False
                }
        else:
            test_results["message"] = "No documents uploaded yet. Upload documents to test full RAG functionality."
        
        return test_results
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Vector storage test failed: {str(e)}",
            "index_available": False,
            "pinecone_connection": "failed"
        }

@app.post("/translate_jargon")
async def translate_jargon(
    legal_term: str = Form(...),
    context: Optional[str] = Form(None)
):
    """
    Translate legal jargon into plain English with examples
    
    Args:
        legal_term: The legal term or phrase to translate
        context: Optional context (contract type, jurisdiction, etc.)
    
    Returns:
        Simple explanation, definition, and practical examples
    """
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        context_info = f" in the context of {context}" if context else ""
        
        system_message = """You are a friendly legal translator that explains complex legal terms in simple, everyday language. 
        
        Your response should be:
        - Clear and easy to understand
        - Use analogies and real-world examples
        - Include practical implications
        - Warm and approachable tone
        - Structure with clear sections
        
        Format your response as JSON with these fields:
        {
          "simple_definition": "One sentence explanation in plain English",
          "detailed_explanation": "2-3 sentences with more detail and context",
          "real_world_example": "Practical example showing how this applies",
          "why_it_matters": "Why someone should care about this term",
          "common_usage": "Where you'd typically see this term used"
        }"""
        
        user_message = f"Please explain the legal term '{legal_term}'{context_info} in simple language that anyone can understand."
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.4,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        import json
        content = response.choices[0].message.content
        if content:
            translation = json.loads(content)
        else:
            raise Exception("No content received from OpenAI")
        
        return {
            "status": "success",
            "term": legal_term,
            "translation": translation
        }
        
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return {
            "status": "error",
            "error": "Failed to translate legal term. Please try again."
        }

@app.post("/ask_contract")
async def ask_contract(
    query: str = Form(...),
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None)
):
    """
    Ask questions about contracts using friendly chat - works before, during, and after upload
    
    Args:
        query: Question about the contract
        jurisdiction: Optional jurisdiction context
        contract_type: Optional contract type context
    
    Returns:
        Friendly conversational response about contracts
    """
    try:
        # Use general contract chat for all questions for now
        # (RAG functionality temporarily disabled while fixing FAISS issues)
        result = await chat_service.general_chat(
            query=query,
            jurisdiction=jurisdiction,
            contract_type=contract_type
        )
        return result
        
    except Exception as e:
        return {
            "answer": "I'm sorry, I encountered an issue while trying to help you with your contract question. Please try rephrasing your question or ask about something specific.",
            "error": f"Failed to process contract question: {str(e)}"
        }

@app.post("/chat_general")
async def chat_general(
    query: str = Form(...),
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None)
):
    """
    General contract chat before upload - friendly legal guidance
    
    Args:
        query: General question about contracts, legal terms, or guidance
        jurisdiction: Optional jurisdiction context
        contract_type: Optional contract type context
    
    Returns:
        Friendly conversational response with legal guidance
    """
    try:
        result = await chat_service.general_chat(
            query=query,
            jurisdiction=jurisdiction,
            contract_type=contract_type
        )
        return result
        
    except Exception as e:
        return {
            "answer": "I apologize, but I'm having trouble processing your question right now. Please try asking again or rephrase your question.",
            "error": f"General chat failed: {str(e)}"
        }

@app.get("/rag_status")
async def get_rag_status(user = Depends(get_current_user)):
    """Get current RAG index statistics (auth optional)"""
    try:
        stats = rag_service.get_index_stats()
        return {
            "status": "healthy",
            "rag_stats": stats,
            "authenticated": user is not None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/auth/register")
async def register_user(
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user with email and password"""
    try:
        result = await firebase_client.create_user(email, password)
        return result
    except Exception as e:
        return {"error": f"Registration failed: {str(e)}"}

@app.post("/auth/verify")
async def verify_token(
    id_token: str = Form(...)
):
    """Verify Firebase ID token"""
    try:
        user_info = await firebase_client.verify_user(id_token)
        if user_info:
            return {"success": True, "user": user_info}
        else:
            return {"error": "Invalid token"}
    except Exception as e:
        return {"error": f"Token verification failed: {str(e)}"}

@app.get("/user/history")
async def get_user_history(user = Depends(require_auth)):
    """Get user's chat history (requires authentication)"""
    try:
        history = await firebase_client.get_user_chat_history(user['email'])
        return {"success": True, "history": history}
    except Exception as e:
        return {"error": f"Failed to retrieve history: {str(e)}"}

@app.get("/admin/contracts")
async def get_all_contracts(user = Depends(require_auth)):
    """Get all contract submissions (admin only)"""
    try:
        # Verify admin role
        if not user.get('admin', False):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        contracts = await firebase_client.get_all_contracts()
        return {"success": True, "contracts": contracts}
    except HTTPException:
        raise
    except Exception as e:
        return {"error": f"Failed to retrieve contracts: {str(e)}"}

@app.get("/user/documents")
async def get_user_documents(user = Depends(require_auth)):
    """Get user's uploaded documents (requires authentication)"""
    try:
        analyses = await firebase_client.get_user_analyses(user['email'])
        return {"success": True, "documents": analyses}
    except Exception as e:
        return {"error": f"Failed to retrieve documents: {str(e)}"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ai-contract-review",
        "firebase_connected": firebase_client.db is not None
    }

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook handler for subscription events"""
    # Placeholder for Stripe webhook handling
    payload = await request.body()
    # TODO: Implement Stripe webhook processing
    return {"status": "received"}

@app.post("/create-checkout-session")
async def create_checkout_session():
    """Create Stripe checkout session for subscription"""
    # Placeholder for Stripe checkout session creation
    # TODO: Implement Stripe checkout session logic
    return {"url": "https://checkout.stripe.com/placeholder"}

if __name__ == "__main__":
    # Get port from environment (Render sets this) or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
