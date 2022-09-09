from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, url
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.types import Integer, Numeric, String
from sqlalchemy.schema import MetaData
from sqlalchemy.exc import ProgrammingError


account_id = '649363699007'
region = 'ca-central-1'
bucket_name = 'sf-transactions-12345'
redshift_role = 'S3RedshiftRole'
redshift_cluster = 'transactions-dw'
db_name = 'san_francisco'
db_username = 'anthony'
db_password = 'Huangjianen611?'
host = f'{redshift_cluster}.c2eeppdorvki.{region}.redshift.amazonaws.com'


def redshift_connection(host: str, db_name: str, username: str, password: str, port: int = 5439) -> Engine:
   """
   """
   connection_url = url.URL.create(
      drivername='redshift+redshift_connector', 
      host=host, 
      port=port,
      database=db_name,
      username=username, 
      password=password
   )
   return create_engine(url=connection_url)

def create_schema(name: str, engine: Engine) -> None:
   """Create a schema called <name>.
   """
   with engine.connect() as conn:
      conn.execute(f"CREATE SCHEMA IF NOT EXISTS {name};")

def create_program_dimension(schema: MetaData, engine: Engine) -> None:
   """Create the Program dimensional table. 
   """
   try:
      program = Table('program', schema,
         Column('program_id', Integer, primary_key=True),
         Column('program', String(100), nullable=False),
         Column('program_code', String(50), nullable=False),
         Column('department', String(100), nullable=False),
         Column('department_code', String(50), nullable=False),
         Column('organization_group', String(100), nullable=False),
         Column('organization_group_code', String(50), nullable=False),
         Column('related_govt_units', String(10), nullable=False),
         keep_existing=True
      )
      program.create(engine, checkfirst=True)
   except ProgrammingError as error:
      print(error)

def create_type_dimension(schema: MetaData, engine: Engine) -> None:
   """Create the Type dimensional table.
   """
   try:
      type = Table('type', schema,
         Column('type_id', Integer, primary_key=True),
         Column('sub_object', String(100), nullable=False),
         Column('sub_object_code', String(50), nullable=False),
         Column('object', String(100), nullable=False),
         Column('object_code', String(50), nullable=False),
         Column('character', String(100), nullable=False),
         Column('character_code', String(50), nullable=False),
         keep_existing=True
      )
      type.create(engine, checkfirst=True)
   except ProgrammingError as error:
      print(error)

def create_fund_dimension(schema: MetaData, engine: Engine) -> None:
   """Create the Fund dimensional table.
   """
   try:
      fund = Table('fund', schema,
         Column('fund_id', Integer, primary_key=True),
         Column('fund_category', String(100), nullable=False),
         Column('fund_category_code', String(50), nullable=False),
         Column('fund', String(100), nullable=False),
         Column('fund_code', String(50), nullable=False),
         Column('fund_type', String(100), nullable=False),
         Column('fund_type_code', String(50), nullable=False),
         keep_existing=True 
      )
      fund.create(engine, checkfirst=True)
   except ProgrammingError as error:
      print(error)
   
def create_finance_dimension(schema: MetaData, engine: Engine) -> None:
   """Create the Finance dimensional table.
   """
   try:
      finance = Table('finance', schema,
         Column('finance_id', Integer, primary_key=True),
         Column('revenue_or_spending', String(20), nullable=False),
         keep_existing=True 
      )
      finance.create(engine, checkfirst=True)
   except ProgrammingError as error:
      print(error)
   
def create_transaction_fact(schema: MetaData, engine: Engine) -> None:
   """Create the transaction fact table.
   """
   try:
      transaction = Table('transaction', schema,
         Column('transaction_id', Integer, primary_key=True),
         Column('fiscal_year', Integer, nullable=False),
         Column('program_id', Integer, ForeignKey('program.program_id'), nullable=False),
         Column('type_id', Integer, ForeignKey('type.type_id'), nullable=False),
         Column('fund_id', Integer, ForeignKey('fund.fund_id'), nullable=False),
         Column('finance_id', Integer, ForeignKey('finance.finance_id'), nullable=False),
         Column('amount', Numeric(20, 2), nullable=False),
         keep_existing=True
      )
      transaction.create(engine, checkfirst=True)
   except ProgrammingError as error:
      print(error)

def load_table(name: str, schema: str, engine: Engine) -> None:
   """Insert data from S3 bucket into the table.
   """
   stmt = "COPY {table} FROM '{s3}' iam_role '{role_arn}' csv ignoreheader 1;".format(
      table=f'{schema}.{name}', 
      s3=f's3://{bucket_name}/{name}.csv', 
      role_arn=f'arn:aws:iam::{account_id}:role/{redshift_role}', 
      region=region
   )

   engine.execute(text(stmt).execution_options(autocommit=True))

def main() -> None:
   
   # 0. Create a connection instance
   engine = redshift_connection(
      host=host, db_name=db_name, 
      username=db_username, password=db_password
   )

   # 1. Create a REPORT schema
   schema = 'report'
   report = MetaData(schema=schema)

   create_schema(name=schema, engine=engine)

   # 2. Create Dimensional Tables
   create_program_dimension(schema=report, engine=engine)
   create_type_dimension(schema=report, engine=engine)
   create_fund_dimension(schema=report, engine=engine)
   create_finance_dimension(schema=report, engine=engine)

   # 3. Create Transaction Fact Table
   create_transaction_fact(schema=report, engine=engine)

   # 4. Load Dimensional Tables
   load_table(name='program', schema=schema, engine=engine)
   load_table(name='type', schema=schema, engine=engine)
   load_table(name='fund', schema=schema, engine=engine)
   load_table(name='finance', schema=schema, engine=engine)

   # 5. Load Fact Table
   load_table(name='transaction', schema=schema, engine=engine)

   engine.dispose()


if __name__ == '__main__':

   main()
   
   
   
