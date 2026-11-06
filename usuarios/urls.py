from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy

from usuarios import views
from usuarios.tokens import gerador_recuperacao

app_name = 'usuarios'
urlpatterns = [
    path(
        'entrar/',
        auth.LoginView.as_view(template_name='usuarios/entrar.html'),
        name='entrar',
    ),
    path('sair/', auth.LogoutView.as_view(), name='sair'),
    path('cadastrar/', views.cadastrar, name='cadastrar'),
    path('minha_conta/', views.minha_conta, name='minha_conta'),
    path('minha_conta/editar/', views.editar_conta, name='editar_conta'),
    path('minha_conta/desativar/', views.desativar_conta, name='desativar_conta'),
    path('', views.listar, name='listagem'),
    path('novo/', views.cadastrar_admin, name='novo'),
    path('<int:id>/editar/', views.editar_usuario, name='editar'),
    path('<int:id>/desativar/', views.desativar_conta, name='desativar'),
    path('<int:id>/reativar/', views.reativar_usuario, name='reativar'),
    path('<int:id>/alterar_papel/', views.alterar_papel, name='alterar_papel'),
    path(
        'redefinir_senha/',
        auth.PasswordResetView.as_view(
            token_generator=gerador_recuperacao,
            template_name='usuarios/formulario.html',
            email_template_name='usuarios/email_recuperacao.txt',
            subject_template_name='usuarios/assunto_recuperacao.txt',
            success_url=reverse_lazy('usuarios:senha_enviada'),
            extra_context={'titulo': 'Recuperar senha'},
        ),
        name='redefinir_senha',
    ),
    path(
        'senha_enviada/',
        auth.PasswordResetDoneView.as_view(
            template_name='usuarios/senha_enviada.html',
        ),
        name='senha_enviada',
    ),
    path(
        'confirmar_senha/<uidb64>/<token>/',
        views.ConfirmarSenha.as_view(
            success_url=reverse_lazy('usuarios:senha_concluida'),
        ),
        name='confirmar_senha',
    ),
    path(
        'senha_concluida/',
        auth.PasswordResetCompleteView.as_view(
            template_name='usuarios/senha_concluida.html',
        ),
        name='senha_concluida',
    ),
]
