# DeliveryDispatch

Projeto em desenvolvimento para o TP1 de Algoritmos 2. O objetivo é implementar a busca geoespacial de entregadores próximos a restaurantes, utilizando Geohash, Trie compacta e filtragem por raio de atendimento.

## Estrutura

- `src/delivery_dispatch/`: código do projeto, com pastas para modelos, algoritmos, serviços, dados e interface.
- `tests/`: testes unitários, de integração e dados de teste.
- `scripts/`: comandos de configuração, execução e verificação.
- `data/`: dados originais, dados processados e cache.
- `experiments/`: cenários e resultados de avaliação de desempenho.
- `docs/`: fonte LaTeX do relatório e figuras.

## Preparação e execução

Requer Python 3.12 ou superior. Execute os comandos a partir da raiz do repositório.

No Windows (PowerShell), use os scripts para preparar o ambiente, executar o programa e rodar os testes:

```powershell
.\scripts\config.bat
.\scripts\run.bat
.\scripts\run_tests.bat
```

- `config.bat`: cria o ambiente virtual `.venv`, se necessário, e instala o projeto e as ferramentas de desenvolvimento. Execute antes do primeiro uso.
- `run.bat`: executa o programa usando a `.venv`, quando disponível.
- `run_tests.bat`: executa os testes com pytest, usando a `.venv`, quando disponível.

Os scripts usam o ambiente virtual automaticamente, sem precisar ativá-lo manualmente.

<details>
<summary>Instruções alternativas para Linux e macOS</summary>

No Linux ou macOS, os arquivos `.bat` não são executáveis. Prepare o ambiente uma vez e use o `tasks.py` para as demais operações:

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/tasks.py setup
python scripts/tasks.py run
python scripts/tasks.py test
python scripts/tasks.py build
```

</details>

## CI e relatório

O CI executa as verificações e o build com Python 3.12 no Linux e no Windows em pushes e pull requests.

O relatório será escrito em [docs/report.tex](docs/report.tex), que atualmente contém apenas o título. Um workflow separado compila o PDF quando `docs/` é alterada ou por execução manual e disponibiliza o arquivo como artefato por 30 dias. A disponibilização externa do relatório será feita separadamente.
