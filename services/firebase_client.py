import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

class FirebaseClient:
    """Service for Firebase/Firestore integration"""
    
    def __init__(self):
        self.db: Optional[Client] = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Initialize with service account key from environment
                service_account_info = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
                
                if service_account_info:
                    # Parse service account key from environment variable
                    service_account = json.loads(service_account_info)
                    cred = credentials.Certificate(service_account)
                else:
                    # Fallback to default credentials (for Google Cloud environments)
                    cred = credentials.ApplicationDefault()
                
                firebase_admin.initialize_app(cred, {
                    'projectId': os.environ.get("FIREBASE_PROJECT_ID")
                })
            
            self.db = firestore.client()
            
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
                .order_by('created_at', direction=firestore.Query.DESCENDING)
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
    
    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get basic analytics about contract analyses
        
        Returns:
            Dict with analytics data
        """
        if not self.db:
            return {"error": "Firebase not available"}
        
        try:
            # Get total count
            analyses_ref = self.db.collection('contract_analyses')
            total_count = len(list(analyses_ref.stream()))
            
            # Get recent count (last 30 days)
            thirty_days_ago = datetime.now(timezone.utc).replace(day=1)  # Simplified for demo
            recent_query = analyses_ref.where('created_at', '>=', thirty_days_ago)
            recent_count = len(list(recent_query.stream()))
            
            return {
                'total_analyses': total_count,
                'recent_analyses': recent_count,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": f"Failed to get analytics: {str(e)}"}
