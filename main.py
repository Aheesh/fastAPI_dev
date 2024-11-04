from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from datetime import datetime, timezone, timedelta
import json
from dotenv import load_dotenv
import os
import uuid
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from base64 import b64encode

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
async def create_consent_request(item: Customer):
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
        'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
        'Content-Type': 'application/json'
    }

    # Debug print (masking sensitive data)
    debug_headers = headers.copy()
    for key in debug_headers:
        if debug_headers[key] and len(debug_headers[key]) > 20:
            debug_headers[key] = debug_headers[key][:20] + "..."
    print(f"Headers being sent: {debug_headers}")
    print(f"URL being called: {os.getenv('SANDBOX_API_URL')}/Consent")

    try:
        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/Consent",  # Using URL from env file
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
# Consent handle is received from the consent request API. Authorization is done using the bearer token and signature
# function returns the consent handle, consent id and consent status
    

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
        'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/Consent/handle",
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
            "consentId": response_data.get('ConsentStatus', {}).get('id'),  # Get ID from consentStatus object
            "consentStatus": response_data.get('ConsentStatus', {}).get('status')  # Get status from consentStatus object
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch consent ID: {str(e)}"}

# POST request to fetch the consent signature using the txn_id and consent_id from /proxy/v2/Consent/fetch
@app.post("/ConsentSignature")
async def get_consent_signature(txnid: str, consent_id: str):
    # Prepare the payload
    payload = {
        "ver": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "txnid": txnid,
        "consentId": consent_id
    }

    headers = {
        'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
        'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
        'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/Consent/fetch",
            json=payload,
            headers=headers
        )
        
        # Debug logging
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        
        return {
            "ver": response_data.get('ver'),
            "txnid": response_data.get('txnid'),
            "consentId": response_data.get('consentId'),
            "status": response_data.get('status'),
            "createTimestamp": response_data.get('createTimestamp'),
            "signedConsent": response_data.get('signedConsent'),
            "ConsentUse": response_data.get('ConsentUse'),
            "timestamp": response_data.get('timestamp')
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch consent signature: {str(e)}"}


# FI Data Fetch flow
# Post function to place a request for FI data using the txn_id and consent id . 
# generate the signature for the request body and send the request to the API.
# The function returns the consent id, txn_id and the session_id Example response
# {
#     "ver": "2.0.0",
#     "timestamp": "2024-11-03T00:54:55.781Z",
#     "txnid": "c4a1450c-d08a-45b4-a475-0468bd10e380",
#     "consentId": "654024c8-29c8-11e8-8868-0289437bf33133",
#     "sessionId": "2583957a-006d-438d-a6a1-3a9a90225c74"
# }

class FIRequestInput(BaseModel):
    txnid: str
    consent_id: str
    digital_signature: str
    from_date: str | None = None  # Optional
    to_date: str | None = None    # Optional

def generate_key_material():
    """Generate KeyMaterial including ECDH key pair"""
    try:
        # Generate private key
        private_key = x25519.X25519PrivateKey.generate()
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize public key to bytes and encode as base64
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_b64 = b64encode(public_bytes).decode('utf-8')
        
        # Generate expiry timestamp (30 minutes from now)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        # Create KeyMaterial structure
        key_material = {
            "cryptoAlg": "ECDH",
            "curve": "Curve25519",
            "params": "cipher=AES/GCM/NoPadding;KeyPairGenerator=ECDH",
            "DHPublicKey": {
                "expiry": expiry.isoformat(),
                "Parameters": "",  # Empty as per AA specification
                "KeyValue": public_b64
            },
            "Nonce": str(uuid.uuid4())
        }
        
        return key_material, private_key
    except Exception as e:
        print(f"Error generating key material: {str(e)}")
        raise

@app.post("/FIRequest")
async def fetch_fi_data(request: FIRequestInput):
    try:
        # Generate key material and get private key
        key_material, private_key = generate_key_material()
        
        # Store private key securely for later use
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        # In production, store this securely instead of printing
        print(f"Private Key (store securely): {b64encode(private_bytes).decode('utf-8')}")
        
        # Prepare the payload
        payload = {
            "ver": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "txnid": request.txnid,
            "Consent": {
                "id": request.consent_id,
                "digitalSignature": request.digital_signature
            },
            "FIDataRange": {
                "from": request.from_date,
                "to": request.to_date
            },
            "KeyMaterial": key_material
        }

        headers = {
            'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
            'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
            'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
            'Content-Type': 'application/json'
        }

        # Debug print (masking sensitive data)
        debug_headers = headers.copy()
        for key in debug_headers:
            if debug_headers[key] and len(debug_headers[key]) > 20:
                debug_headers[key] = debug_headers[key][:20] + "..."
        print(f"Headers being sent: {debug_headers}")
        print(f"URL being called: {os.getenv('SANDBOX_API_URL')}/FI/request")

        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/FI/request",
            json=payload,
            headers=headers
        )
        
        # Debug logging
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        
        # Store the session details for later use
        session_info = {
            "txnid": response_data.get('txnid'),
            "sessionId": response_data.get('sessionId'),
            "private_key": b64encode(private_bytes).decode('utf-8')
        }
        # In production, store this securely
        print(f"Session Info (store securely): {session_info}")
        
        return {
            "ver": response_data.get('ver'),
            "timestamp": response_data.get('timestamp'),
            "txnid": response_data.get('txnid'),
            "consentId": response_data.get('consentId'),
            "sessionId": response_data.get('sessionId')
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch FI data: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")