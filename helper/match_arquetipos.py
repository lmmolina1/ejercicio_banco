"""
Utilities for loading the arquetipos CSV and matching process codes
between a SQL result DataFrame and the arquetipos file.

Functions:
- load_arquetipos(path): carga el CSV y devuelve el DataFrame original
  y una versión 'exploded' con una fila por código de proceso.
- match_codes(df_sql, df_arq_exploded, sql_code_col): une `df_sql`
  con los arquetipos y devuelve un DataFrame con las coincidencias.

Uso (en notebook):
from helper.match_arquetipos import load_arquetipos, match_codes
df_arq, df_arq_expl = load_arquetipos('data/arquetipos.csv')
result, merged = match_codes(df, df_arq_expl, sql_code_col='codigo_proceso')
"""
from typing import Tuple
import pandas as pd


def load_arquetipos(path: str = 'data/arquetipos.csv') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Carga el CSV de arquetipos y devuelve dos DataFrames:
    - df: original con columna de lista `proc_list`
    - df_exploded: dataframe con una fila por código de proceso (`proc_code`)

    La función intenta detectar la columna que contiene los códigos buscando
    'Procesos' en el nombre de la columna. Normaliza espacios y filtra
    valores no aplicables como 'No existen procesos AS-IS actualmente' o
    'Por definir'.
    """
    df = pd.read_csv(path, dtype=str)

    # Detectar la columna que contiene los procesos potenciales
    candidates = [c for c in df.columns if 'Procesos' in c or 'procesos' in c]
    if candidates:
        proc_col = candidates[0]
    else:
        # Fallback to a common name
        proc_col = 'Procesos Potenciales As Is'

    df[proc_col] = df[proc_col].fillna('').astype(str)

    def split_codes(cell: str):
        cell = cell or ''
        parts = [p.strip() for p in cell.split(',') if p is not None]
        # Filtrar valores que no son códigos
        filtered = [p for p in parts if p and p.upper() not in (
            'NO EXISTEN PROCESOS AS-IS ACTUALMENTE', 'POR DEFINIR')]
        return filtered

    df['proc_list'] = df[proc_col].apply(split_codes)

    # Explode to one code per row for easy matching
    df_expl = df.explode('proc_list').rename(columns={'proc_list': 'proc_code'})
    if 'proc_code' in df_expl.columns:
        df_expl['proc_code'] = df_expl['proc_code'].astype(str).str.strip()

    return df, df_expl


def match_codes(df_sql: pd.DataFrame, df_arq_exploded: pd.DataFrame,
                sql_code_col: str = 'codigo_proceso') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Busca, para cada fila de `df_sql`, todas las coincidencias en los
    arquetipos (df_arq_exploded). Retorna:
    - result: `df_sql` enriquecido con columnas: `matched_proc_codes`,
      `matched_codigo_arquetipo`, `matched_nombre_arquetipo` (listas o NaN)
    - merged: el merge 'long form' que contiene una fila por (sql_row, arquetipo)

    `sql_code_col` es el nombre de la columna en `df_sql` que contiene el
    código de proceso a buscar. Ambos lados se comparan como strings.
    """
    if sql_code_col not in df_sql.columns:
        raise KeyError(f"Columna {sql_code_col} no encontrada en df_sql")

    df_sql = df_sql.copy()
    df_sql[sql_code_col] = df_sql[sql_code_col].astype(str).str.strip()

    # Asegurar que la columna de códigos en arquetipos se llame 'proc_code'
    if 'proc_code' not in df_arq_exploded.columns:
        raise KeyError('df_arq_exploded debe contener la columna "proc_code"')

    df_arq_exploded = df_arq_exploded.copy()
    df_arq_exploded['proc_code'] = df_arq_exploded['proc_code'].astype(str).str.strip()

    # Merge largo: cada coincidencia produce una fila
    merged = df_sql.merge(
        df_arq_exploded,
        left_on=sql_code_col,
        right_on='proc_code',
        how='left',
        suffixes=('', '_arq')
    )

    # Agrupar por índice original de df_sql para recolectar todas las coincidencias
    grouped = merged.groupby(merged.index).agg({
        'proc_code': lambda s: [v for v in s.dropna().unique()],
        # Las columnas del arquetipo pueden variar; intentamos recoger las más comunes
        'Código Arquetipo': lambda s: [v for v in s.dropna().unique()] if 'Código Arquetipo' in merged.columns else [],
        'Nombre Arquetipo': lambda s: [v for v in s.dropna().unique()] if 'Nombre Arquetipo' in merged.columns else [],
    })

    # Renombrar columnas agrupadas
    grouped = grouped.rename(columns={
        'proc_code': 'matched_proc_codes',
        'Código Arquetipo': 'matched_codigo_arquetipo',
        'Nombre Arquetipo': 'matched_nombre_arquetipo'
    })

    # Unir con df_sql usando .join() para garantizar alineación de índice
    # Primero, obtener solo las columnas de matches para asegurar que no hay duplicados
    result = df_sql.join(grouped, how='left')

    # Normalizar listas vacías a NaN para claridad
    for c in ['matched_proc_codes', 'matched_codigo_arquetipo', 'matched_nombre_arquetipo']:
        if c in result.columns:
            result[c] = result[c].apply(lambda x: x if x and any(pd.notna(v) for v in x) else pd.NA)

    return result, merged
