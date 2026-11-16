"""Cria um rascunho incremental sem executar testes nem alterar relatórios antigos."""

import hashlib
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PASTA_QA = Path(__file__).resolve().parent
RAIZ = PASTA_QA.parent


def criar_relatorio(pasta: Path = PASTA_QA / 'relatorios') -> Path:
    """Reserva um número sem sobrescrever um relatório, inclusive sob concorrência."""
    pasta.mkdir(parents=True, exist_ok=True)
    numeros = [
        int(resultado.group(1))
        for arquivo in pasta.glob('relatorio_*.md')
        if (resultado := re.fullmatch(r'relatorio_(\d+)\.md', arquivo.name))
    ]
    numero = max(numeros, default=0) + 1
    while True:
        destino = pasta / f'relatorio_{numero:03d}.md'
        try:
            arquivo = destino.open('x', encoding='utf-8')
            break
        except FileExistsError:
            numero += 1
    commit = subprocess.run(
        ['git', 'rev-parse', 'HEAD'], cwd=RAIZ, capture_output=True, text=True
    )
    versao = commit.stdout.strip() if commit.returncode == 0 else 'Não disponível'
    fontes = [RAIZ / 'docs/PLAN_USUARIOS_ORIGINAL.md']
    fontes.extend(sorted((PASTA_QA / 'roteiros').glob('*.py')))
    rastros = '\n'.join(
        f'- `{fonte.relative_to(RAIZ)}`: '
        f'`{hashlib.sha256(fonte.read_bytes()).hexdigest()}`'
        for fonte in fontes
    )
    data = datetime.now(ZoneInfo('America/Bahia')).isoformat(timespec='seconds')
    with arquivo:
        arquivo.write(
            f'# Relatório de QA {numero:03d} — Usuários\n\n'
            f'Estado: **Rascunho — testes ainda não registrados**.\n\n'
            f'Criado em: {data}\n\nCommit no momento da criação: `{versao}`\n\n'
            '## Execução\n\n'
            '- Data/hora dos testes: preencher.\n- Ambiente: preencher.\n'
            '- Relatório anterior: preencher.\n'
            '- Comandos, evidências sanitizadas e versão testada: preencher.\n\n'
            '## Reteste das falhas\n\n'
            '| ID | Situação | Caso executado / evidência |\n'
            '|---|---|---|\n'
            '| F01 | Não retestada | Datas ISO na API |\n'
            '| F02 | Não retestada | Datas ISO no Django Admin |\n'
            '| F03 | Não retestada | Mensagens JWT em pt-BR |\n'
            '| F04 | Não retestada | HTTP 403 para controles internos |\n\n'
            '## Novas falhas\n\n'
            'Para cada falha: ID, requisito e localização, passos, esperado, '
            'encontrado, evidência e impacto. Não reutilizar IDs anteriores.\n\n'
            '## Cobertura, limitações e limpeza\n\nPreencher após os testes.\n\n'
            '## Conclusão\n\nPendente de execução e triagem.\n\n'
            '## SHA-256 dos arquivos na criação do rascunho\n\n'
            f'{rastros}\n'
        )
    return destino


if __name__ == '__main__':
    print(criar_relatorio())
