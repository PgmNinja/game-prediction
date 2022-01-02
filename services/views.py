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


def model_loaded():
    with open('saved.pkl', 'rb') as file:
        data = pickle.load(file)
    return data

data = model_loaded()

model = data['model']
le_home_team = data['le_home_team']
le_away_team = data['le_away_team']


# storage_client = storage.Client.from_service_account_json('GCP_cred.json')

# bucket_name = 'ml_pred_bucket'
# bucket = storage_client.bucket(bucket_name)
# bucket.create(location='ASIA')


login = pd.read_csv('login.csv')

cons_key = login['Keys'][0]
cons_key_sec = login['Keys'][1]
acc_token = login['Keys'][2]
acc_token_sec = login['Keys'][3]

authenticate = tweepy.OAuthHandler(cons_key, cons_key_sec)

authenticate.set_access_token(acc_token, acc_token_sec)

api = tweepy.API(authenticate, wait_on_rate_limit=True)


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
