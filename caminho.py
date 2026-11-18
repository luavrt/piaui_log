import math

R_TERRA = 6371.0   # km


def _xy(lat, lon, lat0):
    """Projeção simples (plana) em km, boa o bastante para distâncias de dezenas de km."""
    x = math.radians(lon) * R_TERRA * math.cos(math.radians(lat0))
    y = math.radians(lat) * R_TERRA
    return x, y


def cidades_no_caminho(geometria, municipios, raio_km=5.0, excluir=()):
    """Acha os municípios que ficam perto do traçado da rota.

    geometria: lista de (lat, lon) do traçado (vem do OSRM)
    municipios: dicionário nome -> (lat, lon)
    raio_km: distância máxima da sede do município até a estrada
    excluir: nomes que não entram (origem e destino)

    Devolve (lista, total_km). Cada item da lista é (nome, km_ao_longo, desvio_km),
    em ordem de passagem. Os km são medidos sobre o traçado."""
    lat0 = sum(p[0] for p in geometria) / len(geometria)
    pts = [_xy(la, lo, lat0) for la, lo in geometria]

    acum = [0.0]                                   # km percorridos até cada ponto
    for k in range(1, len(pts)):
        acum.append(acum[-1] + math.hypot(pts[k][0] - pts[k - 1][0],
                                          pts[k][1] - pts[k - 1][1]))
    total = acum[-1]

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    achadas = []
    for nome, (la, lo) in municipios.items():
        if nome in excluir:
            continue
        px, py = _xy(la, lo, lat0)
        # descarta rápido quem está longe da área da rota
        if (px < min(xs) - raio_km or px > max(xs) + raio_km or
                py < min(ys) - raio_km or py > max(ys) + raio_km):
            continue

        melhor = float("inf")
        ao_longo = 0.0
        for k in range(len(pts) - 1):
            x1, y1 = pts[k]
            x2, y2 = pts[k + 1]
            dx, dy = x2 - x1, y2 - y1
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg2))
            d = math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
            if d < melhor:
                melhor = d
                ao_longo = acum[k] + t * math.sqrt(seg2)

        if melhor <= raio_km:
            achadas.append((nome, ao_longo, melhor))

    achadas.sort(key=lambda item: item[1])
    return achadas, total
