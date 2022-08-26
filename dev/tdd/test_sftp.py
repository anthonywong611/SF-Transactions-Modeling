import unittest
import boto3

from boto3.exceptions import ClientError

class TestTransferFamily(unittest.TestCase):

   client = boto3.client('transfer')

   def test_sftp_server_creation(self):
      pass