import boto3

from configparser import ConfigParser
from botocore.exceptions import ClientError


config = ConfigParser()
config.read_file(open('params.cfg'))

# -----------Envrionment Variables----------- #
# S3
bucket_name = config['S3']['bucket_name']
# Transfer Family
transfer_role = config['Transfer Family']['transfer_role']
# Redshift
redshift_cluster = config['Redshift']['redshift_cluster']
security_group_name = config['Redshift']['security_group_name']
redshift_role = config['Redshift']['redshift_role']
# ------------------------------------------- #

def delete_redshift_cluster(name: str) -> None:
   """Delte the Redshift cluster.
   """
   try:
      redshift = boto3.client('redshift')
      redshift.delete_cluster(
         ClusterIdentifier=name,
         SkipFinalClusterSnapshot=True
      )
      # Wait for the cluster deletion to complete
      redshift.get_waiter('cluster_deleted').wait(ClusterIdentifier=redshift_cluster)
   except ClientError as error:
      redshift_error = error.response["Error"]
      print(f'{redshift_error["Code"]}: {redshift_error["Message"]}')

def delete_security_group(name: str) -> None:
   """Delete the security group.
   """
   try:
      ec2 = boto3.client('ec2')
      ec2.delete_security_group(GroupName=name)
   except ClientError as error:
      security_error = error.response["Error"]
      print(f'{security_error["Code"]}: {security_error["Message"]}')

def delete_iam_role(name: str) -> None:
   """Detach all managed policies from the IAM role.
   """
   try:
      # Detach all attached policies
      role = boto3.resource('iam').Role(name)
      for policy in role.attached_policies.all():
         role.detach_policy(PolicyArn=policy.arn)
      # Delete the role
      role.delete()
   except ClientError as error:
      role_error = error.response["Error"]
      print(f'{role_error["Code"]}: {role_error["Message"]}')

def delete_servers() -> None:
   """Delete the SFTP server. Return the server ID.
   """
   try:
      transfer = boto3.client('transfer')
      for server in transfer.list_servers()['Servers']:
         server_id = server['ServerId']
         # Delete the server
         transfer.delete_server(ServerId=server_id)
   except ClientError as error:
      server_error = error.response["Error"]
      print(f'{server_error["Code"]}: {server_error["Message"]}')

def delete_s3_policy(bucket: str, service: str) -> None:
   """Delete the S3 bucket policy associated with the service.

   Service is either 'transfer' or 'redshift'.
   """
   iam = boto3.client('iam')
   customer_managed = iam.list_policies(Scope='Local')
   for customer_managed_policy in customer_managed['Policies']:
      policy = customer_managed_policy['PolicyName'].lower()
      if service in policy and bucket in policy:
         policy_arn = customer_managed_policy['Arn']
         # Delete the S3 policy
         iam.delete_policy(PolicyArn=policy_arn)

def delete_s3_bucket(name: str) -> None:
   """Empty and delete the S3 bucket. 
   """
   try:
      bucket = boto3.resource('s3').Bucket(name)
      # Empty all objects in the bucket
      bucket.objects.delete()
      # Delete the bucket
      bucket.delete()
   except ClientError as error:
      s3_error = error.response["Error"]
      print(f'{s3_error["Code"]}: {s3_error["Message"]}')

def main():
   # 1. Delete the Redshift cluster
   delete_redshift_cluster(name=redshift_cluster)
   # 2. Delete the security group
   delete_security_group(name=security_group_name)
   # 3. Delete the SFTP server and its user
   delete_servers()
   # 4. Delete the Transfer Family and Redshift IAM roles
   delete_iam_role(name=transfer_role)
   delete_iam_role(name=redshift_role)
   # 5. Delete the S3 policies for Transfer Family and Redshift
   delete_s3_policy(bucket=bucket_name, service='transfer')
   delete_s3_policy(bucket=bucket_name, service='redshift')
   # 6. Delete the S3 bucket
   delete_s3_bucket(name=bucket_name)

if __name__ == '__main__':
   main()