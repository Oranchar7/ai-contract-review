import os
import json
import asyncio
from typing import Dict, Any, Optional
import requests
from models.contract_analysis import ContractAnalysisResponse

class NotificationService:
    """Service for sending notifications via n8n webhook and other channels"""
    
    def __init__(self):
        self.n8n_webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        self.notification_enabled = bool(self.n8n_webhook_url)
    
    async def send_analysis_notification(
        self, 
        email: str, 
        analysis: ContractAnalysisResponse, 
        filename: str
    ) -> bool:
        """
        Send notification about completed contract analysis
        
        Args:
            email: Recipient email address
            analysis: The contract analysis results
            filename: Original contract filename
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.notification_enabled:
            print(f"Notification service not configured. Would send notification to {email}")
            return False
        
        try:
            # Prepare notification payload
            notification_data = {
                "type": "contract_analysis_complete",
                "recipient_email": email,
                "contract_filename": filename,
                "analysis_summary": {
                    "risk_score": analysis.risk_score,
                    "summary": analysis.summary,
                    "risky_clauses_count": len(analysis.risky_clauses),
                    "missing_protections_count": len(analysis.missing_protections),
                    "document_id": analysis.document_id
                },
                "timestamp": "{{ now() }}",  # n8n will process this
                "dashboard_url": f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/analysis/{analysis.document_id}"
            }
            
            # Send webhook notification
            success = await self._send_webhook_notification(notification_data)
            
            if success:
                print(f"Notification sent successfully to {email}")
            else:
                print(f"Failed to send notification to {email}")
            
            return success
            
        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            return False
    
    async def send_error_notification(
        self, 
        email: str, 
        filename: str, 
        error_message: str
    ) -> bool:
        """
        Send notification about analysis error
        
        Args:
            email: Recipient email address
            filename: Original contract filename
            error_message: Error details
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.notification_enabled:
            print(f"Error notification would be sent to {email}: {error_message}")
            return False
        
        try:
            notification_data = {
                "type": "contract_analysis_error",
                "recipient_email": email,
                "contract_filename": filename,
                "error_message": error_message,
                "timestamp": "{{ now() }}",
                "support_url": f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/support"
            }
            
            return await self._send_webhook_notification(notification_data)
            
        except Exception as e:
            print(f"Error sending error notification: {str(e)}")
            return False
    
    async def send_subscription_notification(
        self, 
        email: str, 
        subscription_type: str, 
        status: str
    ) -> bool:
        """
        Send notification about subscription changes
        
        Args:
            email: User email address
            subscription_type: Type of subscription (basic, premium, etc.)
            status: Subscription status (activated, cancelled, etc.)
            
        Returns:
            bool: True if notification was sent successfully
        """
        if not self.notification_enabled:
            print(f"Subscription notification would be sent to {email}: {subscription_type} - {status}")
            return False
        
        try:
            notification_data = {
                "type": "subscription_update",
                "recipient_email": email,
                "subscription_type": subscription_type,
                "subscription_status": status,
                "timestamp": "{{ now() }}",
                "account_url": f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/account"
            }
            
            return await self._send_webhook_notification(notification_data)
            
        except Exception as e:
            print(f"Error sending subscription notification: {str(e)}")
            return False
    
    async def _send_webhook_notification(self, notification_data: Dict[str, Any]) -> bool:
        """
        Send webhook notification to n8n
        
        Args:
            notification_data: Data to send in the webhook
            
        Returns:
            bool: True if webhook was sent successfully
        """
        if not self.n8n_webhook_url:
            return False
        
        try:
            # Send webhook request
            response = await asyncio.to_thread(
                requests.post,
                self.n8n_webhook_url,
                json=notification_data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'AI-Contract-Review/1.0'
                },
                timeout=10
            )
            
            # Check if request was successful
            if response.status_code in [200, 201, 202]:
                print(f"Webhook sent successfully: {response.status_code}")
                return True
            else:
                print(f"Webhook failed with status: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print("Webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Webhook request failed: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error sending webhook: {str(e)}")
            return False
    
    async def send_bulk_notification(
        self, 
        recipients: list, 
        notification_type: str, 
        data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Send notifications to multiple recipients
        
        Args:
            recipients: List of email addresses
            notification_type: Type of notification to send
            data: Notification data
            
        Returns:
            Dict mapping email addresses to success status
        """
        results = {}
        
        for email in recipients:
            try:
                notification_data = {
                    "type": notification_type,
                    "recipient_email": email,
                    **data,
                    "timestamp": "{{ now() }}"
                }
                
                success = await self._send_webhook_notification(notification_data)
                results[email] = success
                
                # Add small delay to avoid overwhelming the webhook endpoint
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Failed to send notification to {email}: {str(e)}")
                results[email] = False
        
        return results
    
    def is_configured(self) -> bool:
        """Check if notification service is properly configured"""
        return self.notification_enabled
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get configuration status for debugging"""
        return {
            "n8n_webhook_configured": bool(self.n8n_webhook_url),
            "webhook_url_length": len(self.n8n_webhook_url) if self.n8n_webhook_url else 0,
            "service_enabled": self.notification_enabled
        }
