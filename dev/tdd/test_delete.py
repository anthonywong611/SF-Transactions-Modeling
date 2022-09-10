import unittest

from clean_up import delete_redshift_cluster


class TestInfrastructuresDeletion(unittest.TestCase):

   def test_Redshift_Cluster_Deletion(self):

      redshift_cluster = 'transactions-dw'

      response = delete_redshift_cluster(name=redshift_cluster)

   def test_Security_Group_Deletion(self):

      pass
      

