import pandas as pd
import numpy as np
from pathlib import Path

def transform_new_to_standard_comercial(df_new: pd.DataFrame) -> pd.DataFrame:
    df = df_new.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {
        'Ano/Mês': 'ANO_MES',
        'Empresa': 'EMPRESA',
        'Origem do Recurso': 'ORIGEM_RECURSOS',
        'Estágio da Obra': 'ESTAGIO_OBRA',
        'Bairro': 'BAIRRO',
        'Área': 'AREA',
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
        'AREA', 'QUANTIDADE', 'QTD_GARAGEM', 'QTD_ELEVADORES',
        'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Derivadas (padrão)
    df['AREA_QUANTIDADE'] = df['AREA'] * df['QUANTIDADE']
    # Mesmo vocabulário do padrão legado usado no residencial.
    if 'ORIGEM_RECURSOS' in df.columns:
        df['ORIGEM_RECURSOS'] = df['ORIGEM_RECURSOS'].replace({'Financiamento Bancário': 'Finan. Bancário'})

    df['AREA_VALOR'] = df['AREA'] * df['VALOR_MEDIO_M2']
    df['AREA_QUANTIDADE_VALOR'] = df['AREA'] * df['QUANTIDADE'] * df['VALOR_MEDIO_M2']

    # Ordem final igual ao padrão comercial
    cols = [
        'ANO_MES', 'EMPRESA', 'ORIGEM_RECURSOS', 'ESTAGIO_OBRA', 'OFERTA_VENDA', 'BAIRRO',
        'TIPO_EDICAO', 'STATUS', 'AREA', 'QUANTIDADE', 'QTD_GARAGEM', 'QTD_ELEVADORES',
        'TEMPO_FINANCIAMENTO', 'VALOR_MEDIO_M2', 'EMPREENDIMENTO',
        'AREA_QUANTIDADE', 'AREA_VALOR', 'AREA_QUANTIDADE_VALOR'
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    return df[cols].copy()


def pick_files_and_convert_comercial():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception as e:
        raise RuntimeError(
            "Tkinter não está disponível no seu Python. "
            "No macOS, normalmente resolve instalando o Python do site python.org (vem com Tk)."
        ) from e

    root = tk.Tk()
    root.withdraw()
    root.update()

    input_file = filedialog.askopenfilename(
        title="Selecione o XLSX no formato NOVO (COMERCIAL)",
        filetypes=[("Excel files", "*.xlsx")]
    )
    if not input_file:
        return

    default_out_name = Path(input_file).with_name(Path(input_file).stem + "_convertido_padrao.xlsx")

    output_file = filedialog.asksaveasfilename(
        title="Salvar XLSX convertido (formato PADRÃO - COMERCIAL)",
        defaultextension=".xlsx",
        initialfile=default_out_name.name,
        initialdir=str(default_out_name.parent),
        filetypes=[("Excel files", "*.xlsx")]
    )
    if not output_file:
        return

    try:
        df_new = pd.read_excel(input_file)
        df_std = transform_new_to_standard_comercial(df_new)
        df_std.to_excel(output_file, index=False)
        messagebox.showinfo("Concluído", f"Arquivo gerado com sucesso:\n{output_file}")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha na conversão:\n{e}")


if __name__ == "__main__":
    pick_files_and_convert_comercial()
