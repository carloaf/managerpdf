# managerpdf

Suíte local de ferramentas para PDF inspirada no iLovePDF, feita em **Python +
Streamlit** com motor **PyMuPDF**. Roda inteiramente em **Docker**: todas as
dependências e configurações vivem dentro do container.

![status](https://img.shields.io/badge/status-MVP-e11d48)

## Funcionalidades

| Ferramenta | Status | Detalhes |
|---|---|---|
| 🧩 Juntar PDFs | ✅ | Vários uploads, reordenação por setas, ordenação por nome, inversão |
| ✂️ Dividir PDF | ✅ | Intervalos (`1-3, 5`), uma página por arquivo, blocos de N páginas |
| 🔄 Rotacionar PDF | ✅ | 90° / 180° / 270°, todas as páginas ou seleção, pré-visualização |
| 🗜️ Comprimir PDF | ✅ | Recompressão de imagens (qualidade + DPI + escala de cinza) e limpeza estrutural |
| 🖼️ PDF → imagem | ✅ | JPG/PNG com DPI ajustável, páginas selecionáveis e resultado em ZIP |
| 📄 PDF → Word | ✅ | DOCX editável via Marker (IA em CPU) + pandoc em container separado |
| 📊 PDF → Excel | ✅ | Tabelas extraídas com PyMuPDF → XLSX/ODS (uma aba por tabela + resumo) |
| 🔍 OCR (IA) | ✅ | PDF pesquisável via Indra OCR (ONNX Runtime) em container separado |

Extras já implementados: detecção automática de **PDFs protegidos por senha**,
validação de arquivos corrompidos, **processamento 100% em memória**,
**exclusão dos uploads e do resultado assim que o download é concluído**,
**cards clicáveis na página inicial** para abrir cada ferramenta e **contador
de trabalhos realizados** (persistente entre reinícios) no topo da página
inicial.

## Como rodar

Pré-requisito: Docker (com Compose v2). Nada mais precisa estar instalado.

```bash
git clone <repo> managerpdf && cd managerpdf
docker compose up --build
```

Acesse **http://localhost:8501**.

O comando sobe três containers: `managerpdf` (interface Streamlit), `ocr`
(serviço Indra OCR) e `convert` (serviço Marker → Word). O build do `ocr` e do
`convert` baixa os modelos de IA (~76 MB cada) e a fonte do Marker, então o
runtime não depende de rede.

## Deploy no servidor (VM em outro PC)

Requisitos na VM: Linux x86_64, **Docker com Compose v2** e acesso SSH. Os
valores abaixo são para a VM de referência (**4 GB de RAM / 6 vCPU**).

```bash
# 1. Na VM: clonar o repositório
git clone <repo> managerpdf && cd managerpdf

# 2. Construir e subir em background
docker compose up -d --build

# 3. Conferir a saúde dos três containers (devem ficar "healthy")
docker compose ps
```

Acesse de qualquer PC da rede: **http://IP_DA_VM:8501** (a interface escuta em
`0.0.0.0:8501`). Se a porta não responder, libere o firewall da VM:

```bash
sudo ufw allow 8501/tcp   # ou: sudo firewall-cmd --add-port=8501/tcp --permanent
```

**Dimensionamento para 4 GB / 6 vCPU** (já aplicado no [compose.yaml](./compose.yaml)):

| Container | Limite | Observação |
|---|---|---|
| `ocr` | `mem_limit: 1g`, `cpus: 2.0`, 2 threads | ≈ 366 MB ocioso; pico ≈ 650 MB |
| `convert` | `mem_limit: 2g`, `cpus: 3.0`, 2 threads | ≈ 280 MB ocioso; pico medido ≈ 740 MB (30 páginas) |
| `managerpdf` | sem limite fixo | ≈ 36 MB ocioso; pico ~1 GB ao processar upload de 200 MB |

- **Total em regime ≈ 0,7 GB; pico ≈ 2 GB** → cabe nos 4 GB, mesmo com as três
  ferramentas em uso simultâneo.
- OCR e Marker são CPU-bound e rodam bem com 2 threads (configuradas por
  `INDRA_THREADS`); **não** aumente as threads — cada thread extra acrescenta
  ~150 MB de RAM sem ganho proporcional na VM.
- Em CPUs **sem AVX2** (máquinas antigas), o ONNX Runtime usa um caminho lento:
  o OCR/conversão pode levar vários segundos por página. Em CPU moderna o
  esperado é ~210–400 ms/página no OCR.
- A primeira conversão inclui o carregamento dos modelos (≈ 15–40 s); as
  seguintes ficam em poucos segundos por página.
- Um documento de até **200 páginas** é aceito na conversão para Word; acima
  disso, divida o PDF antes (proteção de memória do container).

### Atualizar a aplicação na VM

```bash
cd managerpdf
git pull
docker compose up -d --build   # reconstrói e recria o que mudou
```

### Comandos úteis

```bash
docker compose logs -f managerpdf ocr convert   # acompanha os três serviços
docker compose ps                                # status + health
docker compose exec ocr curl -fsS http://localhost:8000/health     # saúde do OCR
docker compose exec convert curl -fsS http://localhost:8000/health # saúde do convert
```

### Atalhos com Make

```bash
make up       # build + start em background
make logs     # acompanha logs
make down     # para os containers
make dev      # modo desenvolvimento (hot reload) em :8502
make shell    # shell dentro do container
make clean    # remove containers, imagens e volumes do projeto
```

### Modo desenvolvimento

Monta o código do host, mas as dependências continuam no container:

```bash
docker compose --profile dev up --build
# http://localhost:8502
```

## Estrutura do projeto

```
managerpdf/
├── app.py                  # entrypoint Streamlit + navegação
├── ui/                     # camada de interface
│   ├── theme.py            # CSS global, hero, cartões
│   ├── components.py       # upload, senha, resultado, execução segura
│   ├── home.py             # página inicial
│   ├── merge_page.py       # juntar PDFs (com ordenação)
│   ├── split_page.py       # dividir PDF
│   ├── rotate_page.py      # rotacionar PDF (com prévia)
│   ├── compress_page.py    # comprimir PDF (com relatório)
│   ├── image_page.py       # PDF → imagem (JPG/PNG em ZIP)
│   ├── word_page.py        # PDF → Word (DOCX via serviço Marker)
│   ├── excel_page.py       # PDF → Excel/Calc (XLSX/ODS)
│   ├── ocr_page.py         # OCR (PDF pesquisável)
│   └── roadmap_page.py     # funcionalidades planejadas
├── src/                    # núcleo de processamento (sem Streamlit)
│   ├── pdf_utils.py        # validação, senha, intervalos de páginas
│   ├── merge.py            # merge_pdfs()
│   ├── split.py            # extract_ranges / split_every_page / split_in_chunks
│   ├── rotate.py           # rotate_pdf()
│   ├── compress.py         # compress_pdf() + CompressionReport
│   ├── to_image.py         # iter_page_images() (PNG/JPG)
│   ├── word.py             # cliente do serviço Marker (PDF → DOCX)
│   ├── excel.py            # extração de tabelas + XLSX/ODS (openpyxl/odfpy)
│   ├── ocr.py              # cliente do serviço OCR + PDF pesquisável
│   ├── archive.py          # ZIP em memória
│   ├── preview.py          # renderização de páginas em PNG
│   ├── stats.py            # contador persistente de trabalhos realizados
│   └── storage.py          # workspace temporário + limpeza de /tmp
├── services/               # serviços auxiliares em containers próprios
│   ├── ocr/                # serviço OCR isolado (Indra OCR + FastAPI)
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── requirements.txt
│   └── convert/            # serviço PDF → Word (Marker + pandoc + FastAPI)
│       ├── Dockerfile
│       ├── app.py
│       └── requirements.txt
├── Dockerfile
├── compose.yaml
├── requirements.txt
└── .streamlit/config.toml
```

A separação é intencional: `src/` não conhece Streamlit, então pode ser usado em
CLI, testes ou API no futuro. `ui/` apenas coleta dados, chama `src/` e exibe
resultados.

## Decisões técnicas

**Motor:** PyMuPDF (fitz) — rápido, sem dependências de sistema, com suporte a
`insert_pdf` (merge/split), `set_rotation` e `replace_image` (compressão).

**Arquivos temporários:** nenhum arquivo é gravado em disco no fluxo normal. Os
PDFs trafegam como `bytes` entre as funções e os downloads do Streamlit. Ao
concluir um download (ou descartar o resultado), a interface remove da sessão o
arquivo gerado e os uploads, recriando o uploader vazio. O `src/storage.py`
fornece `temp_workspace()` (limpeza automática ao sair do `with`) para fluxos
futuros que exijam disco, como OCR, e `purge_temp_root()`, executado na
inicialização, que remove sobras com mais de 6 horas. O `compose.yaml` ainda
monta `/tmp` como `tmpfs` limitado a 256 MB, então um eventual vazamento nunca
chega ao disco do host.

**Contador de trabalhos:** `src/stats.py` mantém um total que começa em 114 e
é incrementado por `components.set_result()` a cada resultado exibido, ou seja,
uma vez por operação concluída com sucesso (reruns e descartes não contam). O
valor vive em `/data/stats.json`, apontado por `STATS_PATH`, e o `compose.yaml`
monta o volume nomeado `stats` nesse caminho — é o único dado persistido, já
que os documentos continuam trafegando apenas em memória. Sem o volume (ou com
o arquivo ilegível) o contador cai para memória e volta a 114 no próximo
reinício.

**Senhas:** `open_pdf()` verifica `needs_pass`, autentica quando necessário e
levanta `PDFPasswordError`; a interface pede a senha e tenta novamente.

**Limites de segurança:** 200 MB por upload (`maxUploadSize`) e no máximo 300
arquivos gerados por operação de divisão, evitando consumo descontrolado de
memória.

**Erros:** toda mensagem é escrita em português e pronta para o usuário final
(`PDFProcessingError`), com uma barreira final em `components.run_safely()`.

**OCR:** o reconhecimento usa o [Indra OCR](https://github.com/datalab-to/indra)
(IA em ONNX Runtime, ~76 MB, sem GPU) em um container separado (`ocr`), exposto
via HTTP. O `managerpdf` envia o PDF ao serviço local, recebe as linhas com
suas coordenadas e sobrepõe uma camada de texto invisível com PyMuPDF, gerando
um PDF pesquisável sem alterar a aparência. Páginas que já possuem camada de
texto são mantidas como estão. O serviço usa 2 threads (pico ~650 MB de RAM) e
tem `mem_limit` de 1 GB no compose.

**PDF → Word:** a conversão usa o [Marker](https://github.com/datalab-to/marker)
(Apache 2.0, modo `fast` em CPU, Indra ONNX) em um container separado
(`convert`), seguido do `pandoc` para transformar o HTML do Marker em DOCX —
assim tabelas e fórmulas se tornam elementos nativos do Word. O `src/word.py`
descriptografa o PDF localmente e envia os bytes ao serviço, que devolve o
DOCX pronto. Os modelos e a fonte de renderização do Marker são baixados no
build, mantendo o runtime sem rede. O Marker declara `torch` como dependência,
mas o build instala apenas as rodas **CPU** (`+cpu`), sem os pacotes CUDA.

**PDF → Excel:** a extração usa `Page.find_tables()` do PyMuPDF (instantâneo,
sem IA) sobre o texto já embutido no PDF e grava a planilha com `openpyxl`
(XLSX) ou `odfpy` (ODS), com uma aba por tabela e uma aba de resumo. PDFs
escaneados sem camada de texto devem passar antes pela ferramenta de OCR; a
extração de tabelas em digitalizados (RapidTable/RapidLayout) está planejada.

## Comportamento da compressão

1. Cada imagem é reescalada para a resolução escolhida (DPI) e recodificada em
   JPEG com a qualidade definida.
2. Imagens com canal de transparência (`smask`) e imagens muito pequenas são
   preservadas para não perder qualidade.
3. O arquivo é salvo com `garbage=4`, `deflate`, `clean`, removendo objetos
   órfãos e compactando streams; há fallbacks caso o PDF seja incomum.
4. Se o resultado ficar maior que o original, o original é devolvido — o
   relatório mostra a redução real.

## Próximos passos

- [ ] Testes automatizados do núcleo (`pytest`)
- [ ] Marca d'água, numeração de páginas e proteção por senha
- [ ] OCR: posicionamento exato do texto em páginas rotacionadas/verticais
- [ ] Excel: tabelas de PDFs escaneados com RapidTable/RapidLayout (ONNX)
- [ ] Word: suporte a `.doc` e ajuste fino de tabelas mescladas

## Licença

Uso pessoal/educacional.
