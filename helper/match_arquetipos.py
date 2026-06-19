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
import re
from typing import Tuple
 
import pandas as pd
 
# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
_SKIP_VALUES = frozenset({
    'NO EXISTEN PROCESOS AS-IS ACTUALMENTE',
    'POR DEFINIR',
})
 
# Internal sentinel: name of the helper column used to preserve the original
# df_sql index across the merge (pandas resets the index on merge by default).
_MERGE_IDX_COL = '__original_idx__'
 
 
# ──────────────────────────────────────────────────────────────────────────────
# load_arquetipos
# ──────────────────────────────────────────────────────────────────────────────
def load_arquetipos(path: str = 'data/arquetipos.csv') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Carga el CSV de arquetipos y devuelve dos DataFrames:
    - df: original con columna de lista `proc_list`
    - df_exploded: una fila por código de proceso (`proc_code`)
 
    BUG FIXED: split_codes ahora normaliza el separador '. ' (punto + espacio)
    convirtiéndolo a coma antes de hacer el split, lo que evita que entradas
    como 'T160112. PAN40308' queden como un único token en lugar de dos códigos
    separados.
    """
    df = pd.read_csv(path, dtype=str)
 
    # Detectar la columna que contiene los procesos potenciales
    candidates = [c for c in df.columns if 'Procesos' in c or 'procesos' in c]
    proc_col = candidates[0] if candidates else 'Procesos Potenciales As Is'
 
    df[proc_col] = df[proc_col].fillna('').astype(str)
 
    def split_codes(cell: str) -> list:
        # FIX: normalize '. ' (period + space) → ',' before splitting.
        # Source data sometimes uses a period instead of a comma as separator
        # (e.g., 'T160112. PAN40308'), which would otherwise produce a single
        # malformed token instead of two valid process codes.
        cell = re.sub(r'\.\s+', ',', cell)
 
        parts = [p.strip() for p in cell.split(',')]
        return [
            p for p in parts
            if p and p.upper() not in _SKIP_VALUES
        ]
 
    df['proc_list'] = df[proc_col].apply(split_codes)
 
    # Explode to one code per row for easy matching
    df_expl = df.explode('proc_list').rename(columns={'proc_list': 'proc_code'})
    df_expl['proc_code'] = df_expl['proc_code'].astype(str).str.strip()
 
    return df, df_expl
 
 
# ──────────────────────────────────────────────────────────────────────────────
# match_codes
# ──────────────────────────────────────────────────────────────────────────────
def match_codes(
    df_sql: pd.DataFrame,
    df_arq_exploded: pd.DataFrame,
    sql_code_col: str = 'codigo_proceso',
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Busca, para cada fila de `df_sql`, todas las coincidencias en los
    arquetipos (df_arq_exploded). Retorna:
    - result: `df_sql` enriquecido con columnas: `matched_proc_codes`,
      `matched_codigo_arquetipo`, `matched_nombre_arquetipo` (listas o pd.NA)
    - merged: el merge 'long form' con una fila por (sql_row × arquetipo)
 
    BUG FIXED: el código original hacía groupby(merged.index) después del
    merge. pandas resetea el índice en el merge (0, 1, 2, …), por lo que
    cada fila del merged tenía un índice único → el groupby creaba un grupo
    por fila (sin agregar nada). Al hacer df_sql.join(grouped), las filas
    del grouped —que eran más que las de df_sql cuando un código tenía varios
    arquetipos— quedaban desalineadas, asignando el arquetipo de otro proceso
    a la fila incorrecta.
 
    La corrección guarda el índice original de df_sql como columna
    (_MERGE_IDX_COL) ANTES del merge, agrupa por esa columna (que sobrevive
    el reset del índice), y hace el join de regreso sobre el índice original.
    Así, todos los arquetipos de un mismo proceso se consolidan correctamente
    en una sola fila.
    """
    if sql_code_col not in df_sql.columns:
        raise KeyError(f"Columna '{sql_code_col}' no encontrada en df_sql")
    if 'proc_code' not in df_arq_exploded.columns:
        raise KeyError('df_arq_exploded debe contener la columna "proc_code"')
 
    df_sql = df_sql.copy()
    df_sql[sql_code_col] = df_sql[sql_code_col].astype(str).str.strip()
 
    df_arq_exploded = df_arq_exploded.copy()
    df_arq_exploded['proc_code'] = df_arq_exploded['proc_code'].astype(str).str.strip()
 
    # ── FIX: preserve the original df_sql index before merging ───────────────
    # pandas.DataFrame.merge() resets the index of the result to 0, 1, 2, …
    # regardless of the input indices. We need to track which merged row came
    # from which original df_sql row so the groupby below aggregates correctly.
    df_sql[_MERGE_IDX_COL] = df_sql.index
 
    # Merge largo: cada coincidencia produce una fila
    merged = df_sql.merge(
        df_arq_exploded,
        left_on=sql_code_col,
        right_on='proc_code',
        how='left',
        suffixes=('', '_arq'),
    )
 
    # Detect archetype column names (handles any column-name variations)
    arq_code_col = next(
        (c for c in merged.columns if 'Código' in c and 'Arquetipo' in c), None
    )
    arq_name_col = next(
        (c for c in merged.columns if 'Nombre' in c and 'Arquetipo' in c), None
    )