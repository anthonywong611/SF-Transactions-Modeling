import os 
import json

from typing import Union

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

# Intermediary step to parse key content
def get_ssh_key_content(type: str) -> str:
   # Keep track of the project directory
   project_dir = os.getcwd()
   assert 'ssh' in os.listdir()
   # Make sure in the ssh/ directory
   os.chdir('./ssh')
   # Must already have ssh key pairs generated
   assert os.listdir() != []

   ssh_key_pairs = list(filter(lambda file: '.sh' not in file, os.listdir()))

   # Request ssh public key
   if type == 'public':
      ssh_key = list(filter(lambda file: '.pub' in file, ssh_key_pairs))[0]
   else: # Request ssh private key
      ssh_key = list(filter(lambda file: '.pub' not in file, ssh_key_pairs))[0]

   # Convert ssh key into string format
   with open(ssh_key) as file:
      ssh_key_content = ''.join(file.readlines())

   # return to project directory
   os.chdir(project_dir)

   return ssh_key_content
