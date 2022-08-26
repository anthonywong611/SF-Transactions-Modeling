import unittest
import boto3

from infrastructures import create_or_get_s3_bucket

class TestS3Bucket(unittest.TestCase):

   def test_bucket_creation(self):
      bucket_name = 'test-sftp-1290'
      create_or_get_s3_bucket(name=bucket_name, region='ca-central-1')
      
      client = boto3.client('s3')
      responses = client.list_buckets()['Buckets']
      buckets = [response['Name'] for response in responses]
      self.assertIn(bucket_name, buckets)