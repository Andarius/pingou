import os

NB_WORKERS = os.getenv('NB_WORKERS', 1)
PG_TABLE = os.getenv('PG_TABLE', 'monitoring.nginx_logs')

RELEASE_STAGE = os.getenv('RELEASE_STAGE', 'development')
BUGSNAG_ID = (os.environ['BUGSNAG_ID']
              if RELEASE_STAGE == 'production'
              else os.getenv('BUGSNAG_ID'))
