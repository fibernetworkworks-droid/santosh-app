"""SQL checks done in code before anything reaches her database.

* `split` cuts text into statements (quotes, "identifiers", $tag$ dollar quotes $tag$, -- and /* */ comments respected).
* `read_problem` = why a statement may NOT run as a read (one statement, SELECT / WITH / VALUES / TABLE / EXPLAIN /
  SHOW only, no side-effect functions). Reads also run inside a READ ONLY transaction, so this is the second lock.
* `write_check` = kind + danger notes for a change (runs only after her tap), or a refusal for things Hoola never runs
  (ALTER SYSTEM, COPY with files / programs, roles with passwords, DROP DATABASE, transaction control inside the text).
"""
from __future__ import annotations

import re

MAX_SQL = 20_000
MAX_WRITE_STATEMENTS = 20

READ_START = {"select", "with", "values", "table", "explain", "show"}
# Functions that do something even inside a READ ONLY transaction (or read the server's files / reach out).
BAD_FUNCS = re.compile(
    r"\b(pg_terminate_backend|pg_cancel_backend|pg_reload_conf|pg_rotate_logfile|pg_read_file|pg_read_binary_file|"
    r"pg_ls_\w+|pg_stat_file|lo_\w+|dblink\w*|pg_advisory\w*|pg_try_advisory\w*|pg_notify|pg_logical_\w+|"
    r"pg_create_\w+|pg_drop_\w+|pg_replication_\w+|pg_switch_wal|pg_promote|pg_backup_\w+|pg_start_backup|"
    r"pg_stop_backup|set_config|pg_sleep\w*|pg_import_system_collations|txid_\w+|pg_current_xact_id|"
    r"pg_wal_replay_\w+|pg_log_backend_memory_contexts|query_to_xml\w*|table_to_xml\w*|cursor_to_xml\w*|"
    r"database_to_xml\w*|schema_to_xml\w*|xmlparse|pg_file_\w+|copy_\w+_program)\s*\(", re.I)
NEVER = [
    (re.compile(r"^\s*alter\s+system\b", re.I), "ALTER SYSTEM (server settings) Hoola kabhi nahi chalata."),
    (re.compile(r"^\s*copy\b.*\b(program|from\s+'|to\s+')", re.I | re.S), "COPY se server ki file / program: kabhi nahi."),
    (re.compile(r"^\s*(create|alter)\s+(role|user)\b.*\bpassword\b", re.I | re.S),
     "Password wala ROLE / USER: password chat mein nahi aate. Yeh database console mein khud karein."),
    (re.compile(r"^\s*drop\s+(database|tablespace)\b", re.I), "Poora database / tablespace mitana: yeh aap khud console se karein."),
    (re.compile(r"^\s*(begin|commit|rollback|start\s+transaction|end|savepoint|release|abort)\b", re.I),
     "BEGIN / COMMIT mat likhiye: Hoola poore badlav ko khud ek transaction mein chalata hai (sab ya kuch nahi)."),
    (re.compile(r"^\s*(load|create\s+(or\s+replace\s+)?language|create\s+extension\s+\w*untrusted)\b", re.I),
     "LOAD / naya language: kabhi nahi."),
]
DANGER = [
    (re.compile(r"^\s*drop\b", re.I), "DROP: cheez hamesha ke liye hat jayegi."),
    (re.compile(r"^\s*truncate\b", re.I), "TRUNCATE: table ki saari rows mit jayengi."),
    (re.compile(r"^\s*alter\s+table\b.*\bdrop\b", re.I | re.S), "ALTER TABLE ... DROP: column / constraint hat jayega."),
    (re.compile(r"^\s*(grant|revoke)\b", re.I), "GRANT / REVOKE: kaun kya dekh / badal sakta hai, woh badlega."),
    (re.compile(r"^\s*(alter|drop|create)\s+(role|user|policy)\b", re.I), "Role / policy ka badlav: access badlega."),
    (re.compile(r"^\s*alter\s+table\b.*\b(disable\s+row\s+level|no\s+force\s+row)", re.I | re.S),
     "Row level security band ho raha hai."),
]


class SqlError(ValueError):
    pass


def split(sql: str) -> list[str]:
    out, buf, i, n = [], [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "-" and sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            buf.append(" ")
            i = j
            continue
        if c == "/" and sql.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if sql.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif sql.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            if depth:
                raise SqlError("Comment /* band nahi hua.")
            buf.append(" ")
            i = j
            continue
        if c in ("'", '"'):
            j = i + 1
            while True:
                k = sql.find(c, j)
                if k < 0:
                    raise SqlError("Quote band nahi hua.")
                if sql.startswith(c * 2, k):
                    j = k + 2
                    continue
                break
            buf.append(sql[i:k + 1])
            i = k + 1
            continue
        if c == "$":
            m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$", sql[i:])
            if m:
                tag = m.group(0)
                k = sql.find(tag, i + len(tag))
                if k < 0:
                    raise SqlError("$$ quote band nahi hua.")
                buf.append(sql[i:k + len(tag)])
                i = k + len(tag)
                continue
        if c == ";":
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    s = "".join(buf).strip()
    if s:
        out.append(s)
    return out


def _bare(stmt: str) -> str:
    """Statement with string / quoted contents blanked, for word checks."""
    s = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$.*?\$\1\$", "''", stmt, flags=re.S)
    s = re.sub(r"'(?:[^']|'')*'", "''", s)
    return s


def first_word(stmt: str) -> str:
    m = re.match(r"\s*\(*\s*([A-Za-z]+)", stmt)
    return (m.group(1) if m else "").lower()


def one(sql: str) -> str:
    sql = (sql or "").strip()
    if not sql:
        raise SqlError("SQL khaali hai.")
    if len(sql) > MAX_SQL:
        raise SqlError(f"SQL bahut lamba hai ({len(sql)} akshar; {MAX_SQL} tak).")
    parts = split(sql)
    if len(parts) != 1:
        raise SqlError("Ek baar mein ek hi SELECT chalaiye (';' se alag kai statements nahi).")
    return parts[0]


def read_problem(stmt: str) -> str:
    w = first_word(stmt)
    bare = _bare(stmt)
    if w not in READ_START:
        return f"'{w.upper() or '?'}' padhne wala query nahi hai: badlav ke liye action=write (aapki haan ke baad chalega)."
    if w == "explain":
        m = re.match(r"\s*explain\s*(\((?P<opts>[^)]*)\))?\s*(?P<rest>.*)", bare, re.I | re.S)
        rest = (m.group("rest") if m else "")
        inner = re.sub(r"^(analy[sz]e|verbose|costs|buffers|format\s+\w+|\s)+", "", rest, flags=re.I).strip()
        if first_word(inner) not in ("select", "with", "values", "table"):
            return "EXPLAIN sirf SELECT / WITH par."
    if w == "with" and re.search(r"\b(insert|update|delete|merge)\b", bare, re.I):
        return "WITH ke andar INSERT / UPDATE / DELETE: yeh badlav hai, action=write."
    if re.search(r"\binto\b", bare, re.I) and w == "select":
        return "SELECT ... INTO naya table banata hai: action=write."
    if re.search(r"\bfor\s+(update|share|no\s+key\s+update|key\s+share)\b", bare, re.I):
        return "FOR UPDATE / SHARE rows ko lock karta hai: padhne mein iski zaroorat nahi."
    m = BAD_FUNCS.search(bare)
    if m:
        return f"{m.group(1)}() server par kuch karta hai / bahar jaata hai: Hoola ise nahi chalata."
    return ""


def check_read(sql: str) -> str:
    stmt = one(sql)
    p = read_problem(stmt)
    if p:
        raise SqlError(p)
    return stmt


def write_check(sql: str) -> dict:
    sql = (sql or "").strip()
    if not sql:
        raise SqlError("SQL khaali hai.")
    if len(sql) > MAX_SQL:
        raise SqlError(f"SQL bahut lamba hai ({len(sql)} akshar; {MAX_SQL} tak).")
    parts = split(sql)
    if not parts:
        raise SqlError("SQL khaali hai.")
    if len(parts) > MAX_WRITE_STATEMENTS:
        raise SqlError(f"Ek card mein {MAX_WRITE_STATEMENTS} statements tak.")
    danger: list[str] = []
    kinds: list[str] = []
    for p in parts:
        bare = _bare(p)
        for rx, why in NEVER:
            if rx.search(bare):
                raise SqlError(why)
        m = BAD_FUNCS.search(bare)
        if m and m.group(1).lower() not in ("set_config",):
            raise SqlError(f"{m.group(1)}() Hoola nahi chalata.")
        w = first_word(p)
        kinds.append(w)
        for rx, why in DANGER:
            if rx.search(bare) and why not in danger:
                danger.append(why)
        if w in ("update", "delete") and not re.search(r"\bwhere\b", bare, re.I):
            danger.append(f"{w.upper()} bina WHERE: poori table ki har row par lagega.")
    ddl = any(k in ("create", "alter", "drop", "truncate", "comment", "grant", "revoke", "reindex", "cluster", "vacuum",
                    "analyze", "refresh") for k in kinds)
    if any(k in ("vacuum",) for k in kinds) and len(parts) > 1:
        raise SqlError("VACUUM transaction ke andar nahi chalta: use akela bhejiye (ya console se).")
    if "vacuum" in kinds:
        raise SqlError("VACUUM transaction ke bahar chalta hai; yeh database console / scheduler se karein.")
    return {"statements": parts, "kinds": kinds, "kind": "schema" if ddl else "data", "danger": danger}
