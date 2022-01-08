from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
	path('', views.PredictView.as_view(), name='predict'),
	path('analysis/', views.AnalysisView.as_view(), name='analysis')
]