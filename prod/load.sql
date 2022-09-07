copy '<schema>'.'<table_name>' 
from 's3://<bucket_name>/<file_name>.csv'
iam_role 'arn:aws:iam::<account_id>:role/<redshift_role_name>'
csv ignoreheader 1 
region '<region>';