import boto3
import logging

from botocore.exceptions import ClientError
from typing import Optional, Dict, List
from parse import get_S3_policy_document
from parse import get_trust_policy_document
from parse import get_ssh_key_content

# environment variables
account_id = '649363699007'
region = 'ca-central-1'

# 1. Set up an S3 bucket 
def create_or_get_s3_bucket(name: str, region: str) -> Optional[bool]:
   """Create an S3 bucket. If the bucket is already created,
   then just return it as is.

   : create_bucket returns a dict of bucket info
   """
   s3 = boto3.client('s3')  
   try:
      s3.create_bucket(
         Bucket=name, 
         CreateBucketConfiguration={
            'LocationConstraint': region
         }
      )
   except ClientError as error:
      s3_error = error.response['Error']
      if s3_error['Code'] == 'BucketAlreadyExists':
         logging.error(s3_error['Message'])
         return False
      print(s3_error['Message'])
   return True

# 2. set up the S3 policy
def create_or_get_iam_policy(policy_name: str, bucket_name: str) -> dict:
   """Create an IAM policy that defines the actions a service may
   apply onto the target S3 bucket.
   """
   iam = boto3.client('iam')
   try:
      s3_policy_document = get_S3_policy_document(bucket_name)
      s3_policy = iam.create_policy(
         PolicyName=policy_name, 
         PolicyDocument=s3_policy_document
      )
      return s3_policy
   except ClientError as error:
      logging.error(error)
      # Policy already created...
      # EntityAlreadyExists exception
      response = iam.list_policies(Scope='Local')
      for policy in response['Policies']:
         if policy['PolicyName'] == policy_name:
            return {'Policy': policy}

# 3.1. Set up an IAM role
def create_or_get_iam_role(role_name: str, trust_entity: str = 'transfer') -> dict:
   """Create an IAM role for Transfer Family. Establish a trust 
   relationship between Transfer Family and AWS. 
   """
   iam = boto3.client('iam')
   try:
      trust_policy_document = get_trust_policy_document(
         account_id=account_id,
         region=region,
         service=trust_entity
      )
      role = iam.create_role(
         RoleName=role_name,
         # Establish a trust relationship 
         AssumeRolePolicyDocument=trust_policy_document
      )
      return role
   except ClientError as error:
      logging.error(error)
      # Role already created...
      # EntityAlreadyExists exception
      return iam.get_role(RoleName=role_name)

# 3.2. Attach policies to IAM role
def attach_policies_to_iam_role(policies: Dict[str, List[str]], role_name: str) -> None:
   """Attach managed policies to the IAM role.
   """
   role = boto3.resource('iam').Role(role_name)
   for account, policy_names in policies.items():
      for policy_name in policy_names:
         if account.lower() == 'customer':
            policy_arn = f'arn:aws:iam::{account_id}:policy/{policy_name}'
         else:
            policy_arn = f'arn:aws:iam::aws:policy/{policy_name}'

         role.attach_policy(PolicyArn=policy_arn)
   
# 4. Set up an SFTP server 
def create_or_get_sftp_server(protocol: str, provider: str, endpoint: str, domain: str, host_key: bool) -> dict:
   """Create a service-managed SFTP server with Transfer 
   Family. The server is hosted publicly with S3 as the 
   storage domain. SSH host keys will be needed for migrating
   local user to the SFTP server.
   """
   transfer = boto3.client('transfer')

   try:
      server_lists = transfer.list_servers()
      # Check if there is any server already created
      if len(server_lists['Servers']) >= 1:
         return {'ServerId': server_lists['Servers'][0]['ServerId']}

      ssh_private_key_content = get_ssh_key_content(type='private')
      
      server = transfer.create_server(
         Protocols=[protocol],
         IdentityProviderType=provider,
         EndpointType=endpoint,
         Domain=domain,
         # submit the ssh private key content for user authentication
         HostKey=ssh_private_key_content
      )

      return server
   except ClientError as error:
      logging.error(error)

# 5. Set up an SFTP user 
def create_or_get_sftp_user(username: str, role_name: str, server_id: str, home_directory: str, ssh_public_key: bool) -> dict:
   """Create a user for the SFTP server endowed with the Transfer 
   Family role. The user will land on the S3 bucket home directory. SSH public key is needed to authenticate with the server. 
   """
   transfer = boto3.client('transfer')
   try:
      # Retrieve relevant configuration parameters 
      # Set up a user for the server
      user = transfer.create_user(
         UserName=username,
         ServerId=server_id,
         Role=f'arn:aws:iam::{account_id}:role/{role_name}',
         HomeDirectory='/' + home_directory,
         SshPublicKeyBody=get_ssh_key_content(type='public')
      )

      return user
   except ClientError as error:
      user_error = error.response['Error']
      logging.error(user_error['Message'])
      # ResourceExistsException
      users = transfer.list_users(ServerId=server_id)
      # a list of dictionary about server users
      for user in users['Users']:
         if user['UserName'] == username:
            user['ServerId'] = users['ServerId']
            return user
   
# 6. Set up a Redshift cluster
def create_or_get_redshift_cluster():
   """Create a Redshift cluster on Postgres.
   """
   pass