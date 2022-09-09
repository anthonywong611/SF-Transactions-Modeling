import boto3
from botocore.exceptions import ClientError


# Delete the Redshift Cluster
def delete_redshift_cluster(name: str) -> dict:
   """
   """
   try:
      redshift = boto3.client('redshift')
      response = redshift.delete_cluster(
         ClusterIdentifier=name,
         SkipFinalClusterSnapshot=True
      )
      return response
   except ClientError as error:
      redshift_error = error.response["Error"]
      print(f'{redshift_error["Code"]}: {redshift_error["Message"]}')

# Delete the Security Group


# Delete the Redshift Role


# Delete the SFTP Server



# Delete the Transfer Family Role


# Delete the S3 Policy for Transfer Family


# Empty and Delete the S3 Bucket