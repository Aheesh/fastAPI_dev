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
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import b64decode
import traceback
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Load environment variables
load_dotenv()

# Define FIDataProcessor class first
class FIDataProcessor:
    def __init__(self):
        self.private_key = None
        self.fiu_nonce = None
        self.key_material = None  # Store the complete key material

    async def decrypt_and_store_fi_data(self, response_data):
        try:
            processed_data = []
            if 'FI' in response_data:
                for fi in response_data['FI']:
                    for data in fi.get('data', []):
                        if 'encryptedFI' in data:
                            if not self.private_key or not self.fiu_nonce or not self.key_material:
                                raise ValueError("Private key, FIU nonce, and key material are required")

                            # Prepare decrypt payload for Rahasya
                            decrypt_payload = {
                                "base64Data": data['encryptedFI'],
                                "base64RemoteNonce": fi['KeyMaterial']['Nonce'],
                                "base64YourNonce": b64encode(self.fiu_nonce).decode('utf-8'),
                                "ourPrivateKey": {
                                    "curve": "Curve25519",
                                    "privateValue": self.private_key
                                },
                                "remoteKeyMaterial": {
                                    "cryptoAlg": fi['KeyMaterial']['cryptoAlg'],
                                    "curve": fi['KeyMaterial']['curve'],
                                    "params": fi['KeyMaterial']['params'],
                                    "DHPublicKey": {
                                        "expiry": fi['KeyMaterial']['DHPublicKey']['expiry'],
                                        "parameters": fi['KeyMaterial']['DHPublicKey']['Parameters'],
                                        "keyValue": fi['KeyMaterial']['DHPublicKey']['KeyValue']
                                    }
                                }
                            }

                            print("\nDecryption Payload:")
                            print(json.dumps(decrypt_payload, indent=2))

                            try:
                                decrypt_response = requests.post(
                                    "http://localhost:8080/ecc/v1/decrypt",
                                    json=decrypt_payload,
                                    headers={'Content-Type': 'application/json'}
                                )
                                
                                print(f"\nDecryption Response Status: {decrypt_response.status_code}")
                                print(f"Decryption Response Body: {decrypt_response.text}")
                                
                                decrypt_response.raise_for_status()
                                decrypted_data = decrypt_response.json()
                                
                                processed_data.append({
                                    'maskedAccNumber': data.get('maskedAccNumber'),
                                    'linkRefNumber': data.get('linkRefNumber'),
                                    'decryptedData': decrypted_data
                                })
                            except requests.exceptions.RequestException as e:
                                print(f"Rahasya decryption service error: {str(e)}")
                                raise

            return processed_data
        except Exception as e:
            print(f"Decryption error: {str(e)}")
            traceback.print_exc()
            raise

# Then define the storage and helper function
processor_storage = {}

def store_processor_for_session(session_id: str, processor: FIDataProcessor):
    processor_storage[session_id] = processor


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
    from_date: str | None = None
    to_date: str | None = None

def generate_key_material():
    """Generate key material using Rahasya service"""
    try:
        # Generate key pair using Rahasya - using GET method
        generate_key_response = requests.get(
            "http://localhost:8080/ecc/v1/generateKey",
            headers={'Content-Type': 'application/json'}
        )
        
        print("\nKey Generation Response:")
        print(f"Status: {generate_key_response.status_code}")
        print(f"Body: {generate_key_response.text}")
        
        generate_key_response.raise_for_status()
        key_data = generate_key_response.json()
        
        # Extract private key and key material from the correct structure
        private_key = key_data['privateKey']
        key_material = key_data['KeyMaterial']  # Use the KeyMaterial object directly
        
        return key_material, private_key
        
    except requests.exceptions.RequestException as e:
        print(f"Rahasya key generation error: {str(e)}")
        raise

@app.post("/FIRequest")
async def request_financial_data(request: FIRequestInput):
    try:
        # Generate key material using Rahasya service
        key_material, private_key = generate_key_material()
        
        # Generate a random nonce
        fiu_nonce = os.urandom(32)  # 32 bytes of random data
        key_material['Nonce'] = b64encode(fiu_nonce).decode('utf-8')
        
        # Create the request payload
        payload = {
            "ver": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "txnid": request.txnid,
            "consentId": request.consent_id,
            "KeyMaterial": key_material
        }

        headers = {
            'Authorization': f'Bearer {os.getenv("SANDBOX_API_SIGNATURE")}',
            'x-jws-signature': request.digital_signature,
            'x-request-meta': os.getenv('SANDBOX_API_META_AA'),
            'Content-Type': 'application/json'
        }

        response = requests.post(
            f"{os.getenv('SANDBOX_API_URL')}/FI/request",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        response_data = response.json()
        
        processor = FIDataProcessor()
        processor.private_key = private_key
        processor.fiu_nonce = fiu_nonce  # Use the generated nonce directly
        processor.key_material = key_material
        
        store_processor_for_session(response_data.get("sessionId"), processor)
        
        return response_data
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add this function before the FIFetch endpoint
def get_stored_private_key(session_id: str) -> str:
    # TODO: In production, retrieve from secure storage (Redis/Database)
    # For demo, return hardcoded key from dhk.json
    with open('dhk.json', 'r') as f:
        return json.load(f)['privateKey']

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
        # Retrieve the stored processor for this session
        processor = processor_storage.get(request.session_id)
        if not processor:
            raise HTTPException(
                status_code=400,
                detail="Session not found. Please make an FI request first."
            )

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

        # Add these debug prints
        print("\n=== FIFetch Response ===")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

        response_data = response.json()
        
        # Use the stored processor to decrypt the data
        processed_data = await processor.decrypt_and_store_fi_data(response_data)
        
        return {
            "status": "success",
            "message": "FI data processed successfully",
            "data": processed_data
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))