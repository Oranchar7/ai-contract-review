import os
import tempfile
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn

from services.file_processor import FileProcessor
from services.ai_analyzer import AIAnalyzer
from services.firebase_client import FirebaseClient
from services.notification_service import NotificationService
from services.rag_service import RAGService
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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page with Firebase configuration"""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "firebase_api_key": os.environ.get("FIREBASE_API_KEY", ""),
            "firebase_project_id": os.environ.get("FIREBASE_PROJECT_ID", ""),
            "firebase_app_id": os.environ.get("FIREBASE_APP_ID", ""),
        }
    )

@app.get("/rag", response_class=HTMLResponse)
async def rag_interface(request: Request):
    """Serve the RAG chat interface"""
    return templates.TemplateResponse("rag.html", {"request": request})

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None)
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
            analysis_result = await ai_analyzer.analyze_contract(
                extracted_text, 
                jurisdiction=jurisdiction,
                contract_type=contract_type
            )
            
            # Store analysis in Firebase
            document_id = await firebase_client.store_analysis(
                analysis_result.dict(),
                filename,
                email
            )
            
            # Add document ID to response
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
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None)
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
            
            # Upload to RAG service
            upload_result = await rag_service.upload_contract(extracted_text, filename)
            
            # Add optional context info
            if jurisdiction or contract_type:
                upload_result.update({
                    "jurisdiction": jurisdiction,
                    "contract_type": contract_type
                })
            
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

@app.post("/ask_contract")
async def ask_contract(
    query: str = Form(...),
    jurisdiction: Optional[str] = Form(None),
    contract_type: Optional[str] = Form(None)
):
    """
    Ask questions about uploaded contracts using RAG
    
    Args:
        query: Question about the contract
        jurisdiction: Optional jurisdiction context
        contract_type: Optional contract type context
    
    Returns:
        Contract analysis results in JSON format
    """
    try:
        result = await rag_service.ask_contract(
            query=query,
            jurisdiction=jurisdiction,
            contract_type=contract_type
        )
        
        # Add a simple answer field for the chat interface
        if "error" not in result:
            # Create a conversational answer from the analysis
            answer_parts = []
            
            if result.get("summary"):
                answer_parts.append(result["summary"])
            
            if result.get("risky_clauses"):
                risk_count = len(result["risky_clauses"])
                if risk_count > 0:
                    answer_parts.append(f"I found {risk_count} potentially risky clause(s).")
            
            if result.get("missing_protections"):
                missing_count = len(result["missing_protections"])
                if missing_count > 0:
                    answer_parts.append(f"There are {missing_count} missing protection(s) to consider.")
            
            if result.get("overall_risk_score"):
                score = result["overall_risk_score"]
                answer_parts.append(f"Overall risk score: {score}/10.")
            
            result["answer"] = " ".join(answer_parts) if answer_parts else "Analysis completed."
        
        return result
        
    except Exception as e:
        return {
            "error": "Analysis failed",
            "details": str(e),
            "risky_clauses": [],
            "missing_protections": [],
            "overall_risk_score": 0,
            "summary": "Could not analyze contract",
            "notes": []
        }

@app.get("/rag_status")
async def get_rag_status():
    """Get current RAG index statistics"""
    try:
        stats = rag_service.get_index_stats()
        return {
            "status": "healthy",
            "rag_stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ai-contract-review"}

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
