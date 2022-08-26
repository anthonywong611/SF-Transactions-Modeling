import os 
import json


# Intermediary step to parse json document
def get_S3_policy_document(bucket_name: str) -> str:
   # Make sure in the project root directory
   assert 'S3_policy.json' in os.listdir()
   # deserialize into dictionary for Python to work with
   # serialize again for string update
   with open('S3_policy.json') as file:
      policy = json.dumps(json.load(file))

   # update 'bucket_name' placeholder with the S3 bucket name
   policy_document = bucket_name.join(policy.split('bucket_name'))
   
   return policy_document

# Intermediary step to parse json document
def get_trust_policy_document(account_id: str, region: str, service: str) -> str:
   # Make sure in the project root directory
   assert 'trust_policy.json' in os.listdir()
   # deserialize into dictionary for Python to work with
   # serialize again for string update
   with open('trust_policy.json') as file:
      policy = json.dumps(json.load(file))
   
   # update placeholders with actual configuration
   policy = account_id.join(policy.split('account_id'))
   policy = region.join(policy.split('region'))
   policy_document = service.join(policy.split('service'))

   return policy_document