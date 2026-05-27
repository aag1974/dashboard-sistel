# Conversor Residencial: entrada CSV + app de arrastar/soltar

Data: 2026-05-27

## Objetivo

Mudar o fluxo de trabalho do `converte_residencial.py`. Hoje ele lê um arquivo
Excel (`.xlsx`) escolhido por diálogo do tkinter e grava o Excel no formato
padrão. O novo fluxo deve:

1. Ler um arquivo **CSV** (em vez de Excel).
2. Lê-lo de forma robusta quanto à codificação, garantindo texto correto em
   Unicode (UTF-8) — acentos, `Ano/Mês`, `Valor M²` etc.
3. Gravar o Excel no formato padrão, salvo **automaticamente ao lado do CSV**.
4. A seleção do arquivo é por **arrastar e soltar numa janela** (zona de drop).
5. Distribuído como um **executável de dois cliques** para **macOS**.

Escopo: **apenas o conversor residencial**. O `converte_comercial.py` não muda.

## Decisões (confirmadas com o usuário)

- Conversor afetado: somente `converte_residencial.py`.
- Interação: janela com zona de "soltar" o arquivo (tkinterdnd2), não soltar no ícone.
- Saída: automática, `<nome>_convertido_padrao.xlsx` na mesma pasta do CSV, sem perguntar.
- Plataforma: somente macOS.
- Empacotamento: **PyInstaller** gerando um `.app` autocontido (Python + pandas +
  openpyxl + tkinterdnd2 embutidos), sem janela de Terminal.
- A lógica de transformação residencial (`_reconstituir_oferta`,
  `transform_new_to_standard`) **permanece inalterada**. Só mudam a entrada
  (Excel → CSV) e a interface (diálogo → zona de drop).

## Ambiente

- Python 3.12.2 (python.org), arquitetura Intel x86_64, em `/usr/local/bin/python3`.
- Já instalados: `pandas` 2.2.1, `openpyxl` 3.1.2, `tkinter` 8.6, `PyInstaller` 6.4.0.
- Falta instalar: `tkinterdnd2` (`pip install tkinterdnd2`).

## Formato do CSV de entrada

Confirmado com o arquivo de exemplo `2026_04_Residencial.csv`:

- Separador de campos: `;`
- Separador decimal: `,` ; separador de milhar: `.` (ex.: `6.264,02`, `53,48`)
- Cabeçalhos com acento/superscrito: `Ano/Mês`, `Área`, `Área Total`,
  `Vagas de Garagem`, `Valor M²`, `Área Valor`, etc.
- O exemplo está em UTF-8, mas o leitor deve tolerar outras codificações comuns.

## Arquitetura

### 1. Leitura do CSV — `ler_csv(caminho) -> pd.DataFrame`

- Usa `pd.read_csv` com `sep=';'`, `decimal=','`, `thousands='.'`.
- Tenta codificações em ordem até uma funcionar: `utf-8-sig` → `cp1252` → `latin-1`.
  (`utf-8-sig` cobre UTF-8 com e sem BOM; `cp1252`/`latin-1` cobrem arquivos
  exportados por Excel/Windows em português.)
- Resultado: colunas numéricas viram `float`/`int` (como vinha do Excel), texto
  vem correto em Unicode. Isso preserva o contrato esperado pelas funções de
  transformação, que hoje recebem números nativos do `read_excel`.

### 2. Núcleo testável — `converter_arquivo(caminho_csv) -> Path`

Função pura (sem GUI):

1. `df_new = ler_csv(caminho_csv)`
2. `df_std = transform_new_to_standard(df_new)` (função existente, inalterada)
3. Define a saída: `Path(csv).with_name(Path(csv).stem + "_convertido_padrao.xlsx")`
4. `df_std.to_excel(saida, index=False)`
5. Retorna o `Path` de saída.

Erros sobem como exceção para a GUI tratar.

### 3. Interface — janela com zona de drop (tkinterdnd2)

- Janela única com uma área grande "Arraste o CSV aqui".
- Ao soltar um arquivo: chama `converter_arquivo`, e mostra na própria janela
  o resultado (caminho do `.xlsx` gerado) ou a mensagem de erro.
- Aceita múltiplos arquivos soltos? Não nesta versão (YAGNI): processa o primeiro
  `.csv` solto; se vier algo que não é `.csv`, mostra aviso.
- Sem diálogo de "salvar como": a saída é automática ao lado do CSV.

### 4. Empacotamento — PyInstaller `.app`

- Script/arquivo `build_app.command` (duplo-clique) que roda o PyInstaller em
  modo `--windowed` para gerar `Converter Residencial.app`.
- Precisa incluir os dados/binários do `tkinterdnd2` (a biblioteca traz os
  binários `tkdnd`); usar `--collect-all tkinterdnd2` (ou `collect_all` no
  `.spec`) para garantir o bundle correto.
- Build local não recebe atributo de quarentena, então o `.app` abre por
  duplo-clique sem o bloqueio do Gatekeeper.

## Fluxo de dados

```
CSV (qualquer encoding comum)
  -> ler_csv: sep=';', decimal=',', thousands='.', encoding tolerante
  -> DataFrame (texto Unicode, números nativos)
  -> transform_new_to_standard (inalterada)
  -> DataFrame padrão
  -> to_excel -> <nome>_convertido_padrao.xlsx (ao lado do CSV)
```

## Tratamento de erros

- CSV ilegível em todas as codificações testadas → erro claro na janela.
- Arquivo solto não é `.csv` → aviso na janela, sem processar.
- Falha na transformação/escrita → mensagem de erro com a causa na janela.
- Avisos de "unidade sem histórico" do `_reconstituir_oferta` hoje vão para o
  console (`print`). Como o `.app` não tem console visível, esses avisos serão
  redirecionados para a área de mensagens da janela (acumulados e exibidos junto
  ao resultado).

## Testes

- Unitário em `converter_arquivo` / `ler_csv` usando `2026_04_Residencial.csv`:
  - Lê sem erro; tipos numéricos corretos (ex.: `Valor M²` vira float `6264.02`).
  - Texto Unicode preservado (cabeçalhos com acento).
  - Gera `.xlsx` com as colunas do padrão na ordem esperada.
  - Saída fica na mesma pasta do CSV com o sufixo `_convertido_padrao`.
- A GUI e o empacotamento PyInstaller são validados manualmente (não há teste
  automatizado de drag-and-drop nem do bundle).

## Entregáveis

1. `converte_residencial.py` atualizado (leitura CSV + GUI de drop; transformação inalterada).
2. `build_app.command` para gerar o `.app` via PyInstaller.
3. `Converter Residencial.app` resultante do build.
4. Nota de dependência: `pip install tkinterdnd2`.

## Fora de escopo (YAGNI)

- Conversor comercial.
- Suporte a Windows.
- Soltar arquivo no ícone do app (droplet).
- Processar múltiplos CSVs de uma vez.
- Diálogo de "salvar como".
