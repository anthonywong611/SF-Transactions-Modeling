# San_Francisco_Financial_Modeling

Challenge: 
- Not sure about the relationship between a column and its corresponding code column. 
- Doubted that it should be a one-to-one relationship but there are columns that clearly have multiple codes identified with it. 
- Sent an email to ask the dataset owner, but still get no reply yet.
- Decided that it should be a many-to-one relationship.

Thought Organization:
- Only need a Transfer Family role attached with a access policy that allows it to call S3 on the user's behalf
- Server host key doesn't actually show changes after being updated with ssh private key (keep in mind!)

ETL Steps:
1 For each column and their corresponding code column:
   1.1 handle null values
   1.2 check many-to-one relationship
   1.3 transform the code column if necessary

-------------------------------------------------------------------------------

Local Step:
1. Generate a SSH key pair (public & private)
2. Scrape the data from official website
3. Configure AWS account on CLI
   3.1 - Store access key on local ./aws folder
4. Transfer the file to S3 through SFTP (after Boto3 step 4 is completed)
   - SFTP server's endpoint
   - SSH private key

Boto3 Step:
1. Set up an S3 bucket 
2. Create IAM role
   2.1 - Create an IAM policy for services to call S3 on user's behalf
      2.1.1 - Specify the target S3 bucket in the policy
   2.2 - Create a Transfer Family role and attach the policy to it
      2.2.2 - Establish a trust relationship between AWS and Transfer Family
      2.2.1 - Attach managed policies for Transfer Family to work with S3 
3. Set up an SFTP server with Transfer Family
   3.1 - Store data in S3 as domain
   3.2 - Submit the SSH private key content
4. Create a user to attach to the server
   4.1 - Attach the Transfer Family role to the user
   4.2 - Submit the SSH public key content
5. Set up a Redshift cluster
   5.1 - Attach the Redshift role to the cluster
      5.1.1 - Policy for working with S3 bucket 
      5.1.2 - Redshift full access
   5.2 - Create a security group that routes inbound traffic to port 5439
   
Cloud Steps:
1. Set up star schema in the Redshift DW
2. Copy the transformed data from S3 into Redshift 
3. Create report 
   3.1 - Aggregation result
   3.2 - Dashboard for features

--------------------------------------------

Production:
1. Infrastructure (Boto3)
   1.1 - Environment variables
      1.1.1 - AWS account ID
      1.1.2 - Region Name
      1.1.3 - S3 Bucket Name
      1.1.4 - Transfer Family Role Name
      1.1.5 - Transfer Family S3 Policy Name
      1.1.6 - Transfer Family AWS Permission Policies
      1.1.7 - SFTP Server Username
      1.1.8 - Redshift Role Name
      1.1.9 - Redshift S3 Policy Name
      1.1.10 - Redshift Cluster Name
      1.1.11 - Redshift Database Name
      1.1.12 - Redshift Database Username
      1.1.13 - Redshift Database Password
2. Initial Load (boto3)
   2.1 - Create a report schema in Redshift database
   2.2 - Define dimensional tables
      2.2.1 - copy dimensional data from S3 over to Redshift
   2.3 - Define fact table
      2.3.1 - copy fact data from S3 over to Redshift

-----------------------------------------------------------

Clean Up:
1. Delete Redshift Cluster
2. Delete Security Group
3. Delete the Redshift Role
4. Delete the SFTP Server
5. Delete the Transfer Family Role
6. Delete the S3 Policy for Transfer Family
7. Empty and Delete the S3 bucket

-----------------------------------------------
Room for Improvement:
1. Set up Glue catalog to store tables metadata
   1.1 - For incremental loading
   1.2 - For sharing data with other users
2. Set up an identity provider like Otka for better management
