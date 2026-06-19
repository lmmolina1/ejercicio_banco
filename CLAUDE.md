# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python 3.14 virtual environment at `.venv/` — always use `.venv\Scripts\python.exe` for pip commands.
- Jupyter kernel must be pointed to `.venv` in VS Code (top-right kernel selector).
- Install dependencies: `.venv\Scripts\python.exe -m pip install pandas`
- The notebook imports `helper/` via `sys.path.insert(0, os.getcwd())`, so the working directory of the kernel must be the repo root.

## Architecture

The project matches SQL process codes against a catalog of "arquetipos" (archetypes) and outputs a filtered CSV.

**Data flow:**
1. `data/query_actividades_proc_q_actual.csv` — SQL result with columns `t1.id_epica`, `t1.periodo`, `codigo_proceso`, `t2.procedimiento`, `t2.actividad`.
2. `data/arquetipos.csv` — Archetype catalog. The column containing process codes is auto-detected by searching for `'Procesos'` in the column name.
3. `data/output/resultado_matching_arquetipos.csv` — Always overwritten (no timestamp suffix).

**Key modules:**

- `helper/match_arquetipos.py` — Core logic:
  - `load_arquetipos(path)` → `(df_original, df_exploded)`. Splits the comma-separated process codes column into one code per row.
  - `match_codes(df_sql, df_arq_exploded, sql_code_col)` → `(result, merged)`. Left-joins SQL rows to arquetipos, groups by original row index to collect all matches, and returns `matched_proc_codes`, `matched_codigo_arquetipo`, `matched_nombre_arquetipo` as clean comma-separated strings (not lists).

- `helper/helper.py` — `Helper` class for pyodbc DB connections (`obtener_dataframe`) and a `Logger` wrapper around `logging`.

- `sql/lz/consulta_data_liq_proc.sql` — Source query that joins process assignments (`cdeproc_sabana_procesos_beneficios`) with liquid data activities (`bpms_data_liquida`) filtered to period `2026Q1`.

**Notebook (`validador_proc_arquetipos.ipynb`) cell order:**
1. Load CSV into `df`.
2. Import helpers (with `importlib.reload` to avoid stale cache), run `match_codes`, apply `_list_to_str` cleanup on `matched_*` columns, filter to `result_filtered`.
3. Save `result_filtered` to `data/output/resultado_matching_arquetipos.csv` (overwrite).

## Important behaviors

- `match_arquetipos.py` is cached by the kernel after first import. The notebook forces `importlib.reload` before every use — do not remove this.
- `matched_*` columns must be plain strings in the output, never Python list reprs like `['value']`. The `_list_to_str` helper in the notebook and `list_to_str` in `match_arquetipos.py` both enforce this.
- Arquetipo rows with `'No existen procesos AS-IS actualmente'` or `'Por definir'` are filtered out during `load_arquetipos`.
