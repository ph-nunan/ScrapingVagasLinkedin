from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random
import tkinter as tk
from tkinter import simpledialog
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Caixa de diálogo para entrada de URL
root = tk.Tk()
root.withdraw()
url = simpledialog.askstring("LinkedIn Scraper", "Cole aqui o link da página de vagas do LinkedIn:")

if not url:
    print("❌ Nenhum link foi fornecido. Encerrando o script.")
    exit()

# Configuração do navegador
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
driver.get(url)

input("🔐 Faça login no LinkedIn no navegador aberto e pressione ENTER aqui para continuar...")

vagas = []
links_vagas_extraidas = set()  # Usado para evitar duplicação de links de vagas

def scrollar_descricao():
    try:
        descricao_area = driver.find_element(By.CLASS_NAME, 'jobs-description__content')
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", descricao_area)
        time.sleep(0.2)
    except:
        pass

def extrair_dados_vaga(card, index, total):
    try:
        start = time.time()
        driver.execute_script("arguments[0].scrollIntoView();", card)
        card.click()
        WebDriverWait(driver, 7).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'jobs-details__main-content'))
        )
        scrollar_descricao()

        try:
            titulo = card.find_element(By.CSS_SELECTOR, 'a.job-card-list__title--link').text.strip()
        except:
            titulo = ""

        try:
            empresa = card.find_element(By.CSS_SELECTOR, 'div.artdeco-entity-lockup__subtitle span').text.strip()
        except:
            empresa = ""

        try:
            descricao = driver.find_element(By.CLASS_NAME, 'jobs-description__content').text.strip()
        except:
            descricao = ""

        try:
            spans = driver.find_elements(By.CSS_SELECTOR, 'span.tvm__text.tvm__text--low-emphasis')
            data = next((s.text.strip() for s in spans if "há" in s.text), "")
        except:
            data = ""

        link = driver.current_url

        if link in links_vagas_extraidas:  # Evitar duplicação
            print(f"[INFO] Vaga {index+1}/{total} já extraída. Ignorando.")
            return None

        links_vagas_extraidas.add(link)  # Adiciona o link ao conjunto para evitar duplicação

        tempo_exec = round(time.time() - start, 2)
        print(f"✅ Vaga {index+1}/{total} extraída em {tempo_exec}s: {titulo[:50]}...")

        return {
            "Título": titulo,
            "Empresa": empresa,
            "Data de Publicação": data,
            "Resumo": descricao,
            "Link": link
        }
    except TimeoutException as e:
        print(f"[ERRO] Vaga {index+1}/{total} falhou por timeout: {e}")
        return None
    except Exception as e:
        print(f"[ERRO] Vaga {index+1}/{total} falhou: {e}")
        return None

def extrair_vagas_pagina():
    print("➡️ Iniciando extração de vagas desta página")
    inicio_pagina = time.time()

    vagas_extraidas = 0  # Para contar o número de vagas extraídas na página
    index = 0
    while True:
        cards = driver.find_elements(By.CLASS_NAME, 'job-card-container')
        total = len(cards)
        if index >= total:
            break
        vaga = extrair_dados_vaga(cards[index], index, total)
        if vaga:
            vagas.append(vaga)
            vagas_extraidas += 1
        index += 1
        time.sleep(random.uniform(0.5, 1.1))  # mais rápido, porém seguro

    duracao = round(time.time() - inicio_pagina, 2)
    print(f"⏱ Página finalizada em {duracao}s com {vagas_extraidas} vagas acumuladas.\n")
    
    return vagas_extraidas

def proxima_pagina(pagina_atual):
    try:
        proximo_botao = driver.find_element(By.XPATH, f'//button[@aria-label="Página {pagina_atual + 1}"]')
        driver.execute_script("arguments[0].click();", proximo_botao)
        WebDriverWait(driver, 10).until(
            EC.staleness_of(proximo_botao)
        )
        time.sleep(2)
        return True
    except NoSuchElementException:
        print("[INFO] Não há próxima página.")
        return False
    except Exception as e:
        print(f"[INFO] Falha ao carregar próxima página: {e}")
        return False

def atualizar_pagina():
    print("🔄 Atualizando a página devido à quantidade insuficiente de vagas...")
    driver.refresh()
    time.sleep(5)

# Loop principal
pagina = 1
print("📅 Início da extração:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
while True:
    print(f"\n📄 Página {pagina}")
    vagas_extraidas = extrair_vagas_pagina()

    # Se menos de 25 vagas foram extraídas, atualiza a página e recomeça
    if vagas_extraidas < 25:
        atualizar_pagina()
        
        # Verifica se a atualização não resultou em novas vagas extraídas
        vagas_extraidas_atualizadas = extrair_vagas_pagina()
        if vagas_extraidas_atualizadas == 0:  # Se não houver vagas extraídas
            print(f"📄 Página {pagina} já foi totalmente explorada e não há novas vagas.")
            # Vai para a próxima página sem ficar tentando as mesmas vagas
            if not proxima_pagina(pagina):
                break
            pagina += 1
        else:
            print(f"📄 Página {pagina} tem novas vagas após atualização.")
    else:
        # Caso contrário, vai para a próxima página
        if not proxima_pagina(pagina):
            break
        pagina += 1

# Salvar os dados
if vagas:
    df = pd.DataFrame(vagas)
    nome_arquivo = f"vagas_linkedin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(nome_arquivo, index=False)
    print(f"✅ Vagas salvas em '{nome_arquivo}'")
else:
    print("❌ Nenhuma vaga foi extraída.")

driver.quit()