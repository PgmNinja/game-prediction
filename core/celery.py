from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
app = Celery('core')
app.conf.enable_utc = False
app.conf.update(timezone = 'Asia/Kolkata')
app.config_from_object('django.conf:settings', namespace='CELERY')


app.conf.beat_schedule = {
    'load_data_periodically': {
        'task': 'ml_app.tasks.weekly_data_load',
        'schedule': crontab(hour=6, minute=0, day_of_week=5)
    },

    'save_data_periodically': {
        'task': 'ml_app.tasks.weekly_data_save',
        'schedule': crontab(hour=6, minute=5, day_of_week=5)
    },

    'save_model_periodically': {
        'task': 'ml_app.tasks.weekly_model_save',
        'schedule': crontab(hour=6, minute=10, day_of_week=5)
    }

}


app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'request:{self.request!r}')
