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
USUARIO    = os.environ.get("APP_USER",   "1")
SENHA      = os.environ.get("APP_PASS",   "1")
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
            return redirect(url_for("home"))
        erro = "Usuario ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── ROTAS ────────────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/financas")
@login_required
def index():
    return render_template("index.html")

@app.route("/saude")
@login_required
def saude():
    return render_template("saude.html")

# ── SAUDE API ──────────────────────────────────────────────────────────────────
@app.route("/api/saude/registros")
@login_required
def get_registros():
    col_saude = client["financas"]["saude"]
    registros = list(col_saude.find({}, {"_id": 0}).sort("data", -1).limit(90))
    return jsonify(registros)

@app.route("/api/saude/registro", methods=["POST"])
@login_required
def salvar_registro():
    body = request.json
    col_saude = client["financas"]["saude"]
    try:
        data = body.get("data") or datetime.now().strftime("%Y-%m-%d")
        # upsert by date
        col_saude.replace_one({"data": data}, {**body, "data": data}, upsert=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400

@app.route("/api/saude/registro/<data>")
@login_required
def get_registro(data):
    col_saude = client["financas"]["saude"]
    reg = col_saude.find_one({"data": data}, {"_id": 0})
    return jsonify(reg or {})

@app.route("/api/saude/registro/<data>", methods=["DELETE"])
@login_required
def del_registro(data):
    col_saude = client["financas"]["saude"]
    col_saude.delete_one({"data": data})
    return jsonify({"ok": True})

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
def iniciar_bot():
    import time
    time.sleep(3)  # aguarda app subir
    try:
        TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
        if not TOKEN:
            print("TELEGRAM_TOKEN nao configurado - bot nao iniciado")
            return
        import telebot
        from pymongo import MongoClient
        # importa o modulo bot
        import bot as telegram_bot
        print("="*40)
        print("Bot Telegram INICIADO com sucesso!")
        print("="*40)
        telegram_bot.bot.infinity_polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"ERRO ao iniciar bot: {e}")
        import traceback
        traceback.print_exc()

# Inicia bot em thread tanto local quanto no Render
import threading
_bot_thread = threading.Thread(target=iniciar_bot, daemon=True)
_bot_thread.start()
print("Thread do bot iniciada!")

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