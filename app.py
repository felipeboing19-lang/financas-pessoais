"""
Financas Pessoais - Flask App com MongoDB
Instalar: pip install flask gunicorn pymongo
Rodar:    python app.py
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from datetime import datetime
import os

# MongoDB
from pymongo import MongoClient

app = Flask(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
USUARIO    = os.environ.get("APP_USER",   "felipe.boing")
SENHA      = os.environ.get("APP_PASS",   "24Hsobvqi@")
app.secret_key = os.environ.get("SECRET_KEY", "chave-super-secreta-mude-isso")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 dias
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

MONGO_URI  = os.environ.get("MONGO_URI",
    "mongodb+srv://felipefinancas:dyB0N3tpgSaB4GF5@cluster0.rfrlqjc.mongodb.net/?appName=Cluster0"
)

# ─── MONGODB ─────────────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db     = client["financas"]
col    = db["dados"]

def carregar():
    doc = col.find_one({"_id": "principal"})
    if doc:
        doc.pop("_id", None)
        return doc
    return {
        "salarios":      {"A": 0.0, "B": 0.0},
        "despesas":      {},
        "poupanca":      0.0,
        "orcamento":     {"total": 0.0, "variaveis": []},
        "financiamento": {"saldo_devedor": 0.0, "parcela": 0.0, "meses_restantes": 0}
    }

def salvar(dados):
    dados["_id"] = "principal"
    col.replace_one({"_id": "principal"}, dados, upsert=True)

def mes_atual():
    return datetime.now().strftime("%Y-%m")

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logado"):
            # Return JSON 401 for API routes, redirect for page routes
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "erro": "nao autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        u = request.form.get("usuario", "").strip()
        s = request.form.get("senha",   "").strip()
        if u == USUARIO and s == SENHA:
            session.permanent = True
            session["logado"] = True
            return redirect(url_for("index"))
        erro = "Usuario ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── ROTAS ────────────────────────────────────────────────────────────────────
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

@app.route("/api/financiamento", methods=["POST"])
@login_required
def salvar_financiamento():
    body  = request.json
    dados = carregar()
    try:
        dados["financiamento"] = {
            "saldo_devedor":   float(body.get("saldo_devedor", 0)),
            "parcela":         float(body.get("parcela", 0)),
            "meses_restantes": int(body.get("meses_restantes", 0)),
        }
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/orcamento", methods=["POST"])
@login_required
def salvar_orcamento():
    body  = request.json
    dados = carregar()
    try:
        dados["orcamento"]["total"] = float(body.get("total", 0))
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/orcamento/variavel", methods=["POST"])
@login_required
def adicionar_variavel():
    body  = request.json
    dados = carregar()
    try:
        item = {
            "id":    datetime.now().isoformat(),
            "nome":  body["nome"],
            "gasto": float(body.get("gasto", 0)),
        }
        dados["orcamento"]["variaveis"].append(item)
        salvar(dados)
        return jsonify({"ok": True, "item": item})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/orcamento/variavel/<id>", methods=["PUT"])
@login_required
def atualizar_variavel(id):
    body  = request.json
    dados = carregar()
    try:
        for v in dados["orcamento"]["variaveis"]:
            if v["id"] == id:
                v["gasto"] = float(body.get("gasto", v["gasto"]))
                v["nome"]  = body.get("nome", v["nome"])
                break
        salvar(dados)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/orcamento/variavel/<id>", methods=["DELETE"])
@login_required
def remover_variavel(id):
    dados = carregar()
    dados["orcamento"]["variaveis"] = [
        v for v in dados["orcamento"]["variaveis"] if v["id"] != id
    ]
    salvar(dados)
    return jsonify({"ok": True})

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

@app.route("/api/despesas/<mes>/<path:id>", methods=["PUT"])
@login_required
def editar_despesa(mes, id):
    body  = request.json
    dados = carregar()
    try:
        lista    = dados.get("despesas", {}).get(mes, [])
        novo_mes = body.get("mes", mes)
        for d in lista:
            if d["id"] == id:
                d["desc"]  = body.get("desc",  d["desc"])
                d["valor"] = float(body.get("valor", d["valor"]))
                d["cat"]   = body.get("cat",   d["cat"])
                if novo_mes != mes:
                    dados["despesas"][mes] = [x for x in lista if x["id"] != id]
                    if not dados["despesas"][mes]:
                        del dados["despesas"][mes]
                    if novo_mes not in dados["despesas"]:
                        dados["despesas"][novo_mes] = []
                    d["mes"] = novo_mes
                    dados["despesas"][novo_mes].append(d)
                break
        salvar(dados)
        return jsonify({"ok": True})
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
    print("  Financas Pessoais rodando!")
    print(f"  PC:      http://localhost:5000")
    print(f"  Celular: http://{ip}:5000")
    print("="*52 + "\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)