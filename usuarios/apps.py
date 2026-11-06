from django.apps import AppConfig
from django.db.models.signals import post_migrate


def configurar_grupos(sender, using, **kwargs) -> None:
    from django.contrib.auth.models import Group, Permission

    for nome, acoes in {
        'CLIENTE': ['view'],
        'VENDEDOR': ['add', 'change', 'delete', 'view'],
    }.items():
        grupo, _ = Group.objects.using(using).get_or_create(name=nome)
        permissoes = Permission.objects.using(using).filter(
            content_type__app_label='produtos',
            codename__in=[f'{acao}_produto' for acao in acoes],
        )
        grupo.permissions.set(permissoes)


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'
    verbose_name = 'Usuários'

    def ready(self) -> None:
        from django.contrib.auth.signals import user_logged_in

        from usuarios.middleware import registrar_sessao

        user_logged_in.connect(registrar_sessao, dispatch_uid='usuarios.sessao')
        post_migrate.connect(configurar_grupos, dispatch_uid='usuarios.grupos')
