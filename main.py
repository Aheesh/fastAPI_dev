from fastapi import FastAPI
from pydantic import BaseModel
import requests
from datetime import datetime, timezone, timedelta
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


class Customer(BaseModel):
    Mobile: int 
    PAN: str | None = None  
    email: str | None = None
    Aadhar: int | None = None


app = FastAPI()


@app.post("/consent")
async def create_item(item: Customer):
    # Prepare the consent request payload
    consent_payload = {
        "ver": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "txnid": "34",
        "ConsentDetail": {
            "consentStart": datetime.now(timezone.utc).isoformat(),
            "consentExpiry": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "consentMode": "VIEW",
            "fetchType": "ONETIME",
            "consentTypes": ["PROFILE"],
            "fiTypes": ["DEPOSIT"],
            "DataConsumer": {
                "id": "DC1",
                "type": "FIU"
            },
            "Customer": {
                "id": "customer1@identifier2.io",
                "Identifiers": [
                    {
                        "type": "MOBILE",
                        "value": str(item.Mobile) if item.Mobile else None
                    }
                ]
            },
            "Purpose": {
                "code": "101",
                "refUri": "https://api.rebit.org.in/aa/purpose/101.xml",
                "text": "Wealth management service",
                "Category": {
                    "type": "string"
                }
            },
            "FIDataRange": {
                "from": "2023-07-06T11:39:57.153Z",
                "to": "2019-12-06T11:39:57.153Z"
            },
            "DataLife": {
                "unit": "MONTH",
                "value": 0
            },
            "Frequency": {
                "unit": "HOUR",
                "value": 1
            },
            "DataFilter": [
                {
                    "type": "TRANSACTIONAMOUNT",
                    "operator": ">=",
                    "value": "1000"
                }
            ]
        }
    }

    headers = {
        'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',  # Add Bearer token
        'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
        'x-request-meta': os.getenv('SANDBOX_API_META'),
        'Content-Type': 'application/json'
    }

    # Debug print (masking sensitive data)
    debug_headers = headers.copy()
    for key in debug_headers:
        if debug_headers[key] and len(debug_headers[key]) > 20:
            debug_headers[key] = debug_headers[key][:20] + "..."
    print(f"Headers being sent: {debug_headers}")
    print(f"URL being called: {os.getenv('SANDBOX_API_URL')}")

    try:
        response = requests.post(
            os.getenv('SANDBOX_API_URL'),  # Using URL from env file
            json=consent_payload,
            headers=headers
        )
        # Add detailed error logging
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        
        # Extract consentHandle from response
        consent_handle = response.json().get('ConsentHandle')
        
        return {
            "message": "Customer created successfully",
            "consentHandle": consent_handle
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to create consent: {str(e)}"}



