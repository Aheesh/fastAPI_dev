from fastapi import FastAPI
from pydantic import BaseModel
import requests
from datetime import datetime, timezone, timedelta
import json
from dotenv import load_dotenv
import os
import uuid

# Load environment variables
load_dotenv()


class Customer(BaseModel):
    Mobile: int 
    PAN: str | None = None  
    email: str | None = None
    Aadhar: int | None = None


app = FastAPI()

#Consent Request API uses the customer details to create a consent request, mobile number is mandatory
@app.post("/ConsentRequest")
async def create_item(item: Customer):
    # Prepare the consent request payload
    consent_payload = {
        "ver": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "txnid": str(uuid.uuid4()),  # Generate a unique transaction ID
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
            "message": "Customer Consent Request created successfully",
            "Mobile": item.Mobile,
            "txn_id": consent_payload["txnid"],
            "consentHandle": consent_handle
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to create consent: {str(e)}"}


# Post request to fetch the consent id using the consent handle from /proxy/v2/Consent/handle
# here is the sample payload {
    #     "ver": "2.0.0",
    #     "timestamp": "2023-06-26T11:39:57.153Z",
    #     "txnid": "795038d3-86fb-4d3a-a681-2d39e8f4fc3c8787878",
    #     "ConsentHandle": "39e108fe-9243-11e8-b9f2-0256d88"
    # }
    # Where consent handle is received from the consent request API. Authorization is done using the bearer token and the signature
    # the function should return the consent handle, consent id and consent status
    

@app.post("/ConsentID")
async def get_consent_id(txnid: str,consent_handle: str ):
    # Prepare the payload
    payload = {
        "ver": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "txnid": txnid,  # Use the transaction ID passed to the function
        "ConsentHandle": consent_handle
    }

    headers = {
        'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
        'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
        'x-request-meta': os.getenv('SANDBOX_API_META'),
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/handle",
            json=payload,
            headers=headers
        )
        
        # Debug logging
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        print(f"Parsed Response Data: {json.dumps(response_data, indent=2)}")  # Add this line to see the exact structure
        
        return {
            "consentHandle": consent_handle,
            "consentId": response_data.get('consentStatus', {}).get('id'),  # Get ID from consentStatus object
            "consentStatus": response_data.get('consentStatus', {}).get('status')  # Get status from consentStatus object
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch consent ID: {str(e)}"}

