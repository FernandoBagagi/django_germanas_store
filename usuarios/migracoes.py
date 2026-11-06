from django.db.migrations.operations.base import Operation


class InstalarUsuarios(Operation):
    """Adota auth_user sem perder PKs ou relações; reversão exige backup."""

    reversible = False

    def __init__(self, operacoes):
        self.operacoes = operacoes

    def state_forwards(self, app_label, state):
        for operacao in self.operacoes:
            operacao.state_forwards(app_label, state)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        conexao = schema_editor.connection
        tabelas = conexao.introspection.table_names()
        usuario = to_state.apps.get_model('usuarios', 'Usuario')
        if 'auth_user' not in tabelas:
            schema_editor.create_model(usuario)
        else:
            with conexao.cursor() as cursor:
                cursor.execute(
                    'SELECT LOWER(TRIM(email)), COUNT(*) FROM auth_user '
                    "WHERE TRIM(email) <> '' GROUP BY LOWER(TRIM(email)) "
                    'HAVING COUNT(*) > 1'
                )
                if cursor.fetchone():
                    raise RuntimeError('Há emails duplicados. Corrija antes de migrar.')
                colunas = {
                    c.name
                    for c in conexao.introspection.get_table_description(
                        cursor,
                        'auth_user',
                    )
                }
                cursor.execute('UPDATE auth_user SET email = LOWER(TRIM(email))')
                cursor.execute(
                    'UPDATE auth_user SET is_staff = 1 WHERE is_superuser = 1'
                )
            estado = to_state.clone()
            estado.models['usuarios', 'usuario'].options['constraints'] = []
            faltantes = [
                f for f in usuario._meta.local_fields if f.column not in colunas
            ]
            for campo in faltantes:
                estado.remove_field('usuarios', 'usuario', campo.name)
            for campo in faltantes:
                estado.add_field('usuarios', 'usuario', campo.name, campo.clone(), True)
                parcial = estado.apps.get_model('usuarios', 'Usuario')
                schema_editor.add_field(parcial, parcial._meta.get_field(campo.name))
            with conexao.cursor() as cursor:
                cursor.execute('UPDATE auth_user SET cadastro_pendente = 1')
            for constraint in usuario._meta.constraints:
                schema_editor.add_constraint(usuario, constraint)
        for nome in ('VinculoGrupo', 'VinculoPermissao'):
            modelo = to_state.apps.get_model('usuarios', nome)
            if modelo._meta.db_table not in tabelas:
                schema_editor.create_model(modelo)
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO auth_group (name) SELECT 'CLIENTE' "
                "WHERE NOT EXISTS (SELECT 1 FROM auth_group WHERE name = 'CLIENTE')"
            )
            cursor.execute(
                'INSERT INTO auth_user_groups (user_id, group_id) '
                'SELECT u.id, g.id FROM auth_user u JOIN auth_group g '
                "ON g.name='CLIENTE' "
                'WHERE u.is_superuser = 0 AND NOT EXISTS '
                '(SELECT 1 FROM auth_user_groups v '
                'WHERE v.user_id=u.id AND v.group_id=g.id)'
            )

    def describe(self):
        return 'Criar ou adotar usuários preservando a tabela auth_user'
