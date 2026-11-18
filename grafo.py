import networkx as nx
import matplotlib.pyplot as plt
from dados import CIDADES

def construir_grafo(matriz, cidades=CIDADES, tempos=None):
    """Grafo completo. weight = km. Se vier a matriz de tempos (minutos), cada aresta
    também guarda o atributo "tempo"."""
    G = nx.DiGraph()
    for i, a in enumerate(cidades):
        for j, b in enumerate(cidades):
            if i != j:
                if tempos is None:
                    G.add_edge(a, b, weight=matriz[i][j])
                else:
                    G.add_edge(a, b, weight=matriz[i][j], tempo=tempos[i][j])
    return G

def desenhar_grafo(G, coords, rota=None, titulo="Grafo de municípios",
                   arquivo=None, origem=None, mostrar=True):
    """Desenha o grafo. A cidade 'origem' (se informada) fica em laranja.
    mostrar=False não abre janela: só devolve a figura."""
    cidades = list(G.nodes)
    pos = {c: (coords[c][1], coords[c][0]) for c in cidades}

    fig = plt.figure(figsize=(9, 9))
    nos = list(G.nodes)
    cores = ["#ff7f0e" if c == origem else "#1f77b4" for c in nos]
    nx.draw_networkx_nodes(G, pos, nodelist=nos, node_color=cores, node_size=500)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white")

    if rota is None:
        arestas = [(a, b) for i, a in enumerate(cidades)
                   for j, b in enumerate(cidades) if i < j]
        nx.draw_networkx_edges(G, pos, edgelist=arestas, alpha=0.2, arrows=False)
    else:
        arestas = list(zip(rota, rota[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=arestas, edge_color="red",
                               width=2, arrows=True)

    plt.title(titulo)
    plt.axis("off")
    if arquivo:
        plt.savefig(arquivo, dpi=150, bbox_inches="tight")   # salva antes de mostrar
    if mostrar:
        plt.show()
    return fig

def desenhar_mapa(G, coords, rota, todas=None, geometria=None, mostrar_conexoes=False):
    """Desenha o grafo e a rota sobre um mapa real (OpenStreetMap), com folium.
    - G: grafo das cidades da rota;  coords: nome -> (lat, lon)
    - rota: lista de cidades na ordem da viagem
    - todas: dicionário com os outros municípios, desenhados como pontinhos cinza
    - geometria: traçado pelas estradas (lista de (lat, lon)); sem ele usa linhas retas
    - mostrar_conexoes: desenha também as arestas do grafo (só vale a pena com poucas cidades)"""
    import folium

    nos = list(G.nodes)
    lats = [coords[c][0] for c in nos]
    lons = [coords[c][1] for c in nos]
    mapa = folium.Map(tiles="OpenStreetMap", control_scale=True)
    mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))

    # contexto: os demais municípios do Piauí
    if todas:
        for nome, (la, lo) in todas.items():
            if nome not in G:
                folium.CircleMarker((la, lo), radius=3, color="#888888", weight=1,
                                    fill=True, fill_opacity=0.6, tooltip=nome).add_to(mapa)

    # arestas do grafo (opcional)
    if mostrar_conexoes:
        for i, a in enumerate(nos):
            for b in nos[i + 1:]:
                folium.PolyLine([coords[a], coords[b]], color="#1f77b4",
                                weight=1, opacity=0.25).add_to(mapa)

    # a rota
    linha = geometria if geometria else [coords[c] for c in rota]
    folium.PolyLine(linha, color="#d62728", weight=4, opacity=0.85).add_to(mapa)

    # paradas numeradas (a volta à origem não ganha número novo)
    volta = rota[-1] == rota[0]
    paradas = rota[:-1] if volta else rota
    tam = 26 if len(paradas) <= 40 else 20
    fonte = 12 if len(paradas) <= 40 else 10
    for ordem, cidade in enumerate(paradas):
        if ordem == 0:
            cor, texto = "#ff7f0e", "P"
        elif not volta and ordem == len(paradas) - 1:
            cor, texto = "#2ca02c", "F"
        else:
            cor, texto = "#1f77b4", str(ordem)
        html = (f'<div style="background:{cor};color:white;border-radius:50%;'
                f'width:{tam}px;height:{tam}px;line-height:{tam - 4}px;text-align:center;'
                f'font-weight:700;font-size:{fonte}px;border:2px solid white;'
                f'box-shadow:0 0 3px rgba(0,0,0,.5)">{texto}</div>')
        folium.Marker(coords[cidade],
                      icon=folium.DivIcon(html=html, icon_size=(tam, tam),
                                          icon_anchor=(tam // 2, tam // 2)),
                      tooltip=f"{ordem}. {cidade}" if ordem else f"Partida: {cidade}").add_to(mapa)
    return mapa
