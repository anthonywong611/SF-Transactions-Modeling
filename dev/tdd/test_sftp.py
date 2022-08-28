import unittest

from infrastructures import create_or_get_sftp_server, create_or_get_sftp_user


class TestTransferFamily(unittest.TestCase):

   def test_sftp_server_creation(self):

      # should return a dictionary of server ID
      sftp_server = create_or_get_sftp_server(
         protocol='SFTP',
         provider='SERVICE_MANAGED',
         endpoint='PUBLIC',
         domain='S3'
      )

      self.assertIsInstance(sftp_server, dict)
      self.assertIn('ServerId', sftp_server.keys())

   def test_sftp_user_creation(self):

      username = 'anthony'
      role_name = 'S3TransferFamilyRole'
      server_id = 's-f383928afd1e47c58'
      bucket_name = 'test-sftp-1290'

      sftp_user = create_or_get_sftp_user(
         username=username,
         role_name=role_name,
         server_id=server_id,
         home_directory=bucket_name
      )

      self.assertIsInstance(sftp_user, dict)
      self.assertIn('ServerId', sftp_user.keys())
      self.assertIn('UserName', sftp_user.keys())
      self.assertEqual(sftp_user['ServerId'], server_id)
      self.assertEqual(sftp_user['UserName'], username)

      