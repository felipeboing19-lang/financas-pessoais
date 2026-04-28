"""
💰 Finanças Pessoais - Flask App com Login
Instalar: pip install flask gunicorn
Rodar:    python app.py

⚙️  ALTERE AS CREDENCIAIS ABAIXO ANTES DE SUBIR:
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json, os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# ─── CONFIGURAÇÕES ────────────────────────────────────────────────────────────
USUARIO = os.environ.get("APP_USER",  "felipe")
SENHA   = os.environ.get("APP_PASS",  "minhasenha123")
app.secret_key = os.environ.get("SECRET_KEY", "chave-super-secreta-mude-isso")
DATA_FILE = os.environ.get("DATA_PATH", "financas_data.json")

# ─── DADOS ────────────────────────────────────────────────────────────────────
def carregar():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"salarios": {"A": 0.0, "B": 0.0}, "despesas": {}, "poupanca": 0.0}

def salvar(dados):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def mes_atual():
    return datetime.now().strftime("%Y-%m")

# ─── PROTEÇÃO DE ROTAS ────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        u = request.form.get("usuario", "").strip()
        s = request.form.get("senha", "").strip()
        if u == USUARIO and s == SENHA:
            session["logado"] = True
            return redirect(url_for("index"))
        erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── ROTAS PRINCIPAIS ─────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/api/dados")
@login_required
def get_dados():
    return jsonify(carregar())

@app.route("/api/salarios", methods=["POST"])
@login_required
def salvar_salarios():
    body  = request.json
    dados = carregar()
    try:
        dados["salarios"]["A"] = float(body.get("A", 0))
        dados["salarios"]["B"] = float(body.get("B", 0))
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/poupanca", methods=["POST"])
@login_required
def salvar_poupanca():
    body  = request.json
    dados = carregar()
    try:
        dados["poupanca"] = float(body.get("valor", 0))
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/despesas", methods=["POST"])
@login_required
def adicionar_despesa():
    body  = request.json
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
@login_required
def remover_despesa(mes, id):
    dados = carregar()
    lista = dados.get("despesas", {}).get(mes, [])
    dados["despesas"][mes] = [d for d in lista if d["id"] != id]
    if mes in dados["despesas"] and not dados["despesas"][mes]:
        del dados["despesas"][mes]
    salvar(dados)
    return jsonify({"ok": True})

# ─── MAIN ─────────────────────────────────────────────────────────────────────
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