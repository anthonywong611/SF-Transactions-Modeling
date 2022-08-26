import unittest
import boto3

from infrastructures import create_or_get_iam_policy
from infrastructures import create_or_get_iam_role
from infrastructures import attach_policies_to_iam_role


class TestIAMRole(unittest.TestCase):

   client = boto3.client('iam')
   role_name = 'S3TransferFamilyRole'
   policy_name = 'S3TrustPolicy'
   bucket_name = 'test-sftp-1290'
   
   def test_Create_Policy_For_Service_To_Work_With_S3_Bucket(self):

      policy = create_or_get_iam_policy(
         policy_name=self.policy_name, 
         bucket_name=self.bucket_name
      )
      response = self.client.get_policy(PolicyArn=policy['Policy']['Arn'])

      self.assertEqual(response['Policy']['PolicyName'], self.policy_name)

   def test_Create_Transfer_Family_Role(self):
      
      role = create_or_get_iam_role(
         role_name=self.role_name, 
         trust_entity='transfer'
      )

      response = self.client.get_role(
         RoleName=self.role_name
      )

      self.assertEqual(role.keys(), response.keys())
      self.assertEqual(role['Role']['RoleName'], self.role_name)
      self.assertEqual(response['Role']['RoleName'], self.role_name)
      self.assertEqual(response['Role']['RoleName'], role['Role']['RoleName'])

   def test_Attach_Managed_Policies_to_Role(self):

      policies = {
         'aws': ['IAMFullAccess', 'AmazonS3FullAccess', 'AWSTransferConsoleFullAccess'],
         'customer': [self.policy_name] 
      }

      attach_policies_to_iam_role(policies=policies, role_name=self.role_name)

      S3TransferRole = boto3.resource('iam').Role(self.role_name)
      attached_policies = list(S3TransferRole.attached_policies.all())

      self.assertGreater(len(attached_policies), 1)
