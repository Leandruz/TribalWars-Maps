import requests
import re
import json
import os
from datetime import datetime

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "Automação", "config.json")
RESULTADOS_DIR = os.path.join(BASE_DIR, "Resultados")

DOMAINS = {
    ".BR": "tribalwars.com.br",
    ".PT": "tribalwars.com.pt",
    ".NET": "tribalwars.net",
    ".DS": "die-staemme.de"
}

PREFIXES = {
    ".BR": "br",
    ".PT": "pt",
    ".NET": "en",
    ".DS": "de"
}

MESES = {
    "jan.": "01", "fev.": "02", "mar.": "03", "abr.": "04",
    "mai.": "05", "jun.": "06", "jul.": "07", "ago.": "08",
    "set.": "09", "out.": "10", "nov.": "11", "dez.": "12"
}

def normalize_date(tw_date):
    # Formato: 22/abr./2026 (09:30)
    match = re.search(r"(\d{1,2})/(\w{3}\.)/(\d{4})", tw_date)
    if match:
        dia, mes_pt, ano = match.groups()
        mes = MESES.get(mes_pt.lower(), "01")
        return f"{ano}-{mes}-{dia.zfill(2)}"
    return None

def get_world_start_date(world_id, domain):
    url = f"https://{world_id}.{domain}/page/settings"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            pattern = r"<td>Início</td>\s*<td>(.*?)</td>"
            match = re.search(pattern, resp.text)
            if match:
                return normalize_date(match.group(1))
    except:
        pass
    return None

def check_new_worlds():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    updates_made = False

    for server_group, known_worlds_list in config.get("servers", {}).items():
        if server_group not in DOMAINS:
            continue
            
        domain = DOMAINS[server_group]
        prefix = PREFIXES.get(server_group, server_group.strip(".").lower())
        known_worlds = set(known_worlds_list)
        
        # URL que lista mundos ativos (estatísticas)
        url = f"https://www.{domain}/page/settings"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                print(f"Erro ao acessar {url}")
                continue
            
            # Procura links como br142.tribalwars.com.br/page/stats ou brc2.tribalwars.com.br
            pattern = r"(" + prefix + r"[a-z]*\d+)\." + re.escape(domain)
            found_worlds = set(re.findall(pattern, resp.text))
            
            new_worlds = found_worlds - known_worlds
            
            if not new_worlds:
                print(f"Nenhum mundo novo detectado para {server_group}.")
                continue

            for mundo in sorted(list(new_worlds)):
                print(f">>> Novo mundo detectado: {mundo} ({server_group})")
                
                # 1. Pegar data
                start_date = get_world_start_date(mundo, domain)
                if not start_date:
                    start_date = datetime.now().strftime("%Y-%m-%d")
                    print(f"      Aviso: Data não encontrada para {mundo}, usando hoje ({start_date}).")
                
                # 2. Atualizar Config
                config["servers"][server_group].append(mundo)
                config["servers"][server_group].sort()
                
                if "server_start_dates" not in config:
                    config["server_start_dates"] = {}
                config["server_start_dates"][mundo] = start_date
                
                # 3. Criar Pastas
                pasta_mundo = os.path.join(RESULTADOS_DIR, server_group, mundo)
                os.makedirs(os.path.join(pasta_mundo, "Players"), exist_ok=True)
                os.makedirs(os.path.join(pasta_mundo, "Tribes"), exist_ok=True)
                print(f"      Pastas criadas em {pasta_mundo}")
                
                updates_made = True
                
        except Exception as e:
            print(f"Erro ao verificar novos mundos para {server_group}: {e}")

    if updates_made:
        # Salvar config
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("\nConfigurações atualizadas com sucesso!")
    else:
        print("\nNenhuma atualização necessária.")

if __name__ == "__main__":
    check_new_worlds()
