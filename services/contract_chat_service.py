import os
import asyncio
from typing import Dict, Any, Optional
from openai import OpenAI

class ContractChatService:
    """Friendly contract chat assistant using GPT-4o mini for conversational interactions"""
    
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        # Use GPT-4o mini for friendly, conversational contract assistance
        self.chat_model = "gpt-4o-mini"
        
    def _is_contract_related_query(self, query: str) -> bool:
        """Check if a query is related to contracts, legal matters, or document analysis"""
        query_lower = query.lower().strip()
        
        # Contract-related keywords
        contract_keywords = [
            # Direct contract terms
            "contract", "agreement", "nda", "clause", "terms", "conditions", "legal",
            "liability", "indemnity", "termination", "breach", "compliance", "negotiate",
            
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
            "market", "industry", "benchmark", "best practice", "recommendation",
            
            # Service Level Agreements and related terms
            "sla", "service level agreement", "service level", "uptime", "availability",
            "response time", "escalation", "service credit", "maintenance window",
            "performance metric", "service delivery", "downtime", "outage",
            
            # Contract type abbreviations
            "msa", "master service agreement", "sow", "statement of work", "loi", "letter of intent",
            "mou", "memorandum of understanding", "nca", "non-compete agreement", 
            "cda", "confidentiality disclosure agreement", "pii", "personally identifiable information",
            "gdpr", "general data protection regulation", "ccpa", "california consumer privacy act",
            "hipaa", "health insurance portability", "sox", "sarbanes oxley", "pci", "payment card industry",
            "eula", "end user license agreement", "tos", "terms of service", "pp", "privacy policy",
            "dpa", "data processing agreement", "baa", "business associate agreement",
            "rfi", "request for information", "rfp", "request for proposal", "rfq", "request for quote",
            "po", "purchase order", "dnr", "do not resuscitate", "aup", "acceptable use policy"
        ]
        
        # Check if query contains contract keywords
        if any(keyword in query_lower for keyword in contract_keywords):
            return True
        
        return False

    def _get_friendly_purpose_statement(self) -> str:
        """Return a friendly statement about the bot's purpose for irrelevant queries"""
        return """Hi there!

I'm your AI Contract Review Assistant, and I specialize in helping with legal documents and contract-related questions.

📋 What I can help you with:
• Analyze contracts and agreements
• Explain legal terms and clauses
• Identify risks in documents
• Answer contract-related questions
• Provide legal guidance and recommendations

💡 To get started:
• Ask me about contract terms or legal concepts
• Upload a contract document for analysis
• Type 'help' to see all available commands

Is there anything contract or legal-related I can help you with today?

⚖️ *Legal Disclaimer:* This is not legal advice. Consult a lawyer for final review."""

    async def general_chat(
        self, 
        query: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle general contract questions before upload or general legal guidance
        
        Args:
            query: User's question about contracts, legal terms, or general guidance
            jurisdiction: Optional jurisdiction context
            contract_type: Optional contract type context
            
        Returns:
            Conversational response with legal guidance
        """
        try:
            # STRICT FILTER: Check for non-contract topics first
            query_lower = query.lower().strip()
            non_contract_indicators = [
                "weather", "joke", "recipe", "cook", "food", "movie", "music", "game", 
                "sports", "news", "time", "date", "math", "calculate", "translate",
                "directions", "travel", "shopping", "restaurant", "hotel", "flight"
            ]
            
            # Check if it's definitely NOT contract-related
            if any(indicator in query_lower for indicator in non_contract_indicators) and not self._is_contract_related_query(query):
                return {
                    "answer": self._get_friendly_purpose_statement(),
                    "type": "purpose_statement",
                    "model_used": "filtering"
                }
            
            # Also check with contract relevance function
            if not self._is_contract_related_query(query):
                return {
                    "answer": self._get_friendly_purpose_statement(),
                    "type": "purpose_statement",
                    "model_used": "filtering"
                }
            # Build conversational context
            context_info = ""
            if jurisdiction:
                context_info += f" I understand you're dealing with {jurisdiction} jurisdiction."
            if contract_type:
                context_info += f" Since you're working with a {contract_type} contract, I'll focus on relevant aspects."
            
            # Create friendly, conversational system prompt
            system_prompt = f"""You are a friendly, helpful legal contract assistant with extensive experience in contract law and risk assessment. You provide clear, practical advice in everyday language while maintaining professionalism.

Your personality:
- Warm and approachable, like a trusted legal advisor friend
- Explain complex legal concepts in simple terms
- Provide practical, actionable advice
- Show genuine concern for protecting the user's interests
- Use analogies and examples to clarify difficult concepts
- Always encourage users to consult with a lawyer for final decisions
- End responses with complete sentences, never cut off mid-sentence

Guidelines:
- Be conversational and supportive
- Break down complex legal jargon into plain English
- Provide specific, practical tips and recommendations
- Acknowledge when something requires professional legal review
- Use encouraging language while being realistic about risks
- Structure responses with clear sections and complete thoughts
- Always finish with a complete sentence, never end abruptly

Remember: You're here to educate and guide, not to replace professional legal counsel."""

            user_prompt = f"""I have a question about contracts and would appreciate your friendly guidance: {query}

{context_info}

Please provide helpful, conversational advice that's easy to understand. If this relates to specific contract terms or risks, help me understand what to look out for and why it matters."""

            # Call OpenAI API with conversational settings
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=3000,
                temperature=0.4,  # Using requested temperature for focused, structured responses
                presence_penalty=0.0,
                frequency_penalty=0.0
            )
            
            content = response.choices[0].message.content
            if not content:
                content = "I apologize, but I'm having trouble processing your question right now. Could you try rephrasing it?"
            
            # Always add detailed analysis section for contract responses
            formatted_content = f"📝 *No documents uploaded yet*\n\n💡 {content}\n\n"
            formatted_content += "📋 For detailed analysis:\n"
            formatted_content += "• Upload contract documents\n"
            formatted_content += "• Ask specific legal questions"
            formatted_content += "\n\n⚖️ *Legal Disclaimer:* This is not legal advice. Consult a lawyer for final review."
            
            return {
                "answer": formatted_content,
                "type": "general_chat",
                "model_used": self.chat_model
            }
            
        except Exception as e:
            return {
                "answer": "I'm sorry, but I encountered an issue while trying to help you. This might be a temporary problem - please try asking your question again, or feel free to rephrase it.",
                "error": str(e),
                "type": "general_chat"
            }
    
    async def document_specific_chat(
        self, 
        query: str, 
        contract_context: str,
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle questions about a specific uploaded contract with friendly conversation
        
        Args:
            query: User's question about their specific contract
            contract_context: Relevant sections from their contract
            jurisdiction: Optional jurisdiction context
            contract_type: Optional contract type context
            
        Returns:
            Conversational response about their specific contract
        """
        try:
            # Build contextual information
            context_info = ""
            if jurisdiction:
                context_info += f" Given that this is under {jurisdiction} jurisdiction, "
            if contract_type:
                context_info += f" and it's a {contract_type} contract, "
            
            system_prompt = f"""You are a friendly, experienced contract attorney who specializes in explaining contract terms in plain English. You're reviewing a specific contract with a client and helping them understand what they're looking at.

Your approach:
- Speak directly to the user about THEIR contract
- Point out specific clauses and explain what they mean in everyday language
- Highlight potential concerns in a caring, protective way
- Suggest practical next steps or questions they should ask
- Use phrases like "In your contract..." "This clause means..." "I notice that..."
- Be encouraging while being honest about risks
- Make the user feel confident about understanding their contract

Remember: You're helping them understand THEIR specific contract, not giving general advice."""

            user_prompt = f"""I'm looking at my contract and have a specific question: {query}

{context_info}here are the relevant sections from my contract:

{contract_context}

Please help me understand what this means for my specific situation and what I should be aware of."""

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=2500,
                temperature=0.6,  # Balanced for accuracy and conversational tone
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            content = response.choices[0].message.content
            if not content:
                content = "I'm having trouble analyzing that specific part of your contract right now. Could you ask about a different section or rephrase your question?"
            
            return {
                "answer": content,
                "type": "document_specific",
                "model_used": self.chat_model
            }
            
        except Exception as e:
            return {
                "answer": "I'm sorry, I ran into an issue while reviewing your contract. Please try asking about a specific clause or section, and I'll do my best to help you understand it.",
                "error": str(e),
                "type": "document_specific"
            }
    
    async def post_analysis_chat(
        self, 
        query: str, 
        analysis_results: Dict[str, Any],
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle questions about completed analysis results with friendly guidance
        
        Args:
            query: User's question about their analysis results
            analysis_results: The completed contract analysis
            jurisdiction: Optional jurisdiction context
            contract_type: Optional contract type context
            
        Returns:
            Conversational response about their analysis results
        """
        try:
            # Summarize the analysis for context
            risk_score = analysis_results.get('risk_score', 0)
            risky_clauses_count = len(analysis_results.get('risky_clauses', []))
            missing_protections_count = len(analysis_results.get('missing_protections', []))
            
            context_info = ""
            if jurisdiction:
                context_info += f" considering {jurisdiction} jurisdiction"
            if contract_type:
                context_info += f" for this {contract_type} contract"
            
            system_prompt = f"""You are a caring, experienced contract attorney who just completed analyzing a client's contract. You're now discussing the results with them in a supportive, educational way.

Your approach:
- Reference their specific analysis results directly
- Help them prioritize what's most important to address
- Explain the implications of the findings in practical terms
- Suggest concrete next steps they can take
- Be reassuring when appropriate, but honest about genuine concerns
- Help them understand what they should negotiate or ask about
- Make them feel empowered to make informed decisions

The analysis shows:
- Overall risk score: {risk_score}/10
- {risky_clauses_count} potential risk areas identified
- {missing_protections_count} missing protections noted

Remember: They're looking to you for guidance on what to do with this information."""

            user_prompt = f"""Based on my contract analysis results, I have a question: {query}

{context_info}

Here's a summary of my analysis:
- Risk Score: {risk_score}/10
- Risk Areas Found: {risky_clauses_count}
- Missing Protections: {missing_protections_count}

Analysis Summary: {analysis_results.get('summary', 'Analysis completed')}

Please help me understand what this means and what I should do next."""

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=2500,
                temperature=0.5,  # Lower temperature for more focused advice
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            content = response.choices[0].message.content
            if not content:
                content = "I'm having some trouble right now, but I'd love to help you understand your analysis results. Could you ask about a specific finding or what you should prioritize first?"
            
            return {
                "answer": content,
                "type": "post_analysis",
                "model_used": self.chat_model,
                "analysis_context": True
            }
            
        except Exception as e:
            return {
                "answer": "I apologize, but I'm having difficulty discussing your analysis results right now. Feel free to ask about specific findings or what steps you should take next, and I'll do my best to guide you.",
                "error": str(e),
                "type": "post_analysis"
            }