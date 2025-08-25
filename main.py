import os
import tempfile
from datetime import datetime
from typing import Optional
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
from services.rag_service import RAGService
from services.contract_chat_service import ContractChatService
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
rag_service = RAGService()
chat_service = ContractChatService()

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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
