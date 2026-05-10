import sys
import os
sys.path.insert(0, '/app')
os.chdir('/app')

from tasks.celery_app import celery_app

if __name__ == '__main__':
    celery_app.start()
