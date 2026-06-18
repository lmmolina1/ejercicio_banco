import logging
from typing import Any, Optional

import pandas as pd


class Logger:
    def __init__(self, nombre: str = 'helper'):
        self.nombre = nombre
        self.log = logging.getLogger(nombre)
        if not self.log.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            self.log.addHandler(handler)
            self.log.setLevel(logging.INFO)

    def warning(self, message: str) -> None:
        self.log.warning(message)

    def info(self, message: str) -> None:
        self.log.info(message)

    def debug(self, message: str) -> None:
        self.log.debug(message)

    def exception(self, exc: Exception) -> None:
        self.log.exception(exc)

    def _reportar(self, task_id: Any, message: str) -> None:
        self.info(f'{task_id}: {message}')


class Helper:
    def __init__(self, logger: Optional[Logger] = None, dsn: Optional[str] = None, username: Optional[str] = None,
                 password: Optional[str] = None, **kwargs: Any):
        self.logger = logger if isinstance(logger, Logger) else Logger(str(logger) if logger else 'helper')
        self.dsn = dsn
        self.username = username
        self.password = password
        self.fetch_size = kwargs.get('fetch_size', 1000)
        self._connection = None

    def _connect(self):
        if self._connection is None:
            if not self.dsn:
                raise ValueError('DSN no especificado para Helper')
            import pyodbc
            self._connection = pyodbc.connect(self.dsn, autocommit=True)
        return self._connection

    def obtener_dataframe(self, query: str, params: Optional[Any] = None) -> pd.DataFrame:
        self.logger.info('Ejecutando consulta a través de Helper')
        conn = self._connect()
        return pd.read_sql_query(query, conn, params=params)
