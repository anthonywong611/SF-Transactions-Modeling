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

