from aifc import Error
import boto3
import logging
import json

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

# 2. Set up the S3 policy for a service
def create_or_get_s3_policy(policy_name: str, bucket_name: str, service: str) -> dict:
   """Create an IAM policy that defines the actions a service may
   apply onto the target S3 bucket.
   """
   iam = boto3.client('iam')
   try:
      s3_policy_document = get_S3_policy_document(bucket_name, service=service)
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

# 3.1. Attach policies to IAM role
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
   
# 3.2. Set up an IAM role for Transfer Family
def create_or_get_transfer_family_role(role_name: str) -> dict:
   """Create an IAM role for Transfer Family. Establish a trust 
   relationship between Transfer Family and AWS for it to behave on 
   user's behalf. 
   """
   iam = boto3.client('iam')
   try:
      trust_policy_document = get_trust_policy_document(
         account_id=account_id,
         region=region
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

# 3.3. Set up an SFTP server 
def create_or_get_sftp_server(protocol: str, provider: str, endpoint: str, domain: str) -> dict:
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

# 3.4. Set up an SFTP user 
def create_or_get_sftp_user(username: str, role_name: str, server_id: str, home_directory: str) -> dict:
   """Create a user for the SFTP server endowed with the Transfer 
   Family role. The user will land on the S3 bucket home directory. 
   SSH public key is needed to authenticate with the server. 
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
   
# 4.1. Set up an IAM role for Redshift
def create_or_get_redshift_role(role_name: str, s3_policy_name: str, s3_bucket: str) -> dict:
   """Create an IAM role for Redshift. The role is granted full access to Redshift including console and editor. A policy defining the actions allowed on the S3 bucket is attached.
   """
   iam = boto3.client('iam')

   try:
      iam.create_role(
         RoleName=role_name,
         AssumeRolePolicyDocument=json.dumps(
            {
               "Version": "2012-10-17",
               "Statement": [
                  {
                     "Effect": "Allow",
                     "Principal": {
                        "Service": [
                           "redshift.amazonaws.com"
                        ]
                     },
                     "Action": "sts:AssumeRole"
                  }
               ]
            }
         )
      )

      create_or_get_s3_policy(
         policy_name=s3_policy_name, 
         bucket_name=s3_bucket, 
         service='redshift'
      )

      # attach the policies to the role
      attach_policies_to_iam_role(
         role_name=role_name,
         policies={
            'customer': [s3_policy_name],
            'aws': ['AmazonRedshiftAllCommandsFullAccess']
         }
      )
   except ClientError as error:
      # EntityAlreadyExists
      logging.error(error)

   return iam.get_role(RoleName=role_name)

# 4.2. Set up a Security Group for Routing Traffic to Redshift
def create_or_get_security_group(group_name: str) -> dict:
   """Create a security group that routes inbound traffic
   to the port 5439.
   """   
   ec2 = boto3.client('ec2')
   try:
      security_group = ec2.create_security_group(
         GroupName=group_name,
         Description='Route all inbound traffic on TCP port 5439'
      )

      # Wait for the security group to become available
      ec2.get_waiter('security_group_exists').wait(GroupNames=[group_name])

      # Add inbound rule that route traffic to TCP on port 5439
      ec2.authorize_security_group_ingress(
         GroupId=security_group['GroupId'],
         IpPermissions=[
            {
               'FromPort': 5439,
               'IpProtocol': 'tcp',
               'IpRanges': [
                  {
                     'CidrIp': '0.0.0.0/0'
                  }
               ],
               'ToPort': 5439
            }
         ]
      )
   except ClientError as error:
      # InvalidGroup.Duplicate error
      logging.error(error)
      
   groups = ec2.describe_security_groups(GroupNames=[group_name])
   return groups['SecurityGroups'][0]

# 4.3. Set up a Redshift cluster
def create_or_get_redshift_cluster(cluster_name: str, db_name: str, db_username: str, db_password: str, role_name: str) -> dict:
   """Create a Redshift cluster on Postgres. Redshift role is already created and ready to be attached.
   """
   redshift = boto3.client('redshift')

   try:
      redshift_role = boto3.resource('iam').Role(role_name)

      cluster = redshift.create_cluster(
         ClusterIdentifier=cluster_name,
         DBName=db_name, 
         MasterUsername=db_username,
         MasterUserPassword=db_password,
         ClusterType='single-node',
         NodeType='dc2.large',
         IamRoles=[redshift_role.arn],
         DefaultIamRoleArn=redshift_role.arn
      )
      return cluster['Cluster']
   except ClientError as error:
      # ClusterAlreadyExists
      logging.error(error)
      cluster = redshift.describe_clusters(ClusterIdentifier=cluster_name)
      return cluster['Clusters'][0]

   