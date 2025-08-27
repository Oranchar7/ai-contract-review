import os
import json
import asyncio
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import tiktoken
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

class PineconeRAGService:
    """Persistent RAG service using Pinecone vector database"""
    
    def __init__(self):
        self.openai_client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4o-mini"
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = 800  # tokens per chunk as specified
        self.overlap = 100     # token overlap as specified
        
        # Pinecone setup
        self.pinecone_client = None
        self.index = None
        self.index_name = "contracts-rag"  # As specified
        self.dimension = 1536  # text-embedding-3-small dimension
        
        # Initialize connection
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone connection and index"""
        try:
            api_key = os.environ.get("PINECONE_API_KEY")
            if not api_key:
                print("Warning: PINECONE_API_KEY not found. Vector storage will be unavailable.")
                return
            
            # Initialize Pinecone client
            self.pinecone_client = Pinecone(api_key=api_key)
            
            # Check if index exists, create only if it doesn't exist
            existing_indexes = [idx.name for idx in self.pinecone_client.list_indexes()]
            
            if self.index_name not in existing_indexes:
                print(f"Creating new Pinecone index: {self.index_name}")
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                # Wait for index to be ready
                import time
                print("Waiting for index to be ready...")
                time.sleep(15)  # Longer wait for serverless
                print(f"New Pinecone index created: {self.index_name}")
            else:
                print(f"Reusing existing Pinecone index: {self.index_name}")
            
            # Connect to index (existing or newly created)
            self.index = self.pinecone_client.Index(self.index_name)
            
            # Verify connection with index stats
            stats = self.index.describe_index_stats()
            print(f"Connected to Pinecone index '{self.index_name}' with {stats.total_vector_count} vectors")
            
        except Exception as e:
            print(f"Failed to initialize Pinecone: {str(e)}")
            self.pinecone_client = None
            self.index = None
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    def _generate_chunk_hash(self, text: str, filename: str) -> str:
        """Generate unique hash for chunk deduplication"""
        content = f"{filename}:{text.strip()}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def _generate_doc_id(self, filename: str, upload_time: str) -> str:
        """Generate unique document ID"""
        content = f"{filename}:{upload_time}".encode('utf-8')
        return f"doc_{hashlib.sha256(content).hexdigest()[:12]}"
    
    def _chunk_document(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Chunk document by tokens with metadata"""
        chunks = []
        tokens = self.tokenizer.encode(text)
        text_decoded = self.tokenizer.decode(tokens)
        
        # Split by tokens, not characters
        for i in range(0, len(tokens), self.chunk_size - self.overlap):
            chunk_end = min(i + self.chunk_size, len(tokens))
            chunk_tokens = tokens[i:chunk_end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk_hash = self._generate_chunk_hash(chunk_text, filename)
            
            chunks.append({
                "text": chunk_text,
                "filename": filename,
                "chunk_index": len(chunks),
                "token_count": len(chunk_tokens),
                "start_token": i,
                "end_token": chunk_end,
                "chunk_hash": chunk_hash
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
    
    async def _similarity_deduplication_check(self, new_embeddings: np.ndarray, threshold: float = 0.97) -> List[int]:
        """Advanced similarity-based deduplication using cosine similarity > 0.97"""
        if not self.index:
            return []
        
        try:
            duplicate_indices = []
            
            # Check each new embedding against existing ones
            for i, embedding in enumerate(new_embeddings):
                # Query Pinecone for similar vectors
                search_results = self.index.query(
                    vector=embedding.tolist(),
                    top_k=3,  # Check top 3 most similar
                    include_metadata=False,
                    include_values=False
                )
                
                # Check if any result exceeds similarity threshold
                matches = getattr(search_results, 'matches', [])
                for match in matches:
                    if match.score > threshold:
                        print(f"Duplicate detected: similarity {match.score:.4f} > {threshold}")
                        duplicate_indices.append(i)
                        break
            
            return duplicate_indices
            
        except Exception as e:
            print(f"Error in similarity deduplication: {str(e)}")
            return []
    
    async def _check_existing_chunks(self, chunk_hashes: List[str]) -> List[str]:
        """Check which chunks already exist in Pinecone by hash"""
        if not self.index:
            return []
        
        try:
            existing_hashes = []
            for chunk_hash in chunk_hashes:
                try:
                    result = self.index.fetch(ids=[chunk_hash])
                    if result.vectors and chunk_hash in result.vectors:
                        existing_hashes.append(chunk_hash)
                except:
                    continue
            
            return existing_hashes
            
        except Exception as e:
            print(f"Error checking existing chunks: {str(e)}")
            return []
    
    async def upload_contract(
        self, 
        contract_text: str, 
        filename: str,
        email: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chunk document, generate embeddings, and store in Pinecone with deduplication
        """
        try:
            if not self.index:
                return {
                    "status": "error",
                    "error": "The knowledge database is temporarily unavailable. Please try again shortly."
                }
            
            # Chunk the document
            chunks = self._chunk_document(contract_text, filename)
            chunk_hashes = [chunk["chunk_hash"] for chunk in chunks]
            
            # Check for existing chunks (deduplication)
            existing_hashes = await self._check_existing_chunks(chunk_hashes)
            new_chunks = [chunk for chunk in chunks if chunk["chunk_hash"] not in existing_hashes]
            
            if not new_chunks:
                return {
                    "status": "success",
                    "filename": filename,
                    "chunks_created": 0,
                    "chunks_skipped": len(chunks),
                    "message": "Document already exists - no new chunks added",
                    "total_tokens": sum(chunk["token_count"] for chunk in chunks)
                }
            
            # Generate embeddings for new chunks only
            chunk_texts = [chunk["text"] for chunk in new_chunks]
            embeddings = await self._get_embeddings(chunk_texts)
            
            # Advanced similarity-based deduplication
            duplicate_indices = await self._similarity_deduplication_check(embeddings, threshold=0.97)
            final_chunks = [chunk for i, chunk in enumerate(new_chunks) if i not in duplicate_indices]
            final_embeddings = np.array([emb for i, emb in enumerate(embeddings) if i not in duplicate_indices])
            
            if len(final_chunks) == 0:
                return {
                    "status": "success",
                    "filename": filename,
                    "chunks_created": 0,
                    "chunks_skipped": len(chunks),
                    "message": "All chunks were duplicates - no new vectors added",
                    "total_tokens": sum(chunk["token_count"] for chunk in chunks)
                }
            
            # Prepare vectors for Pinecone with enhanced metadata
            upload_time = datetime.now().isoformat()
            doc_id = self._generate_doc_id(filename, upload_time)
            vectors = []
            
            for i, (chunk, embedding) in enumerate(zip(final_chunks, final_embeddings)):
                vector_id = chunk["chunk_hash"]
                chunk_id = f"chunk_{i+1:03d}"
                
                # Enhanced metadata structure as specified
                metadata = {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "filename": filename,
                    "text": chunk["text"][:1000],  # Pinecone metadata limit
                    "chunk_index": chunk["chunk_index"],
                    "token_count": chunk["token_count"],
                    "jurisdiction": jurisdiction or "unspecified",
                    "contract_type": contract_type or "unspecified",
                    "uploaded_by": email or "anonymous",
                    "source_url": "",  # Can be populated if available
                    "upload_date": upload_time
                }
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding.tolist(),
                    "metadata": metadata
                })
            
            # Batch upload to Pinecone
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            return {
                "status": "success",
                "filename": filename,
                "doc_id": doc_id,
                "chunks_created": len(final_chunks),
                "chunks_skipped_hash": len(existing_hashes),
                "chunks_skipped_similarity": len(duplicate_indices),
                "total_tokens": sum(chunk["token_count"] for chunk in final_chunks),
                "index_name": self.index_name,
                "embedding_model": self.embedding_model
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to upload contract: {str(e)}"
            }
    
    async def _retrieve_relevant_chunks(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for a query from Pinecone"""
        if not self.index:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self._get_embeddings([query])
            
            # Search Pinecone for similar chunks
            search_results = self.index.query(
                vector=query_embedding[0].tolist(),
                top_k=k,
                include_metadata=True,
                include_values=False
            )
            
            # Format results with enhanced metadata
            relevant_chunks = []
            matches = getattr(search_results, 'matches', [])
            for match in matches:
                chunk_data = {
                    "text": match.metadata.get("text", ""),
                    "doc_id": match.metadata.get("doc_id", ""),
                    "chunk_id": match.metadata.get("chunk_id", ""),
                    "filename": match.metadata.get("filename", ""),
                    "chunk_index": match.metadata.get("chunk_index", 0),
                    "token_count": match.metadata.get("token_count", 0),
                    "relevance_score": float(match.score),
                    "upload_date": match.metadata.get("upload_date", ""),
                    "uploaded_by": match.metadata.get("uploaded_by", ""),
                    "jurisdiction": match.metadata.get("jurisdiction", ""),
                    "contract_type": match.metadata.get("contract_type", "")
                }
                relevant_chunks.append(chunk_data)
            
            return relevant_chunks
            
        except Exception as e:
            print(f"Failed to retrieve chunks from Pinecone: {str(e)}")
            return []
    
    async def ask_contract(
        self, 
        query: str, 
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer questions about uploaded contracts using Pinecone RAG
        """
        try:
            # SAFETY FILTER: Block non-contract queries that should not reach RAG
            query_lower = query.lower().strip()
            non_contract_indicators = [
                "weather", "joke", "recipe", "cook", "food", "movie", "music", "game", 
                "sports", "news", "time", "date", "math", "calculate", "translate",
                "directions", "travel", "shopping", "restaurant", "hotel", "flight"
            ]
            
            # Only block if definitely non-contract (no contract keywords present)
            contract_keywords = ["contract", "agreement", "legal", "sla", "msa", "nda", "clause", "terms", "service level"]
            is_contract_query = any(keyword in query_lower for keyword in contract_keywords)
            
            if any(indicator in query_lower for indicator in non_contract_indicators) and not is_contract_query:
                return {
                    "error": "FILTERED_NON_CONTRACT_QUERY",
                    "query_type": "non_contract", 
                    "purpose_statement": "Hi there! I'm your AI Contract Review Assistant, and I specialize in helping with legal documents and contract-related questions. Is there anything contract or legal-related I can help you with today?",
                    "risky_clauses": [],
                    "missing_protections": [],
                    "overall_risk_score": 0,
                    "summary": "Query filtered as non-contract related",
                    "notes": ["This query appears to be outside my contract analysis expertise"]
                }
            if not self.index:
                return {
                    "error": "The knowledge database is temporarily unavailable. Please try again shortly.",
                    "risky_clauses": [],
                    "missing_protections": [],
                    "overall_risk_score": 0,
                    "summary": "Vector database connection unavailable",
                    "notes": ["Please try again in a few moments"]
                }
            
            # Retrieve relevant chunks from Pinecone
            relevant_chunks = await self._retrieve_relevant_chunks(query, k=7)
            
            # Check if relevant chunks found - implement explicit messaging requirement
            if not relevant_chunks:
                # Fallback to global best practices when no local chunks found
                global_practices_response = await self._get_global_best_practices_response(query, jurisdiction, contract_type)
                return global_practices_response
            
            # Build context from retrieved chunks
            context = "\n\n".join([
                f"[Document Section {i+1} from {chunk['filename']}]:\n{chunk['text']}"
                for i, chunk in enumerate(relevant_chunks)
            ])
            
            # Build analysis prompt
            prompt = self._build_rag_prompt(query, context, jurisdiction, contract_type)
            
            # Call OpenAI API with GPT-4o mini
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
                temperature=0.4  # As requested by user
            )
            
            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise Exception("AI response was empty")
            
            analysis_data = json.loads(content)
            
            # Convert to expected format
            return self._format_analysis_response_with_citations(analysis_data, relevant_chunks)
            
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
        """Build RAG prompt with retrieved context from Pinecone"""
        
        context_info = ""
        if jurisdiction:
            context_info += f"\nJURISDICTION: {jurisdiction}"
        if contract_type:
            context_info += f"\nCONTRACT TYPE: {contract_type}"
        
        return f"""
        Based on the following contract sections retrieved from our persistent knowledge base and the user's question, provide a comprehensive legal analysis.{context_info}
        
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
        
        IMPORTANT: Your response must cite sources using the format [Source: doc_id, chunk_id] for each fact or recommendation you provide based on the retrieved context.
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
            "source_documents": list(set(chunk["filename"] for chunk in chunks)),
            "storage_type": "pinecone_persistent"
        }
    
    async def _get_global_best_practices_response(
        self, 
        query: str, 
        jurisdiction: Optional[str] = None, 
        contract_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback to global best practices when no relevant chunks found"""
        try:
            context_info = ""
            if jurisdiction:
                context_info += f"\nJURISDICTION: {jurisdiction}"
            if contract_type:
                context_info += f"\nCONTRACT TYPE: {contract_type}"
            
            fallback_prompt = f"""
            No contract documents have been uploaded to the system yet.
            
            USER QUESTION: {query}{context_info}
            
            Please provide helpful general guidance about this question based on standard contract law principles and best practices. Start by acknowledging that no documents are uploaded, then answer their question with useful information, and end with friendly instructions.
            
            Please respond in JSON format:
            {{
                "risky_clauses": [],
                "missing_protections": [],
                "overall_risk_score": 0,
                "summary": "No documents uploaded yet. [Then provide helpful general answer to their question about contracts/legal matters]",
                "notes": [
                    "💡 To get specific analysis of your contracts:",
                    "• Upload your contract documents through the web interface",
                    "• Ask questions about specific clauses in your uploaded documents", 
                    "• Get personalized risk assessments and recommendations",
                    "• I can help you understand any contract terms once you upload your documents!"
                ]
            }}
            
            Structure your response to:
            1. Acknowledge no documents uploaded
            2. Answer their question with general contract guidance 
            3. Provide friendly instructions for getting personalized help
            """
            
            # Call OpenAI with global best practices prompt
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly contract attorney. When no documents are uploaded, acknowledge this warmly, provide helpful general guidance about the user's question, then give encouraging instructions about uploading documents for personalized help."
                    },
                    {
                        "role": "user",
                        "content": fallback_prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if not content:
                raise Exception("AI response was empty")
            
            analysis_data = json.loads(content)
            
            return {
                "risky_clauses": analysis_data.get("risky_clauses", []),
                "missing_protections": analysis_data.get("missing_protections", []),
                "overall_risk_score": min(10, max(0, analysis_data.get("overall_risk_score", 0))),
                "summary": analysis_data.get("summary", "No documents uploaded yet. I'd be happy to help with general contract guidance, and once you upload documents, I can provide specific analysis!"),
                "notes": analysis_data.get("notes", ["This response is based on general best practices since no relevant documents were found"]),
                "retrieved_chunks": 0,
                "source_documents": [],
                "storage_type": "global_fallback",
                "fallback_used": True
            }
            
        except Exception as e:
            return {
                "risky_clauses": [],
                "missing_protections": [],
                "overall_risk_score": 0,
                "summary": "No documents uploaded yet. I'd be happy to help with general contract guidance! For specific analysis of your contracts, please upload your documents first.",
                "notes": [
                    "💡 To get specific analysis of your contracts:",
                    "• Upload your contract documents through the web interface",
                    "• Ask questions about specific clauses in your uploaded documents", 
                    "• Get personalized risk assessments and recommendations",
                    "• I can help you understand any contract terms once you upload your documents!"
                ],
                "retrieved_chunks": 0,
                "source_documents": [],
                "storage_type": "fallback_error"
            }
    
    def _format_analysis_response_with_citations(self, analysis_data: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format analysis response with proper source citations"""
        # Add citations to summary and notes
        sources_info = []
        for chunk in chunks:
            if chunk.get("doc_id") and chunk.get("chunk_id"):
                sources_info.append(f"[Source: {chunk['doc_id']}, {chunk['chunk_id']}]")
        
        summary = analysis_data.get("summary", "")
        if sources_info and summary:
            summary += f"\n\nSources: {', '.join(sources_info[:3])}"  # Limit to top 3 sources
        
        return {
            "risky_clauses": analysis_data.get("risky_clauses", []),
            "missing_protections": analysis_data.get("missing_protections", []),
            "overall_risk_score": min(10, max(0, analysis_data.get("overall_risk_score", 0))),
            "summary": summary,
            "notes": analysis_data.get("notes", []),
            "retrieved_chunks": len(chunks),
            "source_documents": list(set(chunk["filename"] for chunk in chunks)),
            "source_citations": sources_info,
            "doc_ids_referenced": list(set(chunk.get("doc_id", "") for chunk in chunks if chunk.get("doc_id"))),
            "storage_type": "pinecone_persistent_with_citations"
        }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index"""
        if not self.index:
            return {
                "status": "disconnected",
                "error": "The knowledge database is temporarily unavailable. Please try again shortly.",
                "total_vectors": 0,
                "index_name": self.index_name
            }
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "status": "connected",
                "total_vectors": stats.total_vector_count,
                "index_name": self.index_name,
                "dimension": self.dimension,
                "storage_type": "pinecone_persistent"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get index stats: {str(e)}",
                "total_vectors": 0,
                "index_name": self.index_name
            }
    
    def is_available(self) -> bool:
        """Check if Pinecone service is available"""
        return self.index is not None