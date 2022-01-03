import os
import io
from googleapiclient.http import MediaIoBaseDownload
import requests
import tweepy
import re
from textblob import TextBlob
import pandas as pd
from bs4 import BeautifulSoup
from bs4 import BeautifulSoup




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
        os.mkdir('data')
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

        with open(os.path.join('data', file_name), 'wb') as f:
            f.write(fh.read())
            f.close()



def twitter_api():
    login = pd.read_csv('login.csv')

    cons_key = login['Keys'][0]
    cons_key_sec = login['Keys'][1]
    acc_token = login['Keys'][2]
    acc_token_sec = login['Keys'][3]

    authenticate = tweepy.OAuthHandler(cons_key, cons_key_sec)

    authenticate.set_access_token(acc_token, acc_token_sec)

    api = tweepy.API(authenticate, wait_on_rate_limit=True)

    return api 



def clean_txt(text):
    text = re.sub(r'@[A-Za-z0-9]+', '', text) #removes @mentions
    text = re.sub(r'#', '', text) #removes the #
    text = re.sub(r'RT[\s]+', '', text) #removes RT
    text = re.sub(r':', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text) #removes the hyperlink

    return text


def get_polar(text):
    return TextBlob(text).sentiment.polarity


def get_data(source):
    soup = BeautifulSoup(source, 'lxml')
    list_urls = []
    download_url = 'https://football-data.co.uk/'
    for link in soup.find_all('a'):
        if link.get('href').endswith('E0.csv'):
            file = link.get('href')
            list_urls.append(download_url + file)
    try:
        os.remove('services/data')
    except:
        pass
    os.mkdir('services/data')

    for i in range(15):
        with open((os.path.join('services/data','data'+str(i)+'.csv')), 'wb') as f:
            for chunk in requests.get(list_urls[i]).iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
