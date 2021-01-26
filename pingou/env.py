import os

RELEASE_STAGE = os.getenv('RELEASE_STAGE', 'development')
BUGSNAG_ID = (os.environ['BUGSNAG_ID']
              if RELEASE_STAGE == 'production'
              else os.getenv('BUGSNAG_ID'))
