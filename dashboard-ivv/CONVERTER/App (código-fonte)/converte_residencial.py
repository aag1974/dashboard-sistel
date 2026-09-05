import sys
import pandas as pd
import numpy as np
from pathlib import Path

def _reconstituir_oferta(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que cada unidade vendida no mês mais recente (m_atual) tenha
    exatamente UMA linha de OFERTA em m_atual para o sistema legado.

    O novo sistema IVV (estoque derivado) já inclui OFERTA(m_atual) para
    unidades que estavam em estoque no início do mês — nesses casos a linha
    já existe e não precisa ser criada (fazê-lo geraria duplicata).

    Para unidades sem OFERTA(m_atual) no CSV (edge case: dados sem OFERTA
    prévia), tenta copiar o Valor M² de OFERTA(m_ant). Se não existir em
    m_ant tampouco, emite AVISO — são casos de integridade de dados a
    tratar manualmente.

    Chave de unidade: Empreendimento + Bloco + Apartamento
    """
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    meses = sorted(df['Ano/Mês'].dropna().unique())
    if len(meses) < 2:
        return df

    m_ant, m_atual = meses[-2], meses[-1]
    KEY = ['Empreendimento', 'Bloco', 'Apartamento']

    oferta_ant = (
        df[(df['Ano/Mês'] == m_ant) & (df['Item'] == 'Oferta')]
        .set_index(KEY)
    )
    # Unidades que já têm OFERTA em m_atual (vindas do estoque derivado IVV)
    oferta_atual_chaves = set(
        map(tuple, df[(df['Ano/Mês'] == m_atual) & (df['Item'] == 'Oferta')][KEY].values.tolist())
    )
    vendas_atual = df[(df['Ano/Mês'] == m_atual) & (df['Item'] == 'Venda')]

    linhas_reconstituidas = []
    for _, row in vendas_atual.iterrows():
        idx = (row['Empreendimento'], row['Bloco'], row['Apartamento'])
        if idx in oferta_atual_chaves:
            # OFERTA(m_atual) já está no CSV pelo estoque derivado — nada a fazer
            continue
        if idx in oferta_ant.index:
            nova = row.copy()
            nova['Item']       = 'Oferta'
            nova['Valor M²']   = oferta_ant.loc[idx, 'Valor M²']
            nova['Área Valor'] = nova['Área'] * nova['Valor M²']
            linhas_reconstituidas.append(nova)
        else:
            print(
                f"AVISO: unidade sem histórico em {m_ant} — "
                f"oferta não reconstituída: {row.get('Empreendimento')} "
                f"{row.get('Bloco')} Apto {row.get('Apartamento')} "
                f"(Lançamento={row.get('Lançamento')})"
            )

    if linhas_reconstituidas:
        df = pd.concat([df, pd.DataFrame(linhas_reconstituidas)], ignore_index=True)

    return df


def transform_new_to_standard(df_new: pd.DataFrame) -> pd.DataFrame:
    # Reconstituir linhas de oferta para unidades vendidas no mês mais recente
    df = _reconstituir_oferta(df_new)
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {
        'Ano/Mês': 'ANO_MES',
        'Empresa': 'EMPRESA',
        'Origem do Recurso': 'ORIGEM_RECURSOS',
        'Estágio da Obra': 'ESTAGIO_OBRA',
        'Bairro': 'BAIRRO',
        'Área': 'AREA',
        'Quartos': 'QTD_QUARTOS',
        'Elevadores': 'QTD_ELEVADORES',
        'Vagas de Garagem': 'QTD_GARAGEM',
        'Tempo de financiamento': 'TEMPO_FINANCIAMENTO',
        'Valor M²': 'VALOR_MEDIO_M2',
        'Empreendimento': 'EMPREENDIMENTO',
    }
    df = df.rename(columns=rename_map)

    def map_oferta(row):
        item = str(row.get('Item', '')).strip().lower()
        lanc = str(row.get('Lançamento', '')).strip().lower()
        is_launch = lanc in ('sim', 's', 'yes', 'y', 'true', '1')

        if item == 'oferta':
            return 'OFERTADOS LANCAMENTOS' if is_launch else 'OFERTADOS DISPONIVEIS'
        if item == 'venda':
            return 'VENDIDOS - LANCADOS E VENDIDOS' if is_launch else 'VENDIDOS'
        if item == 'distrato':
            return 'DISTRATO'
        return np.nan

    df['OFERTA_VENDA'] = df.apply(map_oferta, axis=1)

    # Defaults do padrão
    df['TIPO_EDICAO'] = 'Não permite atualizar o questionáro'
    df['STATUS'] = 'Manual'
    df['QUANTIDADE'] = 1

    # Numéricos
    numeric_cols = [
        'AREA', 'QUANTIDADE', 'QTD_QUARTOS', 'QTD_ELEVADORES', 'QTD_GARAGEM',
        'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Vocabulário do padrão legado: a base histórica usa 'Finan. Bancário' e agrupa
    # 4 quartos ou mais em '4+'. Sem isso o controle de qualidade acusa valor inválido.
    if 'ORIGEM_RECURSOS' in df.columns:
        df['ORIGEM_RECURSOS'] = df['ORIGEM_RECURSOS'].replace({'Financiamento Bancário': 'Finan. Bancário'})
    if 'QTD_QUARTOS' in df.columns:
        df['QTD_QUARTOS'] = df['QTD_QUARTOS'].apply(
            lambda q: '4+' if pd.notna(q) and q >= 4 else ('' if pd.isna(q) else str(int(q)))
        )

    # Derivadas
    df['AREA_QUANTIDADE'] = df['AREA'] * df['QUANTIDADE']
    df['AREA_VALOR'] = df['AREA'] * df['VALOR_MEDIO_M2']
    df['AREA_QUANTIDADE_VALOR'] = df['AREA'] * df['QUANTIDADE'] * df['VALOR_MEDIO_M2']

    # Ordem final padrão
    cols = [
        'ANO_MES', 'EMPRESA', 'ORIGEM_RECURSOS', 'ESTAGIO_OBRA', 'OFERTA_VENDA', 'BAIRRO',
        'TIPO_EDICAO', 'STATUS', 'AREA', 'QUANTIDADE', 'QTD_QUARTOS', 'QTD_ELEVADORES',
        'QTD_GARAGEM', 'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2', 'EMPREENDIMENTO',
        'AREA_QUANTIDADE', 'AREA_VALOR', 'AREA_QUANTIDADE_VALOR'
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    return df[cols].copy()


def ler_csv(caminho) -> pd.DataFrame:
    """
    Lê o CSV de entrada de forma robusta quanto à codificação e ao formato
    numérico brasileiro.

    - separador de campos: ';'
    - decimal: ',' ; milhar: '.'  (ex.: "6.264,02" -> 6264.02)
    - tenta as codificações utf-8-sig -> cp1252 -> latin-1, garantindo texto
      correto em Unicode independentemente da origem (Excel/Windows costuma
      exportar em cp1252).
    - index_col=False evita que o ';' ao final das linhas seja interpretado
      como índice.
    """
    caminho = Path(caminho)
    ultimo_erro = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(
                caminho,
                sep=";",
                decimal=",",
                thousands=".",
                index_col=False,
                encoding=enc,
            )
        except (UnicodeDecodeError, UnicodeError) as e:
            ultimo_erro = e
            continue
    raise ValueError(
        f"Não foi possível ler o CSV nas codificações utf-8/cp1252/latin-1: {ultimo_erro}"
    )


def diretorio_base() -> Path:
    """
    Pasta-base usada para a pasta de saída padrão.

    - App empacotado (.app): a pasta que contém o "Converter Residencial.app".
    - Rodando como script: a pasta onde está este arquivo.
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        for parent in exe.parents:
            if parent.suffix == ".app":
                return parent.parent
        return exe.parent
    return Path(__file__).resolve().parent


def converter_arquivo(caminho_csv, pasta_saida=None) -> Path:
    """
    Núcleo da conversão (sem interface): lê o CSV, aplica a transformação para o
    formato padrão e grava o Excel na pasta de convertidos, retornando o caminho.

    Por padrão, salva em ``diretorio_base()/"Arquivos Convertidos"`` (criada se
    não existir). ``pasta_saida`` permite sobrescrever esse destino.
    """
    caminho_csv = Path(caminho_csv)
    if pasta_saida is None:
        pasta_saida = diretorio_base() / "Arquivos Convertidos"
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    df_new = ler_csv(caminho_csv)
    df_std = transform_new_to_standard(df_new)
    saida = pasta_saida / (caminho_csv.stem + "_convertido_padrao.xlsx")
    df_std.to_excel(saida, index=False)
    return saida


def run_app():
    """
    Abre uma janela com uma zona de arrastar/soltar. Ao soltar um arquivo .csv,
    converte para o Excel padrão (salvo automaticamente ao lado do CSV) e mostra
    o resultado, os avisos e eventuais erros na própria janela.
    """
    import io
    import contextlib
    import tkinter as tk
    from tkinter import StringVar, filedialog

    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
    except Exception as e:
        raise RuntimeError(
            "tkinterdnd2 não está instalado. Rode: pip install tkinterdnd2"
        ) from e

    root = TkinterDnD.Tk()
    root.title("Converter Residencial — CSV → Excel padrão")
    root.geometry("600x460")
    root.configure(bg="#f3f4f6")

    def processar(caminho):
        p = Path(caminho)
        if p.suffix.lower() != ".csv":
            status_var.set(f"⚠️  Isto não é um CSV: {p.name}\nArraste um arquivo .csv.")
            return
        status_var.set(f"Convertendo {p.name}…")
        root.update_idletasks()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                saida = converter_arquivo(p)
        except Exception as e:
            status_var.set(f"❌  Falha na conversão de {p.name}:\n{e}")
            return
        avisos = buf.getvalue().strip()
        msg = f"✅  Arquivo gerado:\n{saida.name}\n\nPasta:\n{saida.parent}"
        if avisos:
            msg += f"\n\n⚠️  Avisos durante a conversão:\n{avisos}"
        status_var.set(msg)

    def on_drop(event):
        caminhos = root.tk.splitlist(event.data)
        if caminhos:
            processar(caminhos[0])

    def escolher():
        caminho = filedialog.askopenfilename(
            title="Selecione o CSV",
            filetypes=[("Arquivos CSV", "*.csv")],
        )
        if caminho:
            processar(caminho)

    tk.Label(
        root, text="Conversor Residencial", font=("Helvetica", 18, "bold"),
        bg="#f3f4f6", fg="#111827",
    ).pack(pady=(20, 4))
    tk.Label(
        root, text="Arraste um arquivo .CSV para a área abaixo",
        font=("Helvetica", 12), bg="#f3f4f6", fg="#374151",
    ).pack(pady=(0, 12))

    drop = tk.Label(
        root, text="⬇\n\nSolte o CSV aqui\n",
        font=("Helvetica", 14), bg="#ffffff", fg="#6b7280",
        relief="ridge", bd=2, width=46, height=8,
    )
    drop.pack(padx=20, pady=4, fill="x")
    drop.drop_target_register(DND_FILES)
    drop.dnd_bind("<<Drop>>", on_drop)

    tk.Button(root, text="…ou clique para escolher o arquivo", command=escolher).pack(pady=10)

    status_var = StringVar(value="Aguardando arquivo…")
    tk.Label(
        root, textvariable=status_var, justify="left", wraplength=560,
        bg="#f3f4f6", fg="#111827", font=("Helvetica", 11),
    ).pack(padx=20, pady=(8, 16), fill="x")

    root.mainloop()


if __name__ == "__main__":
    run_app()
