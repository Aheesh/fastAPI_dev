# Account Aggregator FastAPI Application

This FastAPI application implements the Account Aggregator (AA) specification for financial data aggregation. It provides endpoints for consent management and financial information retrieval through the AA framework.

## Features

- Consent Management (Request, Fetch, and Signature)
- Financial Information Request and Fetch
- Encryption/Decryption of Financial Data
- AA Protocol Implementation

## Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- Account Aggregator sandbox credentials

## Installation

1. Clone the repository

git clone <your-repo-url>
cd <repo-name>


2. Create and activate virtual environment

Create virtual environment
python -m venv venv
Activate virtual environment
On Windows:
venv\Scripts\activate
On macOS/Linux:
source venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Create `.env` file with your configuration
env
SANDBOX_API_URL=your_api_url
SANDBOX_API_SIGNATURE=your_api_signature
SANDBOX_API_META_AA=your_api_meta

5. Run the application

uvicorn main:app --reload

The API will be available at `http://localhost:8000`

## API Endpoints

### Consent Flow

1. **Create Consent Request**
   ```
   POST /ConsentRequest
   ```
   - Creates a new consent request
   - Request body: `{"Mobile": "1234567890"}`
   - Returns: Consent handle

2. **Fetch Consent ID**
   ```
   POST /ConsentID
   ```
   - Fetches consent ID using consent handle
   - Request body: `{"txnid": "...", "consent_handle": "..."}`
   - Returns: Consent ID

3. **Get Consent Signature**
   ```
   POST /ConsentSignature
   ```
   - Fetches digital signature for consent
   - Request body: `{"txnid": "...", "consent_id": "..."}`
   - Returns: Digital signature

### FI Flow

4. **Initiate FI Request**
   ```
   POST /FIRequest
   ```
   - Initiates financial information request
   - Request body:
     ```json
     {
       "txnid": "...",
       "consent_id": "...",
       "digital_signature": "...",
       "from_date": "YYYY-MM-DD",
       "to_date": "YYYY-MM-DD"
     }
     ```
   - Returns: Session ID

5. **Fetch FI Data**
   ```
   POST /FIFetch
   ```
   - Fetches encrypted financial information
   - Request body:
     ```json
     {
       "txnid": "...",
       "session_id": "...",
       "fip_id": "FIP-SIMULATOR",
       "link_ref_numbers": ["..."]
     }
     ```
   - Returns: Encrypted FI data

   ## Dependencies

   text
fastapi==0.109.1
uvicorn==0.27.0
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.6.1
cryptography==42.0.2
python-multipart==0.0.9
python-jose==3.3.0

## Environment Variables

Create a `.env` file in the project root with the following variables:

API Configuration
SANDBOX_API_URL=https://api-sandbox.example.com
SANDBOX_API_SIGNATURE=your_api_signature
SANDBOX_API_META_AA=your_aa_meta_value

## Usage Example

1. Create a consent request:
curl -X POST http://localhost:8000/ConsentRequest \
-H "Content-Type: application/json" \
-d '{"Mobile": "1234567890"}'

2. Get consent ID using the handle:
curl -X POST http://localhost:8000/ConsentID \
-H "Content-Type: application/json" \
-d '{"txnid": "your-txn-id", "consent_handle": "consent-handle-from-step-1"}'

3. Follow similar pattern for subsequent API calls

## Development

To run the application in development mode:

uvicorn main:app --reload --port 8000

The API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Security Notes

- Store sensitive keys securely
- Don't commit `.env` file to version control
- Implement proper error handling in production
- Use secure key storage for production deployments

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request