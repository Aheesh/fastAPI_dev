import requests

response = requests.post(
    "https://api.sandbox.sahamati.org.in/proxy/v2/Consent",
    headers={"x-jws-signature":"text",
             "x-request-meta":"text",
             "Content-Type":"application/json"},
    json={
            "ver":"2.0.0",
          "timestamp":"2023-06-26T11:39:57.153Z",
          "txnid":"4a4adbbe-29ae-11e8-a8d7-0289437bf331",
          "ConsentDetail":      
          {
              "consentStart":"2019-12-06T11:39:57.153Z",
              "consentExpiry":"2019-12-06T11:39:57.153Z",
              "consentMode":"VIEW",
              "fetchType":"ONETIME",
              "consentTypes":["PROFILE"],
              "fiTypes":["DEPOSIT"],
              "DataConsumer":{"id":"DC1","type":"FIU"},
              "Customer":{},
              "Purpose":{"code":"101"},
              "FIDataRange":{"from":"2023-07-06T11:39:57.153Z","to":"2019-12-06T11:39:57.153Z"},
              "DataLife":{"unit":"MONTH","value":0},
              "Frequency":{"unit":"HOUR","value":1}    
          }
        }
)
data = response.json()