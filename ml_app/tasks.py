from celery import shared_task
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from datetime import datetime
from .functions import get_data, save_data
import requests
from celery.utils.log import get_task_logger



logger = get_task_logger(__name__)

#celery -A core worker -l info -B

@shared_task
def weekly_data_load():
    download_link = requests.get("https://football-data.co.uk/englandm.php").text
    logger.info("Loading data...")
    return get_data(download_link)


@shared_task
def weekly_data_save():
    logger.info("SAving data...")
    return save_data()