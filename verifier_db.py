import sqlite3

for chemin in [
    "data/supervision_ils_dme.db",
    "scripts/supervision_ils_dme.db"
]:
    print("\n---", chemin, "---")
    conn = sqlite3.connect(chemin)

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    print("Tables :", tables)

    try:
        nb = conn.execute("SELECT COUNT(*) FROM mesures").fetchone()[0]
        print("Mesures :", nb)
    except Exception as e:
        print("Table mesures absente :", e)

    conn.close()
