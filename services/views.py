from django.shortcuts import render
from django.views import View, generic
import pickle
import numpy as np
import pandas as pd
from .choices import team_choices
from google.cloud import storage
import tweepy
from textblob import TextBlob
import re
from .google import Create_Service
import os
import io
from googleapiclient.http import MediaIoBaseDownload
import requests


CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
DRIVE_URL = 'https://docs.google.com/uc?export=download'

#That port is already in use error fix
# kill -9 $(ps -A | grep python | awk '{print $1}')\

#enable google drive 
#In Auth2 credentials --> redirect_uri: http://localhost:8080/
#test user should be added to grant access

service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)


def drive_api():
    
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


drive_api()
   

    

def model_loaded():
    with open('saved.pkl', 'rb') as file:
        data = pickle.load(file)
    return data



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


def CleanTxt(text):
    text = re.sub(r'@[A-Za-z0-9]+', '', text) #removes @mentions
    text = re.sub(r'#', '', text) #removes the #
    text = re.sub(r'RT[\s]+', '', text) #removes RT
    text = re.sub(r':', '', text)
    text = re.sub(r'https?:\/\/\S+', '', text) #removes the hyperlink

    return text


def getPolar(text):
    return TextBlob(text).sentiment.polarity


class PredictView(View):
    def get(self, request, *args, **kwargs):
        context = {'teams': team_choices}
        return render(request, 'templates/predict.html', context)

    def post(self, request, *args, **kwargs):
        data = model_loaded()

        model = data['model']
        le_home_team = data['le_home_team']
        le_away_team = data['le_away_team']

        api = twitter_api()

        home_team = request.POST.get("home")
        away_team = request.POST.get("away")

        home_twt = api.search_tweets(q=home_team, count=100000, lang='en', tweet_mode='extended')
        away_twt = api.search_tweets(q=away_team, count=100000, lang='en', tweet_mode='extended')

        df_home = pd.DataFrame([tweet.full_text for tweet in home_twt], columns=['Tweets'])
        df_away = pd.DataFrame([tweet.full_text for tweet in away_twt], columns=['Tweets'])

        df_home['Polarity'] = df_home['Tweets'].apply(getPolar)
        df_away['Polarity'] = df_away['Tweets'].apply(getPolar)

        home_polar = np.mean(df_home['Polarity'].values)
        away_polar = np.mean(df_away['Polarity'].values)

        if home_polar >= away_polar:
            X = np.array([[home_team, away_team]])
        else:
            X = np.array([[away_team, home_team]])

        X1 = X[0].copy()

        X[:,0] = le_home_team.transform(X[:,0])
        X[:,1] = le_away_team.transform(X[:,1])
        
        X = X.astype('float')

        y_pred = model.predict(X)

        if y_pred == 2:
            status = X1[0] + ' wins'
        elif y_pred == 1:
            status = 'Match Draws'
        elif y_pred == 0:
            status = X1[1] + ' wins'

        probs = model.predict_proba(X)[0]

        print(X1)


        context = {
                    'teams': team_choices, 
                    'status': status,
                    'probs': probs,
                    'home': str(X1[0]),
                    'away': str(X1[1])
                    }
                    
        return render(request, 'templates/predict.html', context)
