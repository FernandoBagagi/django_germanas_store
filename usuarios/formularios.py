from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

from usuarios.servicos import CAMPOS, ServicoUsuarios
from usuarios.tokens import gerador_recuperacao
from usuarios.validadores import validar_formato_data_iso


class CampoDataISO(forms.DateField):
    def __init__(self, **kwargs):
        kwargs.setdefault('input_formats', ['%Y-%m-%d'])
        kwargs.setdefault(
            'widget', forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})
        )
        super().__init__(**kwargs)

    def to_python(self, value):
        if isinstance(value, str) and value:
            validar_formato_data_iso(value)
        return super().to_python(value)


class FormularioUsuario(forms.Form):
    username = forms.CharField(label='Login', max_length=150)
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(label='Primeiro nome', max_length=150)
    last_name = forms.CharField(label='Sobrenome', max_length=150)
    data_nascimento = CampoDataISO(label='Data de nascimento')
    cpf = forms.CharField(label='CPF')
    telefone = forms.CharField(label='Telefone com DDD')
    password = forms.CharField(label='Senha', strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        if usuario:
            kwargs['initial'] = {c: getattr(usuario, c) for c in CAMPOS}
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields['password'].required = False
            if usuario.cpf:
                self.fields['cpf'].disabled = True

    def dados(self) -> dict:
        dados = dict(self.cleaned_data)
        if self.usuario and not dados.get('password'):
            dados.pop('password', None)
        return dados

    def registrar_erros(self, erro: ValidationError) -> None:
        erros = (
            erro.message_dict
            if hasattr(erro, 'message_dict')
            else {None: erro.messages}
        )
        for campo, mensagens in erros.items():
            self.add_error(campo if campo in self.fields else None, mensagens)


class FormularioPapel(forms.Form):
    papel = forms.ChoiceField(
        choices=[(p, p) for p in ('CLIENTE', 'VENDEDOR', 'ADMIN')]
    )


def verificar_post(dados) -> None:
    ServicoUsuarios.verificar_campos(
        {k: v for k, v in dados.items() if k != 'csrfmiddlewaretoken'}
    )


def solicitar_recuperacao(email: str, request) -> None:
    formulario = PasswordResetForm({'email': email})
    if not formulario.is_valid():
        raise ValidationError({'email': formulario.errors['email']})
    formulario.save(
        token_generator=gerador_recuperacao,
        request=request,
        use_https=request.is_secure(),
        email_template_name='usuarios/email_recuperacao.txt',
        subject_template_name='usuarios/assunto_recuperacao.txt',
    )
