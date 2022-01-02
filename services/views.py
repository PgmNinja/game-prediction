from django.shortcuts import render
from django.views import View, generic
import pickle
import numpy as np
from .choices import team_choices


def model_loaded():
	with open('saved.pkl', 'rb') as file:
		data = pickle.load(file)
	return data

data = model_loaded()

model = data['model']
le_home_team = data['le_home_team']
le_away_team = data['le_away_team']


class PredictView(View):
	def get(self, request, *args, **kwargs):
		context = {'teams': team_choices}
		return render(request, 'templates/predict.html', context)

	def post(self, request, *args, **kwargs):
		home_team = request.POST.get("home")
		away_team = request.POST.get("away")
		X = np.array([[home_team, away_team]])
		X[:,0] = le_home_team.transform(X[:,0])
		X[:,1] = le_away_team.transform(X[:,1])
		X = X.astype('float')
		y_pred = model.predict(X)
		print(y_pred)
		context = {'teams': team_choices}
		return render(request, 'templates/predict.html', context)
