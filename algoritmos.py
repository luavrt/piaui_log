import itertools
import random
from dados import CIDADES

ORIGEM = "Teresina"   # origem padrão (usada quando nenhuma cidade é informada)

def distancia_total(rota, G):
    """Soma o peso das arestas percorridas, no sentido da viagem."""
    total = 0
    for a, b in zip(rota, rota[1:]):
        total = total + G[a][b]["weight"]
    return total

def rota_aleatoria(origem=ORIGEM, cidades=CIDADES, destino=None):
    """origem -> as outras cidades em ordem aleatória -> destino.
    Sem destino (ou destino igual à origem), a rota volta para a origem."""
    if destino is None:
        destino = origem
    intermediarias = [c for c in cidades if c != origem and c != destino]
    random.shuffle(intermediarias)
    return [origem] + intermediarias + [destino]

def vizinho_mais_proximo(G, origem=ORIGEM, destino=None):
    """Constrói a rota escolhendo sempre a cidade não visitada mais próxima.
    Com destino, ele fica por último; sem destino, a rota volta para a origem."""
    if destino is None:
        destino = origem
    # todas as cidades do grafo, menos a origem e o destino
    nao_visitadas = [c for c in G.nodes if c != origem and c != destino]
    rota = [origem]                  # a rota começa na cidade escolhida
    atual = origem                   # o caminhão está na origem

    while nao_visitadas:             # repete enquanto sobrar cidade
        mais_proxima = None
        menor_dist = float("inf")    # começa "infinito": qualquer distância real será menor

        for cidade in nao_visitadas:
            dist = G[atual][cidade]["weight"]
            if dist < menor_dist:    # achou uma mais perto que a melhor até agora
                menor_dist = dist
                mais_proxima = cidade

        rota.append(mais_proxima)            # vai para essa cidade
        nao_visitadas.remove(mais_proxima)   # ela deixa de estar pendente
        atual = mais_proxima                 # o caminhão agora está nela

    rota.append(destino)             # terminou as paradas: vai para o destino
    return rota

def dois_opt(rota, G):
    """Melhora uma rota invertendo trechos enquanto isso reduzir a distância."""
    melhor = rota[:]                        # cópia, para não alterar a rota original
    melhor_dist = distancia_total(melhor, G)
    melhorou = True

    while melhorou:
        melhorou = False
        # o range começa em 1 e termina antes da última posição:
        # a primeira e a última cidade (a origem) nunca são movidas
        for i in range(1, len(melhor) - 2):
            for j in range(i + 1, len(melhor) - 1):
                # inverte o trecho de i até j (inclusive)
                nova = melhor[:i] + melhor[i:j + 1][::-1] + melhor[j + 1:]
                nova_dist = distancia_total(nova, G)

                if nova_dist < melhor_dist:  # a inversão compensou: adota a nova rota
                    melhor = nova
                    melhor_dist = nova_dist
                    melhorou = True

    return melhor

def dois_opt_rapido(rota, G):
    """Mesma lógica do dois_opt, mas calcula só o que muda em cada inversão.
    O dois_opt refaz a soma da rota inteira a cada teste; com centenas de cidades
    isso demora muito. Aqui a diferença é calculada direto, e o resultado é o mesmo."""
    nos = list(dict.fromkeys(rota))                  # cidades da rota, sem repetir
    idx = {c: k for k, c in enumerate(nos)}
    d = [[0.0] * len(nos) for _ in nos]              # matriz local de distâncias
    for a in nos:
        for b in nos:
            if a != b:
                d[idx[a]][idx[b]] = G[a][b]["weight"]

    p = [idx[c] for c in rota]
    n = len(p)

    def prefixos():
        # F[k] = custo de ir de p[0] até p[k]; B[k] = custo do mesmo trecho no sentido contrário
        F = [0.0] * n
        B = [0.0] * n
        for t in range(n - 1):
            F[t + 1] = F[t] + d[p[t]][p[t + 1]]
            B[t + 1] = B[t] + d[p[t + 1]][p[t]]
        return F, B

    F, B = prefixos()
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b = p[i - 1], p[i]      # arestas que saem...
                c, e = p[j], p[j + 1]
                # custo das arestas novas menos o das antigas (trecho interno invertido)
                delta = (d[a][c] + d[b][e] + (B[j] - B[i])
                         - d[a][b] - d[c][e] - (F[j] - F[i]))
                if delta < -1e-9:
                    p[i:j + 1] = p[i:j + 1][::-1]
                    F, B = prefixos()
                    melhorou = True

    return [nos[k] for k in p]

def forca_bruta(G, origem=ORIGEM):
    """Testa todas as ordens possíveis das 10 cidades e devolve a melhor rota."""
    melhor_rota = None
    melhor_dist = float("inf")
    outras = [c for c in CIDADES if c != origem]

    for perm in itertools.permutations(outras):
        rota = [origem] + list(perm) + [origem]
        dist = distancia_total(rota, G)
        if dist < melhor_dist:
            melhor_dist = dist
            melhor_rota = rota

    return melhor_rota
#essa ultima não roda nmo main, pois demora muito tempo para calcular todas as rotas.
