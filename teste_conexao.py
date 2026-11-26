# Rode este arquivo na mesma pasta do config.py
import mysql.connector
import config

print("config usado:", config.__file__)
print("host:", repr(config.host), "| user:", repr(config.user), "| database:", repr(config.database))

try:
    con = mysql.connector.connect(
        host=config.host.strip(), user=config.user.strip(),
        password=config.password, database=config.database.strip(),
        connection_timeout=10,
    )
except Exception as e:
    print("\nFALHOU AO CONECTAR:", type(e).__name__, "-", e)
    raise SystemExit(1)

print("\nConectou! MySQL", con.get_server_info())
cur = con.cursor()
for tabela in ("g06_Administradores", "g06_Leitores", "g06_Livros"):
    print(f"\n--- {tabela} ---")
    try:
        cur.execute(f"DESCRIBE {tabela}")
        for col in cur.fetchall():
            print(col[0], "|", col[1], "| nulo:", col[2], "| chave:", col[3])
    except Exception as e:
        print("Erro:", e)
cur.close()
con.close()