from celery import shared_task
from celery.utils.log import get_task_logger
from celery.schedules import crontab
from datetime import datetime
from .functions import get_data, save_data, get_data_set, save_model
import requests
from celery.utils.log import get_task_logger



logger = get_task_logger(__name__)

dataset = get_data_set()

#celery -A core worker -l info -B

@shared_task
def weekly_data_load():
    download_link = requests.get("https://football-data.co.uk/englandm.php").text
    logger.info("Loading data...")
    return get_data(download_link)


@shared_task
def weekly_data_save():
    logger.info("Saving data...")
    return save_data()


@shared_task
def weekly_model_save():
    logger.info("Saving prediction model...")
    return save_model(dataset)