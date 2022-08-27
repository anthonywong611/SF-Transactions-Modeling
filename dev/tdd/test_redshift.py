import boto3
import unittest

from infrastructures import create_or_get_redshift_cluster


class TestRedshiftCluster(unittest.TestCase):
   
   def test_Redshift_Cluster_Creation(self):

      cluster_name = 'transaction-dw'
      db_name = 'san_francisco'
      db_username = 'awsuser'
      db_password = 'Knpweoak3fu2p'
      role_name = 'S3RedshiftRole'

      cluster = create_or_get_redshift_cluster(
         cluster_name=cluster_name,
         db_name=db_name,
         db_username=db_username,
         db_password=db_password,
         role_name=role_name
      )

      role_arn = f'arn:aws:iam::649363699007:role/{role_name}'

      self.assertIsInstance(cluster, dict)
      # Test cluster configurations
      self.assertEqual(cluster['ClusterIdentifier'], cluster_name)
      # self.assertEqual(cluster['PendingModifiedValues']['ClusterType'], 'single-node')
      self.assertEqual(cluster['NodeType'], 'dc2.large')
      # Test database configurations
      self.assertEqual(cluster['DBName'], db_name)
      self.assertEqual(cluster['MasterUsername'], db_username)
      # Test IAM role configurations
      self.assertEqual(cluster['DefaultIamRoleArn'], role_arn)

      
