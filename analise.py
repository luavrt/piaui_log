import time
import statistics
from algoritmos import (distancia_total, rota_aleatoria,
                        vizinho_mais_proximo, dois_opt)


def medir_tempo(funcao, *args, repeticoes=1):
    """Roda a função várias vezes e devolve (resultado, tempo médio em segundos)."""
    inicio = time.perf_counter()
    for _ in range(repeticoes):
        resultado = funcao(*args)
    fim = time.perf_counter()
    return resultado, (fim - inicio) / repeticoes


def exibir_rota(nome, rota, G):
    """Mostra a sequência de municípios e a distância total."""
    print(f"\n{nome}")
    print(" -> ".join(rota))
    print(f"Distância total: {distancia_total(rota, G):.1f} km")


def analisar_aleatoria(G, n=1000):#rod a aleatoria 1000x para guardar a media, melhor e pior distancia
    """Roda a rota aleatória n vezes e resume os resultados."""
    distancias = [distancia_total(rota_aleatoria(), G) for _ in range(n)]
    _, tempo = medir_tempo(rota_aleatoria, repeticoes=n)
    return {"media": statistics.mean(distancias),
            "melhor": min(distancias),
            "pior": max(distancias),
            "tempo": tempo}


def comparar_algoritmos(G):
    """Executa os três algoritmos, mostra as rotas e a tabela comparativa."""
    aleat = analisar_aleatoria(G)

    rota_vmp, t_vmp = medir_tempo(vizinho_mais_proximo, G, repeticoes=100)
    rota_2opt, t_2opt = medir_tempo(dois_opt, rota_vmp, G, repeticoes=10)

    d_vmp = distancia_total(rota_vmp, G)
    d_2opt = distancia_total(rota_2opt, G)

    exibir_rota("Vizinho mais próximo", rota_vmp, G)
    exibir_rota("2-opt", rota_2opt, G)

    print(f"\nRota aleatória (1000 execuções): "
          f"melhor {aleat['melhor']:.1f} km | pior {aleat['pior']:.1f} km")

    print(f"\n{'Algoritmo':<30}{'Distância (km)':>16}{'Tempo (ms)':>14}")
    print("-" * 60)
    print(f"{'Aleatória (média de 1000)':<30}{aleat['media']:>16.1f}{aleat['tempo'] * 1000:>14.4f}")
    print(f"{'Vizinho mais próximo':<30}{d_vmp:>16.1f}{t_vmp * 1000:>14.4f}")
    print(f"{'2-opt (a partir do VMP)':<30}{d_2opt:>16.1f}{t_2opt * 1000:>14.4f}")

    return {"vmp": rota_vmp, "2opt": rota_2opt}