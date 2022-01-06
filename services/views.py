from django.shortcuts import render
from django.views import View, generic
import pickle
import numpy as np
import pandas as pd
from .choices import team_choices
import re
import os
import requests
from .functions import twitter_api, clean_txt, get_polar 
from ml_app.functions import drive_api_upload



#That port is already in use error fix
# kill -9 $(ps -A | grep python | awk '{print $1}')

#enable google drive (APIs and service --> Library)
#In Auth2 credentials --> redirect_uri: http://localhost:8080/
#test user should be added to grant access
# For production --> OAuth consent screen --> Publishing status
# "Publish app"
# OAuth consent screen --> Edit App --> add scope

# from services.google import Create_Service

# CLIENT_SECRET_FILE = 'client_secret.json'
# API_NAME = 'drive'
# API_VERSION = 'v3'
# SCOPES = ['https://www.googleapis.com/auth/drive']


# drive_service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)


# drive_api_upload(drive_service)


def model_loaded():
    with open('saved.pkl', 'rb') as _file:
        data = pickle.load(_file)
    return data


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

        df_home['Tweets'] = df_home['Tweets'].apply(clean_txt)
        df_away['Tweets'] = df_away['Tweets'].apply(clean_txt)

        df_home['Polarity'] = df_home['Tweets'].apply(get_polar)
        df_away['Polarity'] = df_away['Tweets'].apply(get_polar)

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
