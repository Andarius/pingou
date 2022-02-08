import os

NB_WORKERS = os.getenv('NB_WORKERS', 1)
PG_TABLE = os.getenv('PG_TABLE', 'monitoring.nginx_logs')

RELEASE_STAGE = os.getenv('RELEASE_STAGE', 'development')
BUGSNAG_ID = (os.environ['BUGSNAG_ID']
              if RELEASE_STAGE == 'production'
              else os.getenv('BUGSNAG_ID'))

PG_DB = os.getenv('PG_DB', 'postgres')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'postgres')
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = int(os.getenv('PG_PORT', '5432'))
