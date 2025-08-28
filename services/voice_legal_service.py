"""
Voice-to-Text Legal Jargon Explainer Service
Provides AI-powered explanations for legal terms and jargon in plain language
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from openai import OpenAI

class VoiceLegalService:
    """Service for explaining legal jargon in simple, everyday language"""
    
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        # Use GPT-4o mini for conversational explanations
        self.chat_model = "gpt-4o-mini"
        
    def _is_legal_term_query(self, text: str) -> bool:
        """Check if text contains legal terms or contract-related content"""
        legal_indicators = [
            # Direct legal terms
            "what is", "what does", "explain", "define", "meaning",
            "contract", "agreement", "clause", "terms", "legal", "law",
            "liability", "indemnity", "breach", "compliance", "jurisdiction",
            
            # Legal jargon commonly asked about
            "force majeure", "liquidated damages", "material adverse change",
            "representations and warranties", "due diligence", "escrow",
            "arbitration", "mediation", "injunctive relief", "specific performance",
            "boilerplate", "whereas", "hereinafter", "notwithstanding",
            "covenant", "consideration", "novation", "assignment", "sublicense",
            
            # Contract types
            "nda", "msa", "sla", "employment", "consulting", "partnership",
            "license", "lease", "purchase", "merger", "acquisition",
            
            # Business legal terms
            "incorporation", "llc", "fiduciary", "shareholder", "board of directors",
            "intellectual property", "trademark", "copyright", "patent",
            "non-compete", "non-disclosure", "confidentiality",
            
            # Common legal phrases people ask about
            "in perpetuity", "time is of the essence", "as is", "without prejudice",
            "good faith", "best efforts", "commercially reasonable", "industry standard"
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in legal_indicators)
    
    async def explain_legal_jargon(
        self, 
        text: str, 
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert legal jargon into plain English explanations
        
        Args:
            text: The legal term, phrase, or question to explain
            context: Optional context (contract type, jurisdiction, etc.)
            
        Returns:
            Dictionary with explanation and related information
        """
        try:
            # Check if this is actually a legal term query
            if not self._is_legal_term_query(text):
                return {
                    "explanation": "I specialize in explaining legal terms and contract language. Could you ask about a specific legal term or contract clause you'd like me to explain?",
                    "type": "redirect",
                    "suggestions": [
                        "What does 'force majeure' mean?",
                        "Explain 'liquidated damages'",
                        "What is a material adverse change clause?",
                        "Define indemnification in contracts"
                    ]
                }
            
            # Build context for the explanation
            context_info = ""
            if context:
                context_info = f" (Context: {context})"
            
            # Create system prompt for clear legal explanations
            system_prompt = f"""You're Lexi, a friendly legal assistant who explains legal jargon in simple, everyday language.

When someone asks about legal terms:
- Explain in plain English that anyone can understand
- Use analogies and examples when helpful
- Break down complex concepts into simple parts
- Mention why this term matters in contracts
- Keep explanations conversational and friendly
- If it's a complex topic, offer to explain specific parts in more detail

Be helpful and encouraging - legal language doesn't have to be intimidating!{context_info}"""

            # Get AI explanation
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.4,
                max_tokens=800
            )
            
            explanation = response.choices[0].message.content
            
            # Extract key legal terms mentioned for related suggestions
            related_terms = self._extract_related_terms(explanation)
            
            return {
                "explanation": explanation,
                "type": "legal_explanation",
                "related_terms": related_terms,
                "input_text": text,
                "model_used": self.chat_model
            }
            
        except Exception as e:
            return {
                "explanation": f"Sorry, I had trouble explaining that legal term. Could you try rephrasing your question? Error: {str(e)}",
                "type": "error",
                "error": str(e)
            }
    
    def _extract_related_terms(self, explanation: str) -> List[str]:
        """Extract related legal terms from the explanation for suggestions"""
        common_legal_terms = [
            "force majeure", "liquidated damages", "material adverse change",
            "indemnification", "arbitration", "mediation", "breach of contract",
            "due diligence", "representations and warranties", "covenant",
            "consideration", "assignment", "novation", "escrow", "jurisdiction",
            "governing law", "termination", "confidentiality", "non-compete",
            "intellectual property", "liability", "damages", "injunctive relief"
        ]
        
        explanation_lower = explanation.lower()
        found_terms = [term for term in common_legal_terms if term in explanation_lower]
        
        # Return up to 3 related terms, excluding the original if it was a direct match
        return found_terms[:3]
    
    async def get_voice_friendly_explanation(
        self, 
        text: str, 
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get explanation optimized for voice/audio consumption
        Shorter, more conversational format suitable for text-to-speech
        """
        result = await self.explain_legal_jargon(text, context)
        
        if result["type"] == "legal_explanation":
            # Create a more concise version for voice
            system_prompt = """Summarize this legal explanation in 2-3 sentences maximum, perfect for listening. 
            Keep it conversational and easy to follow when heard aloud. Focus on the key point."""
            
            try:
                voice_response = self.openai_client.chat.completions.create(
                    model=self.chat_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Make this voice-friendly: {result['explanation']}"}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                
                result["voice_explanation"] = voice_response.choices[0].message.content
                result["is_voice_optimized"] = True
                
            except Exception as e:
                # Fall back to original explanation if voice optimization fails
                result["voice_explanation"] = result["explanation"]
                result["is_voice_optimized"] = False
        
        return result