"""Verificações offline da infraestrutura de QA; nunca acessam a aplicação."""

import io
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from qa.novo_relatorio import criar_relatorio
from qa.roteiros.cliente_http import Roteiro


class TesteRastreabilidade(unittest.TestCase):
    def test_numeracao_preserva_historico_e_concorrencia(self) -> None:
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            primeiro = pasta / 'relatorio_001.md'
            primeiro.write_text('Evidência histórica', encoding='utf-8')
            with ThreadPoolExecutor(max_workers=2) as grupo:
                criados = list(grupo.map(lambda _: criar_relatorio(pasta), range(2)))
            self.assertEqual(
                {arquivo.name for arquivo in criados},
                {'relatorio_002.md', 'relatorio_003.md'},
            )
            self.assertEqual(primeiro.read_text(), 'Evidência histórica')
            for arquivo in criados:
                texto = arquivo.read_text()
                self.assertIn('Rascunho', texto)
                self.assertIn('Não retestada', texto)
                self.assertIn('SHA-256', texto)

    def test_evidencias_nao_gravam_corpos_com_segredos(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporario,
            patch.dict(os.environ, {'QA_EXECUCAO': temporario}, clear=True),
        ):
            roteiro = Roteiro()
            with redirect_stdout(io.StringIO()):
                roteiro.verificar(
                    'Sem segredos',
                    {
                        'status': 200,
                        'corpo': {'access': 'segredo-a', 'password': 'segredo-b'},
                    },
                    200,
                    41,
                )
            conteudo = (Path(temporario) / 'verificacoes.jsonl').read_text()
            self.assertNotIn('segredo-a', conteudo)
            self.assertNotIn('segredo-b', conteudo)
            self.assertTrue(json.loads(conteudo)['passou'])

    def test_divergencia_registrada_sem_interromper_a_rodada(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temporario,
            patch.dict(os.environ, {'QA_EXECUCAO': temporario}, clear=True),
        ):
            roteiro = Roteiro()
            with redirect_stdout(io.StringIO()):
                roteiro.verificar('Divergência', {'status': 400, 'corpo': {}}, 403, 65)
            self.assertEqual(roteiro.falhas, 1)

    def test_estado_privado_recusa_repositorio(self) -> None:
        raiz = str(Path(__file__).resolve().parents[2])
        with (
            patch.dict(os.environ, {'QA_EXECUCAO': raiz}, clear=True),
            self.assertRaisesRegex(ValueError, 'fora do repositório'),
        ):
            Roteiro()

    def test_destino_externo_recusado(self) -> None:
        with (
            patch.dict(os.environ, {'QA_URL': 'https://example.com'}, clear=True),
            self.assertRaisesRegex(ValueError, 'servidor local'),
        ):
            Roteiro()


if __name__ == '__main__':
    unittest.main()
