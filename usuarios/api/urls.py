from django.urls import path

from usuarios.api import views

app_name = 'api_usuarios'
urlpatterns = [
    path('', views.Usuarios.as_view(), name='listagem'),
    path('cadastrar/', views.Cadastro.as_view(), name='cadastrar'),
    path('login/', views.Login.as_view(), name='login'),
    path('renovar/', views.Renovacao.as_view(), name='renovar'),
    path('redefinir_senha/', views.Recuperacao.as_view(), name='redefinir_senha'),
    path('confirmar_senha/', views.ConfirmacaoSenha.as_view(), name='confirmar_senha'),
    path('minha_conta/', views.MinhaConta.as_view(), name='minha_conta'),
    path('<int:id>/', views.DetalheUsuario.as_view(), name='detalhe'),
    path(
        '<int:id>/alterar_papel/', views.AlteracaoPapel.as_view(), name='alterar_papel'
    ),
    path('<int:id>/reativar/', views.Reativacao.as_view(), name='reativar'),
]
