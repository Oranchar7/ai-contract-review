import os
import json
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import tiktoken
import faiss
from openai import OpenAI
from models.contract_analysis import ContractAnalysisResponse, RiskyClause, MissingProtection

class RAGService:
    """RAG service for contract analysis with FAISS vector storage"""
    
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        self.embedding_model = "text-embedding-3-small"
        # Use GPT-4o mini for friendly, conversational contract chat
        # Keep GPT-5 for detailed analysis, but use the more conversational model for chat
        self.chat_model = "gpt-4o-mini"
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = 1000  # characters per chunk
        self.overlap = 100     # character overlap between chunks
        
        # FAISS index and document storage
        self.index = None
        self.document_chunks = []
        self.document_metadata = []
        
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    def _chunk_document(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Chunk document into smaller sections with metadata"""
        chunks = []
        text_length = len(text)
        
        for i in range(0, text_length, self.chunk_size - self.overlap):
            chunk_end = min(i + self.chunk_size, text_length)
            chunk_text = text[i:chunk_end]
            
            chunks.append({
                "text": chunk_text,
                "filename": filename,
                "chunk_index": len(chunks),
                "char_count": len(chunk_text),
                "start_char": i,
                "end_char": chunk_end,
                "token_count": self._count_tokens(chunk_text)
            })
        
        return chunks
    
    async def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        try:
            response = await asyncio.to_thread(
                self.openai_client.embeddings.create,
                model=self.embedding_model,
                input=texts
            )
            
            embeddings = np.array([data.embedding for data in response.data])
            return embeddings.astype('float32')
            
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    async def upload_contract(
        self, 
        contract_text: str, 
        filename: str,
        email: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chunk document, generate embeddings, and store in FAISS index
        
        Args:
            contract_text: The extracted text from the contract
            filename: Original filename
            
        Returns:
            Dict with upload status and metadata
        """
        try:
            # Chunk the document
            chunks = self._chunk_document(contract_text, filename)
            chunk_texts = [chunk["text"] for chunk in chunks]
            
            # Generate embeddings
            embeddings = await self._get_embeddings(chunk_texts)
            
            # Initialize FAISS index if not exists
            if self.index is None:
                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
                
            # Normalize embeddings for cosine similarity
            # Ensure embeddings are contiguous for FAISS
            embeddings_normalized = embeddings.copy().astype(np.float32)
            if embeddings_normalized.ndim == 1:
                embeddings_normalized = embeddings_normalized.reshape(1, -1)
            faiss.normalize_L2(embeddings_normalized)
            
            # Store chunks and metadata
            start_idx = len(self.document_chunks)
            self.document_chunks.extend(chunks)
            self.document_metadata.extend([{
                "filename": filename,
                "chunk_index": i,
                "global_index": start_idx + i,
                "email": email,
                "jurisdiction": jurisdiction,
                "contract_type": contract_type,
                "upload_time": asyncio.get_event_loop().time()
            } for i in range(len(chunks))])
            
            # Add to FAISS index
            if embeddings_normalized.shape[0] > 0:
                self.index.add(embeddings_normalized)
            
            return {
                "status": "success",
                "filename": filename,
                "chunks_created": len(chunks),
                "total_tokens": sum(chunk["token_count"] for chunk in chunks),
                "index_size": self.index.ntotal
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to upload contract: {str(e)}"
            }
    
    async def _retrieve_relevant_chunks(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for a query"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self._get_embeddings([query])
            # Ensure query embedding is contiguous for FAISS
            query_embedding_normalized = query_embedding.copy().astype(np.float32)
            if query_embedding_normalized.ndim == 1:
                query_embedding_normalized = query_embedding_normalized.reshape(1, -1)
            faiss.normalize_L2(query_embedding_normalized)
            
            # Search for similar chunks
            k = min(k, self.index.ntotal)  # Ensure k doesn't exceed available vectors
            if k > 0:
                scores, indices = self.index.search(query_embedding_normalized, k)
            else:
                scores, indices = np.array([[]]), np.array([[]])
            
            # Return relevant chunks with scores
            relevant_chunks = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.document_chunks):
                    chunk = self.document_chunks[idx].copy()
                    chunk["relevance_score"] = float(score)
                    relevant_chunks.append(chunk)
            
            return relevant_chunks
            
        except Exception as e:
            raise Exception(f"Failed to retrieve chunks: {str(e)}")
    
    async def ask_contract(
        self, 
        query: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer questions about uploaded contracts using RAG
        
        Args:
            query: User question about the contract
            jurisdiction: Optional jurisdiction context
            contract_type: Optional contract type context
            
        Returns:
            Contract analysis in the expected JSON format
        """
        try:
            # Retrieve relevant chunks
            relevant_chunks = await self._retrieve_relevant_chunks(query, k=5)
            
            if not relevant_chunks:
                return {
                    "error": "No contract documents uploaded or no relevant information found",
                    "risky_clauses": [],
                    "missing_protections": [],
                    "overall_risk_score": 0,
                    "summary": "No contract information available for analysis",
                    "notes": ["Please upload a contract document first"]
                }
            
            # Build context from retrieved chunks
            context = "\n\n".join([
                f"[Document Section {i+1}]:\n{chunk['text']}"
                for i, chunk in enumerate(relevant_chunks)
            ])
            
            # Build analysis prompt
            prompt = self._build_rag_prompt(query, context, jurisdiction, contract_type)
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly, experienced contract attorney who helps people understand their contracts in plain English. You're warm and approachable while being thorough and professional. Provide structured responses in JSON format, but write in a conversational, helpful tone."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=4000,
                temperature=0.3
            )
            
            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise Exception("AI response was empty")
            
            analysis_data = json.loads(content)
            
            # Convert to expected format
            return self._format_analysis_response(analysis_data, relevant_chunks)
            
        except json.JSONDecodeError as e:
            return {
                "error": "Failed to parse AI response",
                "details": str(e),
                "risky_clauses": [],
                "missing_protections": [],
                "overall_risk_score": 0,
                "summary": "Analysis parsing failed",
                "notes": []
            }
        except Exception as e:
            return {
                "error": "Analysis failed",
                "details": str(e),
                "risky_clauses": [],
                "missing_protections": [],
                "overall_risk_score": 0,
                "summary": "Contract analysis could not be completed",
                "notes": []
            }
    
    def _build_rag_prompt(
        self, 
        query: str, 
        context: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> str:
        """Build RAG prompt with retrieved context"""
        
        context_info = ""
        if jurisdiction:
            context_info += f"\nJURISDICTION: {jurisdiction}"
        if contract_type:
            context_info += f"\nCONTRACT TYPE: {contract_type}"
        
        return f"""
        Based on the following contract sections and the user's question, provide a comprehensive legal analysis.{context_info}
        
        USER QUESTION: {query}
        
        RELEVANT CONTRACT SECTIONS:
        {context}
        
        Please provide your analysis in the following JSON format:
        {{
            "risky_clauses": [
                {{
                    "clause": "<specific clause text or reference>",
                    "why": "<explanation of why this clause is risky>",
                    "severity": "<low|medium|high>"
                }}
            ],
            "missing_protections": [
                {{
                    "protection": "<type of protection that's missing>",
                    "why": "<explanation of why this protection is important>",
                    "suggested_language": "<suggested clause language>"
                }}
            ],
            "overall_risk_score": <integer from 1-10>,
            "summary": "<comprehensive summary addressing the user's question>",
            "notes": [
                "<additional important observations or recommendations>"
            ]
        }}
        
        Focus on:
        1. Directly answering the user's question
        2. Identifying risks in the provided contract sections
        3. Suggesting missing protections relevant to the question
        4. Providing actionable recommendations
        
        {f"Consider {jurisdiction} jurisdiction requirements." if jurisdiction else ""}
        {f"Apply {contract_type} contract-specific analysis." if contract_type else ""}
        """
    
    def _format_analysis_response(self, analysis_data: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format analysis response to match expected schema"""
        return {
            "risky_clauses": analysis_data.get("risky_clauses", []),
            "missing_protections": analysis_data.get("missing_protections", []),
            "overall_risk_score": min(10, max(0, analysis_data.get("overall_risk_score", 0))),
            "summary": analysis_data.get("summary", ""),
            "notes": analysis_data.get("notes", []),
            "retrieved_chunks": len(chunks),
            "source_documents": list(set(chunk["filename"] for chunk in chunks))
        }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current FAISS index"""
        if self.index is None:
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "index_size": 0
            }
        
        return {
            "total_chunks": len(self.document_chunks),
            "total_documents": len(set(chunk["filename"] for chunk in self.document_chunks)),
            "index_size": self.index.ntotal,
            "documents": list(set(chunk["filename"] for chunk in self.document_chunks))
        }