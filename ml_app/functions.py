from bs4 import BeautifulSoup
import os
import shutil
import io
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import requests
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
import pickle

pd.options.mode.chained_assignment = None

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



def save_data():
    try:
        os.remove('EPL.csv')
    except OSError:
        print("File 'EPL.csv' does not exist")

    all_match = pd.DataFrame()

    files = [file for file in os.listdir('ml_app/data')]

    for file in files:
        df = pd.read_csv('ml_app/data/'+file)
        all_match = pd.concat([all_match, df])

    all_df = all_match.dropna(how='all')

    all_df['Date'] = pd.to_datetime(all_df['Date'])
    all_df['Year'] = all_df['Date'].dt.year
    all_df = all_df.sort_values('Year')

    all_df = all_df.sort_values('Year', ascending=False)

    all_df.to_csv('EPL.csv')

    return "Successfully saved data."



def get_data_set():
    data = pd.read_csv('EPL.csv', sep=r'\s*,\s*', header=0, encoding='ascii', engine='python')
    res_num = []

    for i in range(data.shape[0]):
        if data['FTHG'][i] > data['FTAG'][i]:
            res_num.append(2)
        elif data['FTAG'][i] > data['FTHG'][i]:
            res_num.append(0)
        else:
            res_num.append(1)

    data['Result'] = res_num

    dataset = pd.DataFrame((data['HomeTeam'][i] for i in range(data.shape[0])), columns=['HomeTeam'])
    dataset['AwayTeam'] = data['AwayTeam']
    dataset['Results'] = data['Result']
    dataset['Year'] = data['Year']

    return dataset


def save_model(dataset):
    try:
        os.remove('saved.pkl')
    except OSError:
        print("File 'saved.pkl' does not exist.")

    le_home_team = LabelEncoder()
    dataset['HomeTeam'] = le_home_team.fit_transform(dataset['HomeTeam'])
    dataset['HomeTeam'].unique()

    le_away_team = LabelEncoder()
    dataset['AwayTeam'] = le_away_team.fit_transform(dataset['AwayTeam'])
    dataset['AwayTeam'].unique()

    X = dataset[['HomeTeam', 'AwayTeam']]
    y = dataset['Results']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=3)
    sc = StandardScaler()
    X_train = sc.fit_transform(X_train)
    X_test = sc.transform(X_test)
    model = SVC(probability=True)
    model.fit(X_train, y_train)

    data = {'model':model, 'le_home_team':le_home_team, 'le_away_team':le_away_team}

    with open('saved.pkl', 'wb') as _file:
        pickle.dump(data, _file)

    with open('saved.pkl', 'rb') as _file:
        data = pickle.load(_file)

    model = data['model']

    accuracy = model.score(X_test,y_test)

    return f"Successfully saved prediction model with accuracy {accuracy}"
