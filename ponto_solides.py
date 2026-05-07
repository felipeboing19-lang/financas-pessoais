"""
Automação de Ponto - Tangerino (Solides)
Deixe rodando no terminal do VS Code. Ctrl+C para parar.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import logging
import sys
import os

# ============================================================
#   CONFIGURAÇÕES — EDITE AQUI
# ============================================================

CODIGO_EMPREGADOR = "SEU_CODIGO_AQUI"   # Ex: NH2XN
PIN               = "SEU_PIN_AQUI"      # Seu PIN numérico

URL = "https://app.tangerino.com.br/Tangerino/"

# Horários das 4 batidas (formato 24h "HH:MM")
HORARIOS = [
    "08:00",   # Entrada
    "12:00",   # Saída almoço
    "13:00",   # Retorno almoço
    "17:00",   # Fim do expediente
]

# Dias da semana (0=seg, 1=ter, 2=qua, 3=qui, 4=sex)
DIAS_UTEIS = [0, 1, 2, 3, 4]

# ============================================================

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%d/%m %H:%M:%S",
    handlers=[
        logging.FileHandler(
            os.path.join(log_dir, f"ponto_{datetime.now().strftime('%Y-%m')}.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def clicar_js(driver, texto_botao):
    """Clica em qualquer elemento clicável que contenha o texto informado."""
    return driver.execute_script("""
        var texto = arguments[0].toLowerCase();
        var elementos = document.querySelectorAll('button, a, input[type=submit], input[type=button]');
        for (var i = 0; i < elementos.length; i++) {
            var el = elementos[i];
            var t = (el.textContent || el.value || '').trim().toLowerCase();
            if (t === texto || t.startsWith(texto)) {
                el.scrollIntoView({block: 'center'});
                el.click();
                return el.tagName + ': ' + t;
            }
        }
        return null;
    """, texto_botao)


def bater_ponto():
    log.info("-" * 45)
    log.info("Iniciando batida de ponto...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)

        log.info("Acessando pagina...")
        driver.get(URL)
        time.sleep(4)

        # Clica na aba "Registrar Ponto"
        log.info("Clicando em 'Registrar Ponto'...")
        aba = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//*[contains(text(), 'Registrar Ponto') or contains(text(), 'Registrar ponto')]"
        )))
        driver.execute_script("arguments[0].click();", aba)
        time.sleep(3)

        # Campo: Código do Empregador
        log.info("Preenchendo codigo do empregador...")
        campo_codigo = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//label[contains(text(),'digo do Empregador')]/following::input[1]"
        )))
        campo_codigo.clear()
        campo_codigo.send_keys(CODIGO_EMPREGADOR)
        time.sleep(1)

        # Campo: PIN
        log.info("Preenchendo PIN...")
        campo_pin = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//label[contains(text(),'PIN')]/following::input[1]"
        )))
        campo_pin.clear()
        campo_pin.send_keys(PIN)
        time.sleep(1)

        # Clica em Registrar
        log.info("Clicando em Registrar...")
        clicou = clicar_js(driver, "registrar")
        log.info(f"   Clicou em: {clicou}")
        time.sleep(5)

        _screenshot(driver, "resultado")

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if any(p in page_text for p in ["registrado", "sucesso", "batida", "confirmado", "obrigado"]):
            log.info("PONTO REGISTRADO COM SUCESSO!")
        elif any(p in page_text for p in ["invalido", "erro", "error", "incorreto"]):
            log.error("ERRO ao registrar — verifique screenshot na pasta logs/")
        else:
            log.info("Resultado inconclusivo — verifique screenshot resultado_*.png em logs/")

    except Exception as e:
        log.error(f"Falha: {e}")
        if driver:
            _screenshot(driver, "excecao")
    finally:
        if driver:
            driver.quit()


def _screenshot(driver, prefixo):
    path = os.path.join(log_dir, f"{prefixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    try:
        driver.save_screenshot(path)
        log.info(f"   Screenshot: logs/{prefixo}_*.png")
    except Exception:
        pass


def proximo_horario(horarios, hora_atual):
    for h in sorted(horarios):
        if h > hora_atual:
            return h
    return None


def loop():
    log.info("=" * 45)
    log.info("  PONTO AUTOMATICO — TANGERINO/SOLIDES")
    log.info(f"  Horarios: {' | '.join(HORARIOS)}")
    log.info("  Dias: segunda a sexta")
    log.info("  Ctrl+C para parar")
    log.info("=" * 45)

    batidos_hoje = set()

    while True:
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        data_hoje = agora.strftime("%Y-%m-%d")
        dia_semana = agora.weekday()

        chave = f"{data_hoje}_{hora_atual}"

        if dia_semana in DIAS_UTEIS and hora_atual in HORARIOS and chave not in batidos_hoje:
            batidos_hoje.add(chave)
            bater_ponto()
            proximo = proximo_horario(HORARIOS, hora_atual)
            if proximo:
                log.info(f"   Proxima batida hoje: {proximo}")
            else:
                log.info("   Sem mais batidas hoje.")

        time.sleep(30)


if __name__ == "__main__":
    try:
        loop()
    except KeyboardInterrupt:
        log.info("\nEncerrado pelo usuario.")
