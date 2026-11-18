import json
import os
import time
import requests
import csv

PASTA = os.path.dirname(os.path.abspath(__file__))

# Cidades usadas pelo main.py (trabalho original). A interface (app.py) usa os 224 municípios.
CIDADES = ["Teresina", "Altos", "Campo Maior", "Piripiri", "Piracuruca",
           "Parnaíba", "Luís Correia", "José de Freitas", "União",
           "Barras", "Esperantina"]

OSRM = "https://router.project-osrm.org"
LIMITE_OSRM = 100   # o servidor público do OSRM aceita no máximo 100 pontos por pedido
BLOCO = 50          # acima do limite, a matriz é pedida em blocos de 50 x 50


def carregar_municipios_pi():
    """Lê os 224 municípios do Piauí (nome -> (lat, lon)) do arquivo municipios_pi.json."""
    with open(os.path.join(PASTA, "municipios_pi.json"), encoding="utf-8") as f:
        return {nome: tuple(c) for nome, c in json.load(f).items()}


def buscar_coordenadas(cidade):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{cidade}, Piauí, Brasil", "format": "json", "limit": 1}
    headers = {"User-Agent": "trabalho-piaui-log-estudante"}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    dados = resp.json()[0]
    return float(dados["lat"]), float(dados["lon"])


def carregar_coordenadas(usar_cache=False):
    if usar_cache and os.path.exists("coordenadas.json"):
        with open("coordenadas.json", encoding="utf-8") as f:
            return json.load(f)

    coords = {}
    for c in CIDADES:
        print(f"Buscando {c}...", end=" ", flush=True)
        coords[c] = buscar_coordenadas(c)
        print(coords[c])
        time.sleep(1.1)

    with open("coordenadas.json", "w", encoding="utf-8") as f:
        json.dump(coords, f, ensure_ascii=False, indent=2)
    return coords


def _pedir_json(url, tentativas=3):
    """GET com algumas tentativas (o servidor público às vezes falha ou limita)."""
    ultimo_erro = None
    for t in range(tentativas):
        try:
            resp = requests.get(url, timeout=60)
            return resp.json()
        except Exception as erro:
            ultimo_erro = erro
            time.sleep(1.5 * (t + 1))
    raise RuntimeError(f"OSRM não respondeu: {ultimo_erro}")


def _tabela_osrm(pontos, origens=None, destinos=None):
    """Chama o serviço /table do OSRM. pontos = lista de (lat, lon).
    Devolve duas matrizes: distâncias em km e tempos de viagem em minutos."""
    # OSRM quer lon,lat
    lista = ";".join(f"{lon},{lat}" for lat, lon in pontos)
    url = f"{OSRM}/table/v1/driving/{lista}?annotations=distance,duration"
    if origens is not None:
        url += "&sources=" + ";".join(map(str, origens))
        url += "&destinations=" + ";".join(map(str, destinos))
    dados = _pedir_json(url)
    if dados.get("code") != "Ok":
        raise RuntimeError(f"Erro do OSRM: {dados.get('code')} {dados.get('message', '')}")
    km = [[None if d is None else d / 1000 for d in linha] for linha in dados["distances"]]
    minutos = [[None if d is None else d / 60 for d in linha] for linha in dados["durations"]]
    return km, minutos


def obter_matrizes_osrm(coords, cidades=None):
    """Matrizes (km e minutos, por estrada) entre as cidades, na ordem da lista.
    Com mais de 100 cidades o pedido é dividido em blocos de 50 x 50."""
    if cidades is None:
        cidades = CIDADES
    cidades = list(cidades)
    pontos = [coords[c] for c in cidades]
    n = len(pontos)

    if n <= LIMITE_OSRM:
        km, minutos = _tabela_osrm(pontos)
    else:
        km = [[None] * n for _ in range(n)]
        minutos = [[None] * n for _ in range(n)]
        blocos = [list(range(i, min(i + BLOCO, n))) for i in range(0, n, BLOCO)]
        for bi in blocos:
            for bj in blocos:
                if bi is bj:
                    idx, src, dst = bi, range(len(bi)), range(len(bi))
                else:
                    idx = bi + bj
                    src = range(len(bi))
                    dst = range(len(bi), len(idx))
                sub_km, sub_min = _tabela_osrm([pontos[k] for k in idx], list(src), list(dst))
                for li, i in enumerate(bi):
                    for lj, j in enumerate(bj):
                        km[i][j] = sub_km[li][lj]
                        minutos[i][j] = sub_min[li][lj]
                time.sleep(0.3)   # gentileza com o servidor público

    for i in range(n):
        for j in range(n):
            if i != j and (km[i][j] is None or minutos[i][j] is None):
                raise RuntimeError(f"O OSRM não achou caminho de {cidades[i]} para {cidades[j]}.")
        km[i][i] = 0.0
        minutos[i][i] = 0.0
    return km, minutos


def obter_matriz_osrm(coords, cidades=None):
    """Só a matriz de distâncias (km). É a que o main.py usa."""
    return obter_matrizes_osrm(coords, cidades)[0]


def obter_geometria_osrm(coords, rota):
    """Traçado da rota pelas estradas, como lista de (lat, lon).
    Devolve None se o OSRM não conseguir (aí o mapa usa linhas retas)."""
    try:
        pontos = ";".join(f"{coords[c][1]},{coords[c][0]}" for c in rota)
        url = f"{OSRM}/route/v1/driving/{pontos}?overview=full&geometries=geojson"
        dados = _pedir_json(url, tentativas=2)
        if dados.get("code") != "Ok":
            return None
        return [(lat, lon) for lon, lat in dados["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        return None


def obter_rota_osrm(coords, origem, destino):
    """Rota de carro entre duas cidades: distância (km), tempo (min) e traçado [(lat, lon)]."""
    pontos = ";".join(f"{coords[c][1]},{coords[c][0]}" for c in (origem, destino))
    url = f"{OSRM}/route/v1/driving/{pontos}?overview=full&geometries=geojson"
    dados = _pedir_json(url)
    if dados.get("code") != "Ok":
        raise RuntimeError(f"Erro do OSRM: {dados.get('code')} {dados.get('message', '')}")
    r = dados["routes"][0]
    return {"km": r["distance"] / 1000,
            "min": r["duration"] / 60,
            "geometria": [(lat, lon) for lon, lat in r["geometry"]["coordinates"]]}


def imprimir_matriz(matriz, cidades=None):
    if cidades is None:
        cidades = CIDADES
    print(" " * 16 + "".join(f"{c[:8]:>10}" for c in cidades))
    for nome, linha in zip(cidades, matriz):
        print(f"{nome:<16}" + "".join(f"{d:>10.1f}" for d in linha))

if __name__ == "__main__":
    coords = carregar_coordenadas()
    matriz = obter_matriz_osrm(coords)
    imprimir_matriz(matriz)

#so pra salvar a matriz no excel
def salvar_matriz_csv(matriz, arquivo="matriz_distancias.csv", cidades=None):
    """Salva a matriz em CSV, no formato que o Excel brasileiro abre direto."""
    if cidades is None:
        cidades = CIDADES
    with open(arquivo, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([""] + list(cidades))
        for nome, linha in zip(cidades, matriz):
            escritor.writerow([nome] + [f"{d:.1f}".replace(".", ",") for d in linha])
