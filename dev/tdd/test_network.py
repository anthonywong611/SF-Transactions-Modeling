import unittest

from infrastructures import create_or_get_security_group


class TestNetworkTrafficRouting(unittest.TestCase):

   name = 'RedshiftConnector'

   def test_Security_Group_Creation(self):

      response = create_or_get_security_group(group_name=self.name)

      self.assertIn('GroupId', response)
      self.assertIn('IpPermissions', response)

      traffic_rule = response['IpPermissions'][0]

      self.assertEqual(traffic_rule['FromPort'], 5439)
      self.assertEqual(traffic_rule['ToPort'], 5439)
      self.assertEqual(traffic_rule['IpProtocol'], 'tcp')
   