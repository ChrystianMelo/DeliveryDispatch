# DeliveryDispatch

Encontrar entregadores próximos a um restaurante com baixa latência exige organizar posições
geográficas e reduzir o espaço de busca sem perder precisão. O DeliveryDispatch está sendo
construído para explorar esse problema em Belo Horizonte, combinando Geohash, Trie compacta,
simulação espacial e geometria viária.

Além de avançar a solução, o desenvolvimento exercita estruturas de dados, algoritmos
geoespaciais, integração com serviços externos e testes automatizados.

## Visão geral

O fluxo implementado atualmente:

- prepara e geocodifica uma base de bares e restaurantes;
- gera uma frota sintética distribuída ao redor desses estabelecimentos;
- ajusta as posições dos entregadores à malha viária do OpenStreetMap;
- converte coordenadas em Geohashes;
- organiza estabelecimentos e entregadores em índices baseados em Trie compacta.

A busca em células vizinhas, a filtragem final por raio e a interface interativa ainda serão
integradas.

## Requisitos

- Python 3.12 ou superior;
- conexão com a internet caso a base processada ou a malha viária ainda não estejam
  disponíveis localmente.

## Instalação e execução

No Windows, execute os comandos a partir da raiz do repositório:

```powershell
.\scripts\config.bat
.\scripts\run.bat 100
```

O argumento `100` define a quantidade de entregadores simulados. Use `0` para executar
somente a preparação dos dados.

Para consultar as demais opções:

```powershell
.\scripts\run.bat --help
```

<details>
<summary>Linux e macOS</summary>

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/tasks.py setup
python scripts/tasks.py run 100
```

</details>

## Dados e cache

A base enriquecida com coordenadas fica em
`data/processed/bares_geocodificados.csv`. Respostas de geocodificação e a malha viária são
armazenadas em `data/cache/` para evitar consultas e downloads repetidos.

A opção `--rebuild-processed` recria a base processada. Essa operação pode exigir milhares de
consultas e deve respeitar a
[política de uso do Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

Os dados geográficos utilizados são fornecidos por
[OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.

## Testes

No Windows:

```powershell
.\scripts\run_tests.bat
```

Em outros ambientes:

```bash
python scripts/tasks.py test
```

## Estrutura

- `src/delivery_dispatch/`: implementação da aplicação;
- `data/`: bases original, processada e caches locais;
- `tests/`: testes automatizados;
- `experiments/`: cenários e resultados experimentais;
- `docs/`: relatório e documentação.

## Relatório

A descrição completa do problema, as decisões de implementação, a análise dos algoritmos e
os resultados experimentais ficam concentrados no relatório:

- [Fonte em LaTeX](docs/report.tex)
- [Baixar relatório em PDF](https://github.com/ChrystianMelo/DeliveryDispatch/releases/download/report/report.pdf)
