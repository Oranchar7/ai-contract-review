import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore import Client

class FirebaseClient:
    """Service for Firebase/Firestore integration"""
    
    def __init__(self):
        self.db: Optional[Client] = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection with production credentials"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Get Firebase project ID from environment
                project_id = os.environ.get("FIREBASE_PROJECT_ID")
                
                if not project_id:
                    raise Exception("FIREBASE_PROJECT_ID environment variable is required")
                
                # Initialize with service account key from environment if available
                service_account_info = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
                
                if service_account_info:
                    # Parse service account key from environment variable
                    service_account = json.loads(service_account_info)
                    cred = credentials.Certificate(service_account)
                else:
                    # Use default credentials for production (works in Google Cloud environments)
                    cred = credentials.ApplicationDefault()
                
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            
            self.db = firestore.client()
            print(f"Firebase initialized successfully with project: {os.environ.get('FIREBASE_PROJECT_ID')}")
            
        except Exception as e:
            print(f"Warning: Firebase initialization failed: {str(e)}")
            print("Contract analysis will work without Firebase, but data won't be persisted.")
            self.db = None
    
    async def store_analysis(
        self, 
        analysis_data: Dict[str, Any], 
        filename: str, 
        email: Optional[str] = None
    ) -> str:
        """
        Store contract analysis results in Firestore
        
        Args:
            analysis_data: The analysis results to store
            filename: Original filename of the analyzed contract
            email: Optional user email
            
        Returns:
            str: Document ID of the stored analysis
        """
        if not self.db:
            # Return a mock ID if Firebase is not available
            return f"mock_id_{datetime.now().timestamp()}"
        
        try:
            # Prepare document data
            document_data = {
                'analysis': analysis_data,
                'filename': filename,
                'email': email,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'status': 'completed'
            }
            
            # Store in Firestore
            doc_ref = self.db.collection('contract_analyses').add(document_data)
            document_id = doc_ref[1].id
            
            print(f"Analysis stored in Firestore with ID: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"Failed to store analysis in Firebase: {str(e)}")
            # Return a fallback ID
            return f"error_id_{datetime.now().timestamp()}"
    
    async def get_analysis(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis results by document ID
        
        Args:
            document_id: The document ID to retrieve
            
        Returns:
            Dict with analysis data or None if not found
        """
        if not self.db:
            return None
        
        try:
            doc_ref = self.db.collection('contract_analyses').document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            print(f"Failed to retrieve analysis from Firebase: {str(e)}")
            return None
    
    async def get_user_analyses(self, email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get analysis history for a specific user
        
        Args:
            email: User email address
            limit: Maximum number of results to return
            
        Returns:
            List of analysis documents
        """
        if not self.db:
            return []
        
        try:
            query = (
                self.db.collection('contract_analyses')
                .where('email', '==', email)
                .order_by('created_at', direction='DESCENDING')
                .limit(limit)
            )
            
            docs = query.stream()
            analyses = []
            
            for doc in docs:
                analysis_data = doc.to_dict()
                analysis_data['id'] = doc.id
                analyses.append(analysis_data)
            
            return analyses
            
        except Exception as e:
            print(f"Failed to retrieve user analyses: {str(e)}")
            return []
    
    async def update_analysis_status(self, document_id: str, status: str) -> bool:
        """
        Update the status of an analysis document
        
        Args:
            document_id: The document ID to update
            status: New status value
            
        Returns:
            bool: True if update was successful
        """
        if not self.db:
            return False
        
        try:
            doc_ref = self.db.collection('contract_analyses').document(document_id)
            doc_ref.update({
                'status': status,
                'updated_at': datetime.now(timezone.utc)
            })
            return True
            
        except Exception as e:
            print(f"Failed to update analysis status: {str(e)}")
            return False
    
    async def delete_analysis(self, document_id: str) -> bool:
        """
        Delete an analysis document
        
        Args:
            document_id: The document ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        if not self.db:
            return False
        
        try:
            self.db.collection('contract_analyses').document(document_id).delete()
            return True
            
        except Exception as e:
            print(f"Failed to delete analysis: {str(e)}")
            return False
    
    async def create_user(self, email: str, password: str) -> Dict[str, Any]:
        """Create a new user with email and password"""
        if not self.db:
            return {"error": "Firebase not available"}
        
        try:
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                password=password,
                email_verified=False
            )
            
            # Create user profile in Firestore
            user_data = {
                'uid': user_record.uid,
                'email': email,
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'documents_uploaded': 0,
                'total_chat_messages': 0
            }
            
            self.db.collection('users').document(user_record.uid).set(user_data)
            
            return {
                "success": True,
                "uid": user_record.uid,
                "email": email
            }
            
        except Exception as e:
            return {"error": f"Failed to create user: {str(e)}"}
    
    async def verify_user(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token and return user info"""
        if not self.db:
            return None
        
        try:
            # Verify the token
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']
            
            # Get user profile from Firestore
            user_doc = self.db.collection('users').document(uid).get()
            
            if user_doc.exists:
                return user_doc.to_dict()
            return None
            
        except Exception as e:
            print(f"Failed to verify user: {str(e)}")
            return None
    
    async def store_contract_submission(
        self,
        email: str,
        jurisdiction: str,
        contract_type: str,
        other_contract_type: str = None,
        filename: str = None
    ) -> str:
        """Store contract form submission in secure 'contracts' collection"""
        if not self.db:
            return f"mock_contract_{datetime.now().timestamp()}"
        
        try:
            # Build contract submission data
            contract_data = {
                'email': email,
                'jurisdiction': jurisdiction,
                'contractType': contract_type,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Add otherContractType if "Other" was selected
            if contract_type == "Other" and other_contract_type:
                contract_data['otherContractType'] = other_contract_type
            
            # Add filename if provided (for uploads)
            if filename:
                contract_data['filename'] = filename
                contract_data['hasUpload'] = True
            else:
                contract_data['hasUpload'] = False
            
            # Store in 'contracts' collection with auto-generated ID
            doc_ref = self.db.collection('contracts').add(contract_data)
            print(f"Contract submission stored with ID: {doc_ref[1].id}")
            return doc_ref[1].id
            
        except Exception as e:
            print(f"Failed to store contract submission: {str(e)}")
            return f"error_contract_{datetime.now().timestamp()}"
    
    async def store_document_metadata(
        self,
        filename: str,
        email: str,
        jurisdiction: str,
        contract_type: str,
        vector_id: str
    ) -> str:
        """Store document metadata in Firestore (legacy method)"""
        if not self.db:
            return f"mock_doc_{datetime.now().timestamp()}"
        
        try:
            doc_data = {
                'filename': filename,
                'email': email,
                'jurisdiction': jurisdiction,
                'contract_type': contract_type,
                'vector_id': vector_id,
                'upload_time': datetime.now(timezone.utc),
                'status': 'processed'
            }
            
            doc_ref = self.db.collection('documents').add(doc_data)
            return doc_ref[1].id
            
        except Exception as e:
            print(f"Failed to store document metadata: {str(e)}")
            return f"error_doc_{datetime.now().timestamp()}"
    
    async def store_chat_history(
        self,
        email: str,
        user_question: str,
        ai_response: str,
        retrieved_chunks: List[Dict[str, Any]],
        jurisdiction: Optional[str] = None,
        contract_type: Optional[str] = None
    ) -> str:
        """Store chat interaction in Firestore"""
        if not self.db:
            return f"mock_chat_{datetime.now().timestamp()}"
        
        try:
            chat_data = {
                'email': email,
                'user_question': user_question,
                'ai_response': ai_response,
                'retrieved_chunks': retrieved_chunks,
                'jurisdiction': jurisdiction,
                'contract_type': contract_type,
                'timestamp': datetime.now(timezone.utc),
                'response_length': len(ai_response)
            }
            
            doc_ref = self.db.collection('chat_history').add(chat_data)
            return doc_ref[1].id
            
        except Exception as e:
            print(f"Failed to store chat history: {str(e)}")
            return f"error_chat_{datetime.now().timestamp()}"
    
    async def get_all_contracts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all contract submissions (admin only)"""
        if not self.db:
            return []
        
        try:
            # Get all contracts from the secure collection
            docs = self.db.collection('contracts').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            contracts = []
            for doc in docs:
                contract = doc.to_dict()
                contract['id'] = doc.id
                contracts.append(contract)
            
            return contracts
            
        except Exception as e:
            print(f"Failed to retrieve contracts: {str(e)}")
            return []
    
    async def get_user_chat_history(self, email: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        if not self.db:
            return []
        
        try:
            query = (
                self.db.collection('chat_history')
                .where('email', '==', email)
                .order_by('timestamp', direction='DESCENDING')
                .limit(limit)
            )
            
            docs = query.stream()
            history = []
            
            for doc in docs:
                chat_data = doc.to_dict()
                chat_data['id'] = doc.id
                history.append(chat_data)
            
            return history
            
        except Exception as e:
            print(f"Failed to retrieve chat history: {str(e)}")
            return []
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get basic analytics about contract analyses
        
        Returns:
            Dict with analytics data
        """
        if not self.db:
            return {"error": "Firebase not available"}
        
        try:
            # Get total count of analyses
            analyses_ref = self.db.collection('contract_analyses')
            total_analyses = len(list(analyses_ref.stream()))
            
            # Get total documents uploaded
            docs_ref = self.db.collection('documents')
            total_documents = len(list(docs_ref.stream()))
            
            # Get total users
            users_ref = self.db.collection('users')
            total_users = len(list(users_ref.stream()))
            
            # Get total chat messages
            chat_ref = self.db.collection('chat_history')
            total_chats = len(list(chat_ref.stream()))
            
            return {
                'total_analyses': total_analyses,
                'total_documents': total_documents,
                'total_users': total_users,
                'total_chats': total_chats,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to get analytics: {str(e)}"}
