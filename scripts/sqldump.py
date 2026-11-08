"""Reader for the henry-5.0.0.sql PostgreSQL dump.

The dump consists of DDL followed by single-row INSERT statements. Foreign
keys are written as name lookups, e.g. (SELECT id from species WHERE iupac='x'),
and note links use (SELECT CURRVAL('henry_id_seq')). This module splits the
file into statements (quote- and parenthesis-aware, following the approach of
the earlier scan.py), classifies every value strictly, and executes the
inserts in file order with PostgreSQL semantics for SERIAL ids, CURRVAL and
scalar sub-selects.
"""
import re

HDR = re.compile(r"INSERT INTO (\w+)\s*\(([^)]*)\)\s*VALUES\s*\(")
RE_STR = re.compile(r"^'((?:[^']|'')*)'$", re.S)
RE_LOOKUP = re.compile(r"^\(SELECT id from (\w+) WHERE (\w+)='((?:[^']|'')*)'\)$", re.S)
RE_CURRVAL = re.compile(r"^\(SELECT CURRVAL\('(\w+)'\)\)$")


def statements(src):
    """Yield (start, end, table, cols, raw_values) for each INSERT in order.

    start/end are character offsets of the statement text, from 'INSERT' up to
    and including the terminating ';'.
    """
    i = 0
    n = len(src)
    while True:
        m = HDR.search(src, i)
        if not m:
            return
        j = m.end()
        depth = 1
        vals = []
        cur = []
        inq = False
        while depth > 0:
            if j >= n:
                raise ValueError("unterminated statement at offset %d" % m.start())
            c = src[j]
            if inq:
                if c == "'":
                    if j + 1 < n and src[j + 1] == "'":
                        cur.append("''")
                        j += 2
                        continue
                    inq = False
                cur.append(c)
            else:
                if c == "'":
                    inq = True
                    cur.append(c)
                elif c == "(":
                    depth += 1
                    cur.append(c)
                elif c == ")":
                    depth -= 1
                    if depth > 0:
                        cur.append(c)
                elif c == "," and depth == 1:
                    vals.append("".join(cur).strip())
                    cur = []
                else:
                    cur.append(c)
            j += 1
        vals.append("".join(cur).strip())
        if src[j] != ";":
            raise ValueError("statement at offset %d not terminated by ';'" % m.start())
        yield m.start(), j + 1, m.group(1), [c.strip() for c in m.group(2).split(",")], vals
        i = j + 1


def sql_unquote(s):
    return s.replace("''", "'")


def sql_quote(s):
    return "'" + s.replace("'", "''") + "'"


def classify(raw):
    """Return ('str', text) | ('lookup', table, column, text) | ('currval', seq)."""
    m = RE_STR.match(raw)
    if m:
        return ("str", sql_unquote(m.group(1)))
    m = RE_LOOKUP.match(raw)
    if m:
        return ("lookup", m.group(1), m.group(2), sql_unquote(m.group(3)))
    m = RE_CURRVAL.match(raw)
    if m:
        return ("currval", m.group(1))
    raise ValueError("unrecognised value form: %r" % raw[:200])


def execute(src):
    """Execute all INSERTs in order. Returns (tables, events, spans).

    tables: {table: [row dict]} with 'id' (SERIAL, 1-based in insert order),
            'sql_seq' (1-based statement number in the file) and, for every
            looked-up column, both the resolved id (None if no row matched)
            and the lookup key as written ('<col>__key').
    events: list of anomalies (lookup with no match, ambiguous lookups,
            primary-key collisions) in the order they occur.
    spans:  list of (start, end) offsets of every statement.
    """
    tables = {}
    index = {}      # (table, column) -> {value: [ids]} built incrementally
    seq_curr = {}   # sequence name -> current value
    events = []
    spans = []
    pk_seen = set()
    for seq, (a, b, table, cols, raws) in enumerate(statements(src), start=1):
        spans.append((a, b))
        if len(cols) != len(raws):
            raise ValueError("column/value count mismatch in statement %d" % seq)
        rows = tables.setdefault(table, [])
        row = {"sql_seq": seq}
        for col, raw in zip(cols, raws):
            col = col.lower()  # PostgreSQL folds unquoted identifiers
            kind = classify(raw)
            if kind[0] == "str":
                row[col] = kind[1]
            elif kind[0] == "lookup":
                _, lt, lc, key = kind
                ids = index.get((lt, lc), {}).get(key, [])
                if len(ids) == 1:
                    row[col] = ids[0]
                elif not ids:
                    row[col] = None
                    events.append({"sql_seq": seq, "table": table, "column": col,
                                   "event": "lookup_no_match",
                                   "detail": "%s.%s = %r matched no row inserted so far" % (lt, lc, key)})
                else:
                    row[col] = None
                    events.append({"sql_seq": seq, "table": table, "column": col,
                                   "event": "lookup_ambiguous",
                                   "detail": "%s.%s = %r matched ids %s (PostgreSQL would raise an error)" % (lt, lc, key, ids)})
                row[col + "__key"] = key
                row[col + "__lookup"] = (lt, lc)
            else:
                sname = kind[1]
                if sname not in seq_curr:
                    raise ValueError("CURRVAL before NEXTVAL in statement %d" % seq)
                row[col] = seq_curr[sname]
                row[col + "__currval"] = sname
        # SERIAL id: the sequence advances for every attempted insert
        sname = table + "_id_seq"
        seq_curr[sname] = seq_curr.get(sname, 0) + 1
        row["id"] = seq_curr[sname]
        if table == "henry_notes":
            pk = (row.get("henry_id"), row.get("notes_id"))
            if None in pk:
                events.append({"sql_seq": seq, "table": table, "column": "henry_id,notes_id",
                               "event": "pk_null", "detail": "primary key would contain NULL: %s" % (pk,)})
            elif pk in pk_seen:
                events.append({"sql_seq": seq, "table": table, "column": "henry_id,notes_id",
                               "event": "pk_duplicate", "detail": "duplicate primary key %s" % (pk,)})
            pk_seen.add(pk)
        rows.append(row)
        for col, val in row.items():
            if isinstance(val, str) and not col.endswith("__key"):
                index.setdefault((table, col), {}).setdefault(val, []).append(row["id"])
    return tables, events, spans
