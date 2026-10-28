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
| 🔍 OCR | 🔜 | Planejado (PDF pesquisável) |

Extras já implementados: detecção automática de **PDFs protegidos por senha**,
validação de arquivos corrompidos, **processamento 100% em memória**,
**exclusão dos uploads e do resultado assim que o download é concluído** e
**cards clicáveis na página inicial** para abrir cada ferramenta.

## Como rodar

Pré-requisito: Docker (com Compose v2). Nada mais precisa estar instalado.

```bash
git clone <repo> managerpdf && cd managerpdf
docker compose up --build
```

Acesse **http://localhost:8501**.

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
│   └── roadmap_page.py     # funcionalidades planejadas
├── src/                    # núcleo de processamento (sem Streamlit)
│   ├── pdf_utils.py        # validação, senha, intervalos de páginas
│   ├── merge.py            # merge_pdfs()
│   ├── split.py            # extract_ranges / split_every_page / split_in_chunks
│   ├── rotate.py           # rotate_pdf()
│   ├── compress.py         # compress_pdf() + CompressionReport
│   ├── to_image.py         # iter_page_images() (PNG/JPG)
│   ├── archive.py          # ZIP em memória
│   ├── preview.py          # renderização de páginas em PNG
│   └── storage.py          # workspace temporário + limpeza de /tmp
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

**Senhas:** `open_pdf()` verifica `needs_pass`, autentica quando necessário e
levanta `PDFPasswordError`; a interface pede a senha e tenta novamente.

**Limites de segurança:** 200 MB por upload (`maxUploadSize`) e no máximo 300
arquivos gerados por operação de divisão, evitando consumo descontrolado de
memória.

**Erros:** toda mensagem é escrita em português e pronta para o usuário final
(`PDFProcessingError`), com uma barreira final em `components.run_safely()`.

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

- [ ] OCR com Tesseract na imagem Docker
- [ ] Testes automatizados do núcleo (`pytest`)
- [ ] Marca d'água, numeração de páginas e proteção por senha

## Licença

Uso pessoal/educacional.
