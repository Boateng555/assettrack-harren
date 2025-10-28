import os
import requests
import json
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

class MicrosoftGraphEmailBackend(BaseEmailBackend):
    """Custom email backend using Microsoft Graph API"""
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.sender = "it-office-assettrack@harren-group.com"
    
    def get_access_token(self):
        """Get access token using client credentials flow"""
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            token_res = requests.post(token_url, data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            })
            token_res.raise_for_status()
            return token_res.json()["access_token"]
        except Exception as e:
            if not self.fail_silently:
                raise e
            return None
    
    def send_messages(self, email_messages):
        """Send email messages using Microsoft Graph API"""
        if not email_messages:
            return 0
        
        access_token = self.get_access_token()
        if not access_token:
            return 0
        
        sent_count = 0
        for message in email_messages:
            try:
                # Build message payload
                to_recipients = [{"emailAddress": {"address": addr}} for addr in message.to]
                
                # Determine content type and body
                content_type = "Text"
                body_content = message.body
                
                # Check for HTML alternative
                for alt in message.alternatives:
                    if alt[1] == "text/html":
                        content_type = "Html"
                        body_content = alt[0]
                        break
                
                payload = {
                    "message": {
                        "subject": message.subject,
                        "body": {
                            "contentType": content_type,
                            "content": body_content
                        },
                        "toRecipients": to_recipients
                    },
                    "saveToSentItems": True
                }
                
                # Send email via Microsoft Graph
                response = requests.post(
                    f"https://graph.microsoft.com/v1.0/users/{self.sender}/sendMail",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    data=json.dumps(payload)
                )
                
                if response.status_code == 202:
                    sent_count += 1
                    print(f"✅ Email sent successfully via Microsoft Graph (Status: {response.status_code})")
                else:
                    print(f"❌ Email failed via Microsoft Graph (Status: {response.status_code})")
                    if not self.fail_silently:
                        response.raise_for_status()
                        
            except Exception as e:
                print(f"❌ Error sending email via Microsoft Graph: {e}")
                if not self.fail_silently:
                    raise e
        
        return sent_count


