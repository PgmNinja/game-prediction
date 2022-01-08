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
from ml_app.functions import get_data_set 



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

        home_team = request.POST.get('home', None)
        away_team = request.POST.get('away', None)
        request.session['home'] = home_team
        request.session['away'] = away_team

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
        request.session['home_polar'] = home_polar
        request.session['away_polar'] = away_polar

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

        print(probs)

        context = {
                    'teams': team_choices, 
                    'status': status,
                    'probs': probs,
                    'home': str(X1[0]),
                    'away': str(X1[1])
                    }
                    
        return render(request, 'templates/predict.html', context)



class AnalysisView(View):
    def get(self, request, *args, **kwargs):
        data = get_data_set()
        home_team = request.session['home']
        away_team = request.session['away']
        home_polar = request.session['home_polar']*100
        away_polar = request.session['away_polar']*100

        home_team_df = pd.concat([data.loc[data['HomeTeam'] == home_team], data.loc[data['AwayTeam'] == home_team]])
        away_team_df = pd.concat([data.loc[data['HomeTeam'] == away_team], data.loc[data['AwayTeam'] == away_team]])

        df_head_to_head = pd.concat([data.loc[(data['HomeTeam'] == home_team) & (data['AwayTeam'] == away_team)], \
            data.loc[(data['HomeTeam'] == away_team) & (data['AwayTeam'] == home_team)]])

        home_stats = {}
        away_stats = {}

        home_team_win = 0
        away_team_win = 0

        for i in range(home_team_df.shape[0]):
            if (home_team_df['HomeTeam'].iloc[i] == home_team and home_team_df['Results'].iloc[i] == 2) or \
            (home_team_df['AwayTeam'].iloc[i] == home_team and home_team_df['Results'].iloc[i] == 0):
                if home_team_df['Year'].iloc[i] in home_stats:
                    home_stats[home_team_df['Year'].iloc[i]] += 1 
                else:
                    home_stats[home_team_df['Year'].iloc[i]] = 1

        for i in range(away_team_df.shape[0]):
            if (away_team_df['HomeTeam'].iloc[i] == away_team and away_team_df['Results'].iloc[i] == 2) or \
            (away_team_df['AwayTeam'].iloc[i] == away_team and away_team_df['Results'].iloc[i] == 0):
                if away_team_df['Year'].iloc[i] in away_stats:
                    away_stats[away_team_df['Year'].iloc[i]] += 1 
                else:
                    away_stats[away_team_df['Year'].iloc[i]] = 1


        for i in range(df_head_to_head.shape[0]):
            if ((df_head_to_head['HomeTeam'].iloc[i] == home_team) and (df_head_to_head['Results'].iloc[i] == 2)) or \
            ((df_head_to_head['AwayTeam'].iloc[i] == home_team) and (df_head_to_head['Results'].iloc[i] == 0)):
                home_team_win += 1

            if ((df_head_to_head['HomeTeam'].iloc[i] == away_team) and (df_head_to_head['Results'].iloc[i] == 2)) or \
            ((df_head_to_head['AwayTeam'].iloc[i] == away_team) and (df_head_to_head['Results'].iloc[i] == 0)):
                away_team_win += 1


        context = {
        'home_team': home_team,
        'away_team': away_team,
        'home_stats': home_stats,
        'away_stats': away_stats,
        'home_count': home_team_win,
        'away_count': away_team_win,
        'home_polar': home_polar,
        'away_polar': away_polar
        }

        return render(request, 'templates/analysis.html', context)