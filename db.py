"""
PostgreSQL wrapper that mimics the Supabase Python SDK interface.
This allows app.py to keep the same .table().select().eq().execute() syntax
while using a local PostgreSQL database instead of Supabase cloud.
"""
import psycopg2
import psycopg2.extras
from datetime import datetime, date

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "haps",
    "user": "postgres",
    "password": "12345678"
}


def _get_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def _serialize(val):
    """Convert Python objects to JSON-safe types."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


class _Result:
    """Mimics Supabase response object with .data attribute."""
    def __init__(self, data):
        self.data = data


class _Query:
    """Chainable query builder that mimics Supabase SDK syntax."""

    def __init__(self, table):
        self._table = table
        self._op = None          # 'select', 'insert', 'update', 'delete'
        self._columns = "*"
        self._filters = []       # list of (column, value)
        self._order_col = None
        self._order_desc = False
        self._limit_val = None
        self._payload = None     # for insert / update
        self._returning = True

    # ---- operation setters ----
    def select(self, columns="*"):
        self._op = "select"
        self._columns = columns
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    # ---- filter / modifier chainers ----
    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, column, desc=False):
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    # ---- execute ----
    def execute(self):
        conn = _get_conn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if self._op == "select":
                return self._exec_select(cur)
            elif self._op == "insert":
                return self._exec_insert(cur)
            elif self._op == "update":
                return self._exec_update(cur)
            elif self._op == "delete":
                return self._exec_delete(cur)
            else:
                return _Result([])
        finally:
            conn.close()

    # ---- private helpers ----
    def _where_clause(self):
        if not self._filters:
            return "", []
        parts = []
        vals = []
        for col, val in self._filters:
            parts.append(f'"{col}" = %s')
            vals.append(val)
        return " WHERE " + " AND ".join(parts), vals

    def _exec_select(self, cur):
        where, vals = self._where_clause()
        sql = f'SELECT {self._columns} FROM "{self._table}"{where}'
        if self._order_col:
            direction = "DESC" if self._order_desc else "ASC"
            sql += f' ORDER BY "{self._order_col}" {direction}'
        if self._limit_val:
            sql += f" LIMIT {int(self._limit_val)}"
        cur.execute(sql, vals)
        rows = cur.fetchall()
        return _Result([{k: _serialize(v) for k, v in dict(r).items()} for r in rows])

    def _exec_insert(self, cur):
        rows_to_insert = self._payload if isinstance(self._payload, list) else [self._payload]
        all_results = []
        for row in rows_to_insert:
            cols = [k for k in row.keys()]
            col_names = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["%s"] * len(cols))
            vals = [row[c] for c in cols]
            sql = f'INSERT INTO "{self._table}" ({col_names}) VALUES ({placeholders}) RETURNING *'
            cur.execute(sql, vals)
            result = cur.fetchone()
            if result:
                all_results.append({k: _serialize(v) for k, v in dict(result).items()})
        return _Result(all_results)

    def _exec_update(self, cur):
        where, where_vals = self._where_clause()
        set_parts = []
        set_vals = []
        for k, v in self._payload.items():
            set_parts.append(f'"{k}" = %s')
            set_vals.append(v)
        sql = f'UPDATE "{self._table}" SET {", ".join(set_parts)}{where} RETURNING *'
        cur.execute(sql, set_vals + where_vals)
        rows = cur.fetchall()
        return _Result([{k: _serialize(v) for k, v in dict(r).items()} for r in rows])

    def _exec_delete(self, cur):
        where, vals = self._where_clause()
        sql = f'DELETE FROM "{self._table}"{where} RETURNING *'
        cur.execute(sql, vals)
        rows = cur.fetchall()
        return _Result([{k: _serialize(v) for k, v in dict(r).items()} for r in rows])


class PostgresClient:
    """Drop-in replacement for supabase.create_client() return value."""
    def table(self, name):
        return _Query(name)


def create_client():
    """Mimics supabase.create_client() — returns a PostgresClient."""
    return PostgresClient()
