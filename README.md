# San_Francisco_Financial_Modeling

Challenge: 
- Not sure about the relationship between a column and its corresponding code column. 
- Doubted that it should be a one-to-one relationship but there are columns that clearly have multiple codes identified with it. 
- Sent an email to ask the dataset owner, but still get no reply yet.
- Decided that it should be a many-to-one relationship.

ETL Steps:
- For each column and their corresponding code column:
   - handle null values
   - check many-to-one relationship
   - transform the code column if necessary
- Load the transformed data into database
   - create star schema
   - load into data warehouse

Local Step:
1. Gnerate a SSH key pair (public & private)

Boto3 Step:
1. Set up an S3 bucket 
2. Create IAM roles
   2.1 - Create an IAM policy for services to call S3 on user's behalf
      2.1 - Specify the target S3 bucket in the policy
   2.2 - Create a Transfer Family role and attach the policy to it
      2.2.1 - Update the trust relationship with extra conditions 
3. Set up an SFTP server with Transfer Family
   3.1 - Create (if not exists) a CloudWatch role
   3.2 - Create a user to attach to the server
      3.2.1 - Attach the Transfer Family role to the user
      3.2.2 - Submit the SSH public key content
5. Set up a Redshift cluster

- Only need a Transfer Family role attached with a access policy that allows it to call S3 on the user's behalf