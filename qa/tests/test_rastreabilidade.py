"""Verificações offline da infraestrutura de QA; nunca acessam a aplicação."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from qa.tests.cliente_http import Roteiro


class TesteRastreabilidade(unittest.TestCase):
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
