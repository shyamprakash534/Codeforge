"""Small DB abstraction with SQLite default and PostgreSQL-ready DSN."""
import sqlite3
class DatabaseTool:
    def __init__(self,url='sqlite:///codeforge.db'):
        self.url=url; self.conn=None
    def connect(self):
        if self.url.startswith('sqlite:///'):
            self.conn=sqlite3.connect(self.url.removeprefix('sqlite:///')); return self.conn
        raise RuntimeError('PostgreSQL requires the optional psycopg dependency; use sqlite for the zero-config mode.')
    def execute(self,sql,params=()):
        if self.conn is None: self.connect()
        cur=self.conn.execute(sql,params); self.conn.commit(); return cur.fetchall()
