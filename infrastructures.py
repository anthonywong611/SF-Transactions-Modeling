import boto3
import logging
import json

from botocore.exceptions import ClientError
from configparser import ConfigParser
from typing import Optional, Dict, List
from parse_policy import *


config = ConfigParser()
config.read_file(open('params.cfg'))

# -----------Envrionment Variables----------- #
# Account Info
account_id = config['Account Info']['account_id']
region = config['Account Info']['region']
# S3
bucket_name = config['S3']['bucket_name']
# Transfer Family
transfer_role = config['Transfer Family']['transfer_role']
transfer_s3_policy = config['Transfer Family']['transfer_s3_policy_prefix'] + bucket_name
transfer_aws_permissions = [
   config['Transfer Family']['aws_permission_1'], 
   config['Transfer Family']['aws_permission_2'], 
   config['Transfer Family']['aws_permission_3']
]
sftp_server_username = config['Transfer Family']['sftp_server_username']
# Redshift
security_group_name = config['Redshift']['security_group_name']
redshift_role = config['Redshift']['redshift_role']
redshift_s3_policy = config['Redshift']['redshift_s3_policy_prefix'] + bucket_name
redshift_cluster = config['Redshift']['redshift_cluster']
redshift_db_name = config['Redshift']['redshift_db_name']
redshift_db_username = config['Redshift']['redshift_db_username']
redshift_db_password = config['Redshift']['redshift_db_password']
# ------------------------------------------- #

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
         # Establish a trust relationship between AWS and Transfer Family
         AssumeRolePolicyDocument=trust_policy_document
      )
      return role
   except ClientError as error:
      logging.error(error)
      # Role already created...
      # EntityAlreadyExists exception
      return iam.get_role(RoleName=role_name)

def create_or_get_sftp_server() -> dict:
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
         Protocols=['SFTP'],
         IdentityProviderType='SERVICE_MANAGED',
         EndpointType='PUBLIC',
         Domain='S3',
         # submit the ssh private key content for user authentication
         HostKey=ssh_private_key_content
      )

      return server
   except ClientError as error:
      logging.error(error)

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

      policy_arn = f'arn:aws:iam::{account_id}:policy/{s3_policy_name}'
      # Wait for the role and the policy to become available
      iam.get_waiter('role_exists').wait(RoleName=role_name)
      iam.get_waiter('policy_exists').wait(PolicyArn=policy_arn)

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
   
def create_or_get_redshift_cluster(cluster_name: str, db_name: str, db_username: str, db_password: str, security_group: dict, role_name: str) -> dict:
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
         VpcSecurityGroupIds=[security_group['GroupId']],
         IamRoles=[redshift_role.arn],
         DefaultIamRoleArn=redshift_role.arn
      )
      return cluster['Cluster']
   except ClientError as error:
      # ClusterAlreadyExists
      logging.error(error)
      cluster = redshift.describe_clusters(ClusterIdentifier=cluster_name)
      return cluster['Clusters'][0]

def main() -> None:
   """Set up an S3 bucket, an SFTP server with a user, and a Redshift cluster.
   """
   # 1. Set up an S3 bucket 
   create_or_get_s3_bucket(name=bucket_name, region=region)
   # 2.1 Set up an IAM role for Transfer Family
   create_or_get_transfer_family_role(role_name=transfer_role)
   # Wait for S3 bucket to become available
   boto3.client('s3').get_waiter('bucket_exists').wait(Bucket=bucket_name)
   # 2.2 Set up the S3 policy for Transfer Family to call the S3 bucket on user's behalf
   s3_policy = create_or_get_s3_policy(
      policy_name=transfer_s3_policy, 
      bucket_name=bucket_name, 
      service='transfer'
   )
   # Wait for policy to become available
   boto3.client('iam').get_waiter('policy_exists').wait(PolicyArn=s3_policy['Policy']['Arn'])
   # Wait for Transfer Family role to become available
   boto3.client('iam').get_waiter('role_exists').wait(RoleName=transfer_role)
   # 2.3 Attach managed policies to the Transfer Family role 
   transfer_permissions = {'aws': transfer_aws_permissions, 'customer': [transfer_s3_policy]}
   attach_policies_to_iam_role(
      policies=transfer_permissions, 
      role_name=transfer_role
   )
   # 3. Set up an SFTP server with Transfer Family
   sftp_server = create_or_get_sftp_server()
   # Wait for the server to become available online
   boto3.client('transfer').get_waiter('server_online').wait(ServerId=sftp_server['ServerId'])
   # 4. Create a user to attach to the server
   create_or_get_sftp_user(
      username=sftp_server_username, 
      role_name=transfer_role, 
      server_id=sftp_server['ServerId'], 
      home_directory=bucket_name
   )
   # 5.1 Set up a security group to route traffic to Redshift
   traffic_group = create_or_get_security_group(group_name=security_group_name)
   # 5.2 Set up an IAM role for Redshift
   create_or_get_redshift_role(
      role_name=redshift_role, 
      s3_policy_name=redshift_s3_policy, 
      s3_bucket=bucket_name
   )
   # No need to Wait for the Redshift role to become available since that is accounted for during role creation
   # 5.3 Create a Redshift cluster with the Redshift role attached
   create_or_get_redshift_cluster(
      cluster_name=redshift_cluster, 
      db_name=redshift_db_name, 
      db_username=redshift_db_username, 
      db_password=redshift_db_password, 
      security_group=traffic_group, 
      role_name=redshift_role
   )
   # Wait for the cluster to become available
   boto3.client('redshift').get_waiter('cluster_available').wait(ClusterIdentifier=redshift_cluster)
   # Print the SFTP server Endpoint
   print(f'SFTP Server Endpoint: {sftp_server["ServerId"]}.server.transfer.{region}.amazonaws.com')

if __name__ == '__main__':
   main()