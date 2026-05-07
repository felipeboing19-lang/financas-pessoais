"""
Bot Telegram - Financas Pessoais
Instalar: pip install pyTelegramBotAPI SpeechRecognition requests pyogg
Rodar:    python bot.py
"""
import telebot
import os, re, ssl, tempfile, urllib.request, json
from pymongo import MongoClient
from datetime import datetime
import speech_recognition as sr

ssl._create_default_https_context = ssl._create_unverified_context

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8668862795:AAFpa5dNjKQSQYnKy5SGRC1Pix2t2Rxo5tw")
MONGO_URI      = os.environ.get("MONGO_URI", "mongodb+srv://felipefinancas:dyB0N3tpgSaB4GF5@cluster0.rfrlqjc.mongodb.net/?appName=Cluster0")
USUARIOS_AUTH  = os.environ.get("TELEGRAM_USERS", "").split(",")

bot    = telebot.TeleBot(TELEGRAM_TOKEN)
client = MongoClient(MONGO_URI)
col    = client["financas"]["dados"]

# ── DB ────────────────────────────────────────────────────────────────────────
def carregar():
    doc = col.find_one({"_id": "principal"})
    if doc:
        doc.pop("_id", None)
        return doc
    return {"salarios":{"A":0,"B":0},"despesas":{},"poupanca":0,
            "orcamento":{"total":0,"variaveis":[]},"financiamento":{}}

def salvar(dados):
    dados["_id"] = "principal"
    col.replace_one({"_id": "principal"}, dados, upsert=True)

def mes_atual():
    return datetime.now().strftime("%Y-%m")

def brl(v):
    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")

def autorizado(msg):
    uid = str(msg.from_user.id)
    if not USUARIOS_AUTH or USUARIOS_AUTH == ['']:
        return True
    return uid in USUARIOS_AUTH

# ── NUMEROS POR EXTENSO ───────────────────────────────────────────────────────
EXTENSO = {
    'zero':0,'um':1,'uma':1,'dois':2,'duas':2,'tres':3,'tres':3,'quatro':4,
    'cinco':5,'seis':6,'sete':7,'oito':8,'nove':9,'dez':10,
    'onze':11,'doze':12,'treze':13,'quatorze':14,'quinze':15,
    'dezesseis':16,'dezessete':17,'dezoito':18,'dezenove':19,'vinte':20,
    'trinta':30,'quarenta':40,'cinquenta':50,'sessenta':60,
    'setenta':70,'oitenta':80,'noventa':90,'cem':100,'cento':100,
    'duzentos':200,'duzentas':200,'trezentos':300,'trezentas':300,
    'quatrocentos':400,'quinhentos':500,'quinhentas':500,
    'seiscentos':600,'setecentos':700,'oitocentos':800,'novecentos':900,
    'mil':1000
}

def extenso_para_numero(texto):
    texto = texto.lower()
    texto = texto.replace('reais','').replace('real','')
    texto = texto.replace('e meio','e 500').replace('meia','500')
    texto = texto.replace(',','').strip()

    palavras = texto.split()
    resultado = 0
    atual = 0
    i = 0

    while i < len(palavras):
        p = palavras[i]
        proximo = palavras[i+1] if i+1 < len(palavras) else ''

        if p == 'mil':
            if atual == 0: atual = 1
            resultado += atual * 1000
            atual = 0
        elif p in EXTENSO:
            # se proximo e "mil", multiplica direto
            if proximo == 'mil':
                resultado += EXTENSO[p] * 1000
                atual = 0
                i += 1  # pula "mil"
            else:
                atual += EXTENSO[p]
        else:
            # numero direto ex: "20", "5", "2"
            try:
                n = int(float(p.replace(',','.')))
                if proximo == 'mil':
                    resultado += n * 1000
                    atual = 0
                    i += 1  # pula "mil"
                else:
                    atual += n
            except:
                pass
        i += 1

    total = resultado + atual
    return total if total > 0 else None

# ── PROCESSAR GASTO ───────────────────────────────────────────────────────────
def limpar_numero(s):
    """Converte '20.000' ou '1.500,50' ou '150' para float"""
    s = s.strip()
    # formato brasileiro: 20.000 ou 1.500,50
    if '.' in s and ',' not in s:
        # pode ser separador de milhar: 20.000 -> 20000
        # ou decimal americano: 20.5
        partes = s.split('.')
        if len(partes[-1]) == 3:
            # e separador de milhar: 20.000, 1.500
            return float(s.replace('.', ''))
        else:
            return float(s)
    elif ',' in s:
        # formato brasileiro: 1.500,50
        return float(s.replace('.', '').replace(',', '.'))
    else:
        return float(s)

def processar_gasto(texto, msg):
    texto = texto.lower().strip()
    valor = None
    nome  = None

    # Padrao com numero formatado: "gasto mercado 20.000" ou "gasto carro 1.500,00"
    m1 = re.search(r'gast(?:o|ei|ar)?\s+(\w+)\s+([\d.,]+)', texto)
    # Padrao invertido: "20.000 no mercado"
    m2 = re.search(r'([\d.,]+)\s*(?:reais?|r\$)?\s*(?:no|na|em|do|da)?\s*(\w+)', texto)

    if m1:
        nome = m1.group(1).capitalize()
        try: valor = limpar_numero(m1.group(2))
        except: pass
    elif m2:
        try: valor = limpar_numero(m2.group(1))
        except: pass
        nome = m2.group(2).capitalize()

    if not valor:
        valor = extenso_para_numero(texto)

    if not nome:
        ignorar = {'gasto','gastei','gastar','reais','real','paguei','no',
                   'na','em','do','da','de','um','uma','e','o','a','pagar'}
        palavras = [p for p in texto.split()
                   if p not in ignorar and not re.match(r'[\d.,]+', p)
                   and p not in EXTENSO]
        if palavras:
            nome = palavras[0].capitalize()

    if not valor or not nome:
        bot.reply_to(msg,
            "Nao entendi. Tente:\n`gasto mercado 150`\nou fale: _gasto mercado cento e cinquenta_",
            parse_mode="Markdown")
        return

    dados = carregar()
    if "orcamento" not in dados:
        dados["orcamento"] = {"total":0,"variaveis":[]}
    if "variaveis" not in dados["orcamento"]:
        dados["orcamento"]["variaveis"] = []

    dados["orcamento"]["variaveis"].append({
        "id": datetime.now().isoformat(),
        "nome": nome,
        "gasto": valor
    })
    salvar(dados)

    total = sum(v["gasto"] for v in dados["orcamento"]["variaveis"])
    orc   = dados["orcamento"].get("total", 0)
    resp  = f"✅ *{nome}* adicionado!\n💸 Valor: *{brl(valor)}*\n📊 Total variaveis: *{brl(total)}*"
    if orc > 0:
        resp += f"\n💰 Restante: *{brl(orc-total)}*"
    bot.reply_to(msg, resp, parse_mode="Markdown")

# ── AUDIO - usa Telegram file_id para baixar e Google Speech para transcrever ──
def transcrever_ogg(ogg_path):
    """Converte OGG Opus para WAV usando wave + audioop puros do Python"""
    try:
        import wave, audioop, struct, io

        # Tenta ler como OGG Opus via ctypes (Windows tem codec nativo)
        # Alternativa: usa subprocess para converter com tools do sistema
        wav_path = ogg_path.replace('.ogg', '.wav')

        # Tenta PowerShell no Windows para converter (nativo)
        ret = os.system(
            f'powershell -Command "'
            f'Add-Type -AssemblyName PresentationCore; '
            f'$player = New-Object System.Windows.Media.MediaPlayer; '
            f'"'
        )

        # Abordagem mais direta: usa SpeechRecognition com microfone virtual
        # Nao funciona sem ffmpeg para OGG

        # MELHOR ABORDAGEM: baixar como MP3 nao esta disponivel no Telegram
        # Usar Google Cloud Speech direto com OGG/OPUS que ele suporta nativamente!

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with open(ogg_path, 'rb') as f:
            audio_content = f.read()

        import base64
        audio_b64 = base64.b64encode(audio_content).decode('utf-8')

        # Google Cloud Speech REST API - aceita OGG_OPUS nativamente
        # Usando endpoint publico (sem chave para pt-BR curto)
        url = "https://speech.googleapis.com/v1/speech:recognize"

        payload = json.dumps({
            "config": {
                "encoding": "OGG_OPUS",
                "sampleRateHertz": 48000,
                "languageCode": "pt-BR"
            },
            "audio": {
                "content": audio_b64
            }
        }).encode('utf-8')

        # Sem chave de API usa quota gratuita limitada
        req = urllib.request.Request(
            url + "?key=AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            result = json.loads(r.read().decode('utf-8'))
            results = result.get('results', [])
            if results:
                alt = results[0].get('alternatives', [])
                if alt:
                    return alt[0].get('transcript', '')
        return None

    except Exception as e:
        print(f"Erro transcricao: {e}")
        return None

# ── HANDLERS ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=['start','ajuda','help'])
def cmd_ajuda(msg):
    if not autorizado(msg): return
    bot.reply_to(msg,
        "💰 *Bot Financas Pessoais*\n\n"
        "*Adicionar gasto:*\n"
        "`gasto mercado 150`\n"
        "`gasto padaria 45.50`\n\n"
        "*Consultas:*\n"
        "`ver gastos`\n`ver despesas`\n`resumo`\n\n"
        "*Audio:* mande um audio falando o gasto\n\n"
        f"*Seu ID:* `{msg.from_user.id}`",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and
    any(m.text.lower().startswith(p) for p in ['gasto','gastei','gastar']))
def cmd_gasto(msg):
    if not autorizado(msg): return
    processar_gasto(msg.text, msg)

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('ver gastos'))
def cmd_ver_gastos(msg):
    if not autorizado(msg): return
    dados = carregar()
    variaveis = dados.get("orcamento",{}).get("variaveis",[])
    if not variaveis:
        bot.reply_to(msg, "Nenhum gasto variavel registrado."); return
    total = sum(v["gasto"] for v in variaveis)
    orc   = dados.get("orcamento",{}).get("total",0)
    linhas = [f"📊 *Gastos Variaveis - {mes_atual()}*\n"]
    for v in variaveis:
        linhas.append(f"• {v['nome']}: *{brl(v['gasto'])}*")
    linhas.append(f"\n💸 Total: *{brl(total)}*")
    if orc > 0:
        linhas += [f"💰 Orcamento: *{brl(orc)}*", f"✅ Restante: *{brl(orc-total)}*"]
    bot.reply_to(msg, "\n".join(linhas), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('ver despesas'))
def cmd_ver_despesas(msg):
    if not autorizado(msg): return
    dados = carregar()
    m = mes_atual()
    desps = dados.get("despesas",{}).get(m,[])
    if not desps:
        bot.reply_to(msg, f"Nenhuma despesa em {m}."); return
    total = sum(d["valor"] for d in desps)
    linhas = [f"🧾 *Despesas Fixas - {m}*\n"]
    for d in sorted(desps, key=lambda x: x["valor"], reverse=True):
        linhas.append(f"• {d['desc']}: *{brl(d['valor'])}*")
    linhas.append(f"\n💸 Total: *{brl(total)}*")
    bot.reply_to(msg, "\n".join(linhas), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'resumo')
def cmd_resumo(msg):
    if not autorizado(msg): return
    dados = carregar()
    m = mes_atual()
    renda   = (dados["salarios"].get("A",0)+dados["salarios"].get("B",0))
    total_d = sum(d["valor"] for d in dados.get("despesas",{}).get(m,[]))
    total_v = sum(v["gasto"] for v in dados.get("orcamento",{}).get("variaveis",[]))
    total   = total_d + total_v
    saldo   = renda - total
    pct     = (total/renda*100) if renda > 0 else 0
    bot.reply_to(msg,
        f"💰 *Resumo - {m}*\n\n"
        f"💼 Renda: *{brl(renda)}*\n"
        f"🧾 Fixas: *{brl(total_d)}*\n"
        f"💸 Variaveis: *{brl(total_v)}*\n"
        f"📊 Total: *{brl(total)}* ({pct:.1f}%)\n"
        f"{'✅' if saldo>=0 else '❌'} Saldo: *{brl(saldo)}*\n"
        f"🏦 Poupanca: *{brl(dados.get('poupanca',0))}*",
        parse_mode="Markdown")

@bot.message_handler(content_types=['voice'])
def cmd_voice(msg):
    if not autorizado(msg): return
    bot.reply_to(msg, "🎤 Processando audio...")
    try:
        file_info = bot.get_file(msg.voice.file_id)
        file_url  = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        tmp = tempfile.mktemp(suffix='.ogg')
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(file_url) as resp:
            with open(tmp, 'wb') as f:
                f.write(resp.read())

        texto = transcrever_ogg(tmp)
        if os.path.exists(tmp):
            os.remove(tmp)

        if not texto:
            bot.reply_to(msg,
                "Nao consegui entender o audio.\nUse texto: `gasto mercado 150`",
                parse_mode="Markdown")
            return

        bot.reply_to(msg, f"🎤 Entendi: _{texto}_", parse_mode="Markdown")
        processar_gasto(texto, msg)

    except Exception as e:
        print(f"Erro voice: {e}")
        bot.reply_to(msg, "Erro no audio. Use texto: `gasto mercado 150`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def cmd_desconhecido(msg):
    if not autorizado(msg): return
    bot.reply_to(msg, "Digite `ajuda` para ver os comandos.", parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot iniciado!")
    bot.infinity_polling()