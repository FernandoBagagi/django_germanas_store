from django.urls import path

from produtos import views

app_name = 'produtos'
urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('produtos/', views.listagem, name='listagem'),
    path('produtos/<int:id>/', views.detalhe, name='detalhe'),
]
