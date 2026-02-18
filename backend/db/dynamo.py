import os
from functools import lru_cache

import boto3
from dotenv import load_dotenv

load_dotenv()  # lee .env (local)

TABLE_NAME = os.getenv("TABLE_NAME", "EventUsers")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

@lru_cache
def get_table():
    ddb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return ddb.Table(TABLE_NAME)