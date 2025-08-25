from typing import List, Optional
from pydantic import BaseModel, Field

class RiskyClause(BaseModel):
    """Model for representing a risky clause in a contract"""
    clause_type: str = Field(..., description="Type of risky clause (e.g., 'Termination', 'Liability')")
    description: str = Field(..., description="Description of why this clause is risky")
    recommendation: str = Field(..., description="Recommendation for addressing this risk")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, or high")

class MissingProtection(BaseModel):
    """Model for representing a missing protection in a contract"""
    protection_type: str = Field(..., description="Type of missing protection")
    description: str = Field(..., description="Description of what protection is missing")
    importance: str = Field(..., description="Why this protection is important")
    suggested_clause: str = Field(default="", description="Suggested clause language to add")

class ContractAnalysisResponse(BaseModel):
    """Complete contract analysis response model"""
    risk_score: int = Field(..., ge=1, le=10, description="Overall risk score from 1-10")
    summary: str = Field(..., description="Brief summary of the contract analysis")
    risky_clauses: List[RiskyClause] = Field(default=[], description="List of identified risky clauses")
    missing_protections: List[MissingProtection] = Field(default=[], description="List of missing protections")
    detailed_analysis: str = Field(..., description="Comprehensive detailed analysis")
    document_id: str = Field(default="", description="Firebase document ID for this analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "risk_score": 7,
                "summary": "This contract contains several high-risk clauses that heavily favor the other party, with limited protections for your interests.",
                "risky_clauses": [
                    {
                        "clause_type": "Termination",
                        "description": "The contract allows the other party to terminate at any time without cause or notice.",
                        "recommendation": "Negotiate for mutual termination rights with reasonable notice period.",
                        "risk_level": "high"
                    }
                ],
                "missing_protections": [
                    {
                        "protection_type": "Limitation of Liability",
                        "description": "No limits on liability for damages or losses.",
                        "importance": "Without liability limits, you could be responsible for unlimited damages.",
                        "suggested_clause": "Each party's liability shall be limited to the total amount paid under this agreement."
                    }
                ],
                "detailed_analysis": "This contract presents significant risks due to unbalanced termination clauses, unlimited liability exposure, and lack of standard business protections...",
                "document_id": "abc123xyz"
            }
        }

class AnalysisRequest(BaseModel):
    """Model for contract analysis request"""
    filename: str = Field(..., description="Name of the uploaded file")
    email: Optional[str] = Field(None, description="Optional email for notifications")
    
class AnalysisStatus(BaseModel):
    """Model for analysis status tracking"""
    document_id: str
    status: str = Field(..., description="Status: pending, processing, completed, error")
    created_at: str
    updated_at: str
    filename: str
    email: Optional[str] = None
    
class UserAnalysisHistory(BaseModel):
    """Model for user's analysis history"""
    analyses: List[AnalysisStatus]
    total_count: int
    user_email: str

class ErrorResponse(BaseModel):
    """Model for error responses"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
    timestamp: str = Field(..., description="Error timestamp")
