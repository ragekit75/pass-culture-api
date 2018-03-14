import os

BROWSER_URL = os.environ.get('BROWSER_URL', 'http://localhost:3000')
ENV = os.environ.get('ENV', 'dev')
IS_DEV = ENV == 'dev'

BEFORE_AFTER_LIMIT = 5
BLOB_SIZE = 20
