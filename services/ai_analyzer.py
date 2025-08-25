import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from openai import OpenAI
from models.contract_analysis import ContractAnalysisResponse, RiskyClause, MissingProtection

class AIAnalyzer:
    """Service for AI-powered contract analysis using OpenAI"""
    
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-5"
    
    async def analyze_contract(
        self, 
        contract_text: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> ContractAnalysisResponse:
        """
        Analyze contract text using AI and return structured results
        
        Args:
            contract_text: The extracted text from the contract
            jurisdiction: Optional jurisdiction (e.g., "US-NY", "CA-ON")
            contract_type: Optional contract type (e.g., "NDA", "MSA", "SaaS TOS")
            
        Returns:
            ContractAnalysisResponse: Structured analysis results
        """
        try:
            # Prepare the analysis prompt
            analysis_prompt = self._build_analysis_prompt(contract_text, jurisdiction, contract_type)
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert contract attorney with 20+ years of experience in contract law, risk assessment, and legal document analysis. Provide thorough, accurate, and actionable contract analysis."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=4000,
                temperature=0.3
            )
            
            # Parse the response
            content = response.choices[0].message.content
            if not content:
                raise Exception("AI response was empty")
            analysis_data = json.loads(content)
            
            # Convert to structured response
            return self._parse_analysis_response(analysis_data)
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response: {str(e)}")
        except Exception as e:
            raise Exception(f"AI analysis failed: {str(e)}")
    
    def _build_analysis_prompt(
        self, 
        contract_text: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> str:
        """Build the comprehensive analysis prompt"""
        # Build context information for jurisdiction and contract type
        context_info = ""
        if jurisdiction:
            context_info += f"\nJURISDICTION: {jurisdiction}"
        if contract_type:
            context_info += f"\nCONTRACT TYPE: {contract_type}"
        
        return f"""
        Please analyze the following contract and provide a comprehensive risk assessment.{context_info}
        
        CONTRACT TEXT:
        {contract_text[:15000]}  # Limit text to avoid token limits
        
        Please provide your analysis in the following JSON format:
        {{
            "risk_score": <integer from 1-10, where 10 is highest risk>,
            "summary": "<brief 2-3 sentence summary of overall contract assessment>",
            "risky_clauses": [
                {{
                    "clause_type": "<type of risky clause>",
                    "description": "<description of the specific clause and why it's risky>",
                    "recommendation": "<specific recommendation to address this risk>",
                    "risk_level": "<high|medium|low>"
                }}
            ],
            "missing_protections": [
                {{
                    "protection_type": "<type of missing protection>",
                    "description": "<description of what protection is missing>",
                    "importance": "<why this protection is important>",
                    "suggested_clause": "<suggested clause language to add>"
                }}
            ],
            "detailed_analysis": "<comprehensive analysis covering key terms, obligations, termination clauses, liability, intellectual property, confidentiality, dispute resolution, and any other significant legal considerations>"
        }}
        
        Focus on identifying:
        1. Unfair or heavily one-sided terms
        2. Unclear or ambiguous language
        3. Missing standard protections
        4. Excessive liability or penalty clauses
        5. Problematic termination or renewal terms
        6. Intellectual property concerns
        7. Confidentiality and non-disclosure issues
        8. Payment and delivery terms
        9. Dispute resolution mechanisms
        10. Compliance and regulatory considerations
        
        {f"Consider the specific jurisdiction ({jurisdiction}) laws and requirements." if jurisdiction else ""}
        {f"Focus on issues specific to {contract_type} contracts." if contract_type else ""}
        
        Provide specific, actionable recommendations for each identified issue.
        """
    
    def _parse_analysis_response(self, analysis_data: Dict[str, Any]) -> ContractAnalysisResponse:
        """Parse AI response into structured ContractAnalysisResponse"""
        
        # Parse risky clauses
        risky_clauses = []
        for clause_data in analysis_data.get('risky_clauses', []):
            risky_clauses.append(RiskyClause(
                clause_type=clause_data.get('clause_type', 'Unknown'),
                description=clause_data.get('description', ''),
                recommendation=clause_data.get('recommendation', ''),
                risk_level=clause_data.get('risk_level', 'medium')
            ))
        
        # Parse missing protections
        missing_protections = []
        for protection_data in analysis_data.get('missing_protections', []):
            missing_protections.append(MissingProtection(
                protection_type=protection_data.get('protection_type', 'Unknown'),
                description=protection_data.get('description', ''),
                importance=protection_data.get('importance', ''),
                suggested_clause=protection_data.get('suggested_clause', '')
            ))
        
        return ContractAnalysisResponse(
            risk_score=min(10, max(1, analysis_data.get('risk_score', 5))),
            summary=analysis_data.get('summary', 'Analysis completed'),
            risky_clauses=risky_clauses,
            missing_protections=missing_protections,
            detailed_analysis=analysis_data.get('detailed_analysis', 'Detailed analysis not available'),
            document_id=""  # Will be set by the main handler
        )
    
    async def generate_recommendations(self, analysis: ContractAnalysisResponse) -> Dict[str, str]:
        """
        Generate additional recommendations based on the analysis
        
        Args:
            analysis: The contract analysis results
            
        Returns:
            Dict with additional recommendations
        """
        try:
            prompt = f"""
            Based on this contract analysis, provide specific next steps and recommendations:
            
            Risk Score: {analysis.risk_score}/10
            Summary: {analysis.summary}
            Number of Risky Clauses: {len(analysis.risky_clauses)}
            Number of Missing Protections: {len(analysis.missing_protections)}
            
            Please provide recommendations in JSON format:
            {{
                "immediate_actions": "<most urgent actions to take>",
                "negotiation_priorities": "<key points to focus on during negotiations>",
                "legal_review_needed": "<whether professional legal review is recommended>",
                "contract_approval": "<recommendation on whether to sign as-is, negotiate, or reject>"
            }}
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior contract attorney providing strategic advice."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000,
                temperature=0.2
            )
            
            content = response.choices[0].message.content
            if not content:
                return {"error": "AI response was empty"}
            return json.loads(content)
            
        except Exception as e:
            return {
                "error": f"Failed to generate additional recommendations: {str(e)}"
            }
