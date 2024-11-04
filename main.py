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
                "id": "customer2@identifier3.io",
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
        'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',  # Check if Bearer token is correct
        'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
        'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
        'Content-Type': 'application/json'
    }

    # Add debug logging to see exact header values
    print("\n=== Debug Headers ===")
    print("Authorization:", headers['Authorization'])
    print("x-jws-signature:", headers['x-jws-signature'])
    print("x-request-meta:", headers['x-request-meta'])

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
    """Generate KeyMaterial from locally stored keys"""
    try:
        # Load pre-generated keys from local file
        with open('dhk.json', 'r') as f:
            key_data = json.load(f)
            
        # Debug print
        print("Loaded key data:", json.dumps(key_data, indent=2))
            
        if 'KeyMaterial' not in key_data:
            raise KeyError("KeyMaterial not found in key data")
        if 'DHPublicKey' not in key_data['KeyMaterial']:
            raise KeyError("DHPublicKey not found in KeyMaterial")
        
        # Generate a new Nonce using base64
        nonce = b64encode(os.urandom(32)).decode('utf-8')
        
        # Update expiry to current time + 30 minutes
        expiry = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
        
        # Format KeyMaterial exactly as per the sample
        key_material = {
            "cryptoAlg": "ECDH",
            "curve": "Curve25519",
            "params": "",  # Empty string as per sample
            "DHPublicKey": {
                "expiry": expiry,
                "Parameters": "",
                "KeyValue": key_data['KeyMaterial']['DHPublicKey']['KeyValue']  # Keep PEM format
            },
            "Nonce": nonce
        }
        
        print("\n=== Generated KeyMaterial ===")
        print(json.dumps(key_material, indent=2))
        
        return key_material, key_data['privateKey']
        
    except FileNotFoundError:
        print("dhk.json file not found")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing dhk.json file: {str(e)}")
        raise
    except KeyError as e:
        print(f"Missing required key in dhk.json: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

@app.post("/FIRequest")
async def fetch_fi_data(request: FIRequestInput):
    try:
        key_material, private_key = generate_key_material()
        
        # Store the private key and session details for later use
        # You might want to use Redis or a similar store in production
        session_data = {
            "private_key": private_key,
            "session_id": None,  # Will be filled from response
            "key_material": key_material
        }
        
        payload = {
            "ver": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "txnid": request.txnid,
            "Consent": {
                "id": request.consent_id,
                "digitalSignature": request.digital_signature
            },
            "KeyMaterial": key_material,
            "FIDataRange": {
                "from": request.from_date or "2023-01-01T00:00:00.000Z",
                "to": request.to_date or datetime.now(timezone.utc).isoformat()
            }
        }

        print("\n=== FIRequest Payload ===")
        print(json.dumps(payload, indent=2))

        headers = {
            'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
            'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
            'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/FI/request",
            json=payload,
            headers=headers
        )
        
        print(f"\n=== FIRequest Response ===")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

        response_data = response.json()
        
        # Store session_id with encryption details
        session_data["session_id"] = response_data.get("sessionId")
        
        return response_data

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# FI Data Fetch API uses the txn_id, session_id, fipID and the linkReferenceNumber to fetch the data 
# response captures the encryptedFinancial Data , masked Account data and store it in the database.

class FIFetchInput(BaseModel):
    txnid: str
    session_id: str
    fip_id: str
    link_ref_numbers: list[str]

@app.post("/FIFetch")
async def fetch_fi_data_details(request: FIFetchInput):
    try:
        payload = {
            "ver": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "txnid": request.txnid,
            "sessionId": request.session_id,
            "fipId": "FIP-SIMULATOR",
            "linkRefNumber": [
                {
                    "id": ref_num,
                    "type": "DEPOSIT"
                } for ref_num in request.link_ref_numbers
            ]
        }

        print("\n=== FIFetch Request ===")
        print("Session ID:", request.session_id)
        print("Transaction ID:", request.txnid)
        print("Payload:", json.dumps(payload, indent=2))

        headers = {
            'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
            'x-jws-signature': os.getenv('SANDBOX_API_SIGNATURE'),
            'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/FI/fetch",
            json=payload,
            headers=headers
        )

        if response.status_code != 200:
            print(f"\n=== Error Response ===")
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
            error_detail = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail=f"FI fetch failed: {error_detail}"
            )

        return response.json()

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))