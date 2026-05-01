import json, os
from pymongo import MongoClient

MONGO_URI = "mongodb+srv://felipefinancas:dyB0N3tpgSaB4GF5@cluster0.rfrlqjc.mongodb.net/?appName=Cluster0"
DATA_FILE = "financas_data.json"

if not os.path.exists(DATA_FILE):
    print(f"Arquivo {DATA_FILE} nao encontrado!")
    exit(1)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    dados = json.load(f)

client = MongoClient(MONGO_URI)
db  = client["financas"]
col = db["dados"]

dados["_id"] = "principal"
col.replace_one({"_id": "principal"}, dados, upsert=True)

print("Migracao concluida!")
print(f"  Salarios: A={dados['salarios']['A']} B={dados['salarios']['B']}")
print(f"  Meses com despesas: {len(dados.get('despesas', {}))}")
print(f"  Poupanca: {dados.get('poupanca', 0)}")