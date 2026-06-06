import duckdb
c = duckdb.connect("data/lucia.duckdb")
for t in c.execute("SHOW TABLES").fetchall():
    n = c.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"{t[0]}: {n} rows")
c.close()
