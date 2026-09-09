"""Database abstraction supporting SQLite and PostgreSQL through one interface."""
import os, sqlite3

class DatabaseTool:
    def __init__(self,url=None):
        self.url=url or os.getenv('CODEFORGE_DB_URL','sqlite:///codeforge.db'); self.conn=None
    def connect(self):
        if self.url.startswith('sqlite:///'):
            self.conn=sqlite3.connect(self.url.removeprefix('sqlite:///')); return self.conn
        if self.url.startswith(('postgresql://','postgres://')):
            try: import psycopg
            except ImportError as exc: raise RuntimeError('Install the database extra to use PostgreSQL (psycopg).') from exc
            self.conn=psycopg.connect(self.url); return self.conn
        raise ValueError('Unsupported database URL; use sqlite:///... or postgresql://...')
    def execute(self,sql,params=()):
        if self.conn is None: self.connect()
        with self.conn.cursor() as cur:
            cur.execute(sql,params)
            rows=cur.fetchall() if cur.description else []
        self.conn.commit(); return rows
    def close(self):
        if self.conn: self.conn.close(); self.conn=None
