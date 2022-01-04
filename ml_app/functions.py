from bs4 import BeautifulSoup
import os
import shutil
import io
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import requests

from services.google import Create_Service

CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']


drive_service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)



def drive_api_download(service):
    # https://drive.google.com/drive/folders/1naSzPiBscG81IK2wgvwqrEG0zVqVqqTo?usp=sharing
    folder_id = '1naSzPiBscG81IK2wgvwqrEG0zVqVqqTo'
    query = f"parents = '{folder_id}'"

    response = service.files().list(q=query).execute()

    files = response.get('files')
    nextPageToken = response.get('nextPageToken')

    while nextPageToken:
        response = service.files().list(q=query, pageToken=nextPageToken).execute()
        files.extend(response.get('files'))
        nextPageToken = response.get('nextPageToken')

    try:
        os.makedirs('ml_app/data')
    except:
        return False

    for file in files:
        file_id = file['id']
        file_name = file['name']

        request = service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fd=fh, request=request)

        done = False

        while not done:
            status, done = downloader.next_chunk()
            print('Download progrss {0}'.format(status.progress()*100))

        fh.seek(0)

        with open(os.path.join('ml_app/data', file_name), 'wb') as f:
            f.write(fh.read())
            f.close()


#This funtion is not working
def drive_api_upload(service):
    folder_id = '1naSzPiBscG81IK2wgvwqrEG0zVqVqqTo'
    path = 'ml_app/data'
    files = []
    path = 'ml_app/data'
    for file in os.listdir(path):
        files.append(os.path.basename(file))

    for file in files:
        file_path = os.path.join(path, file)
        file_metadata = {
        'name': file,
        'parents': [folder_id]
        }

        media = MediaIoBaseUpload(file_path, mimetype='text/csv')

        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
            ).execute()



def get_data(source):
    soup = BeautifulSoup(source, 'lxml')
    list_urls = []
    download_url = 'https://football-data.co.uk/'
    for link in soup.find_all('a'):
        file = link.get('href')
        if file.endswith('E0.csv'):
            list_urls.append(download_url + file)
    try:
        shutil.rmtree('ml_app/data')
        os.makedirs('ml_app/data')

    except OSError:
        os.makedirs('ml_app/data')

    for i in range(15):
        file_path = 'ml_app/data'
        file_name = 'data'+str(i)+'.csv'
        with open((os.path.join(file_path, file_name)), 'wb') as f:
            for chunk in requests.get(list_urls[i]).iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return "Successfully loaded data."



