"""
💰 Finanças Pessoais - Flask App
Instalar: pip install flask gunicorn
Rodar:    python app.py
"""
from flask import Flask, render_template, request, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = os.environ.get("DATA_PATH", "financas_data.json")

def carregar():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"salarios": {"A": 0.0, "B": 0.0}, "despesas": {}}

def salvar(dados):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def mes_atual():
    return datetime.now().strftime("%Y-%m")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dados")
def get_dados():
    return jsonify(carregar())

@app.route("/api/salarios", methods=["POST"])
def salvar_salarios():
    body = request.json
    dados = carregar()
    try:
        dados["salarios"]["A"] = float(body.get("A", 0))
        dados["salarios"]["B"] = float(body.get("B", 0))
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/despesas", methods=["POST"])
def adicionar_despesa():
    body = request.json
    dados = carregar()
    try:
        mes = body.get("mes") or mes_atual()
        despesa = {
            "id":    datetime.now().isoformat(),
            "desc":  body["desc"],
            "valor": float(body["valor"]),
            "cat":   body.get("cat") or "Outros",
            "mes":   mes,
        }
        if mes not in dados["despesas"]:
            dados["despesas"][mes] = []
        dados["despesas"][mes].append(despesa)
        salvar(dados)
        return jsonify({"ok": True, "despesa": despesa})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/despesas/<mes>/<path:id>", methods=["DELETE"])
def remover_despesa(mes, id):
    dados = carregar()
    lista = dados.get("despesas", {}).get(mes, [])
    dados["despesas"][mes] = [d for d in lista if d["id"] != id]
    if mes in dados["despesas"] and not dados["despesas"][mes]:
        del dados["despesas"][mes]
    salvar(dados)
    return jsonify({"ok": True})

if __name__ == "__main__":
    import socket
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = "127.0.0.1"
    print("\n" + "="*52)
    print("  💰 Finanças Pessoais rodando!")
    print(f"  PC:      http://localhost:5000")
    print(f"  Celular: http://{ip}:5000")
    print("="*52 + "\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
