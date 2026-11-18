from dados import carregar_coordenadas, obter_matriz_osrm, imprimir_matriz
from grafo import construir_grafo, desenhar_grafo
from algoritmos import distancia_total, forca_bruta, rota_aleatoria, vizinho_mais_proximo, dois_opt
from analise import comparar_algoritmos, exibir_rota, medir_tempo

EXECUTAR_FORCA_BRUTA = False  #True para rodar força bruta (muito lento)

#dados
coords = carregar_coordenadas()
matriz = obter_matriz_osrm(coords)
imprimir_matriz(matriz)

#grafo
G = construir_grafo(matriz)

#teste do cálculo: ida e volta simples
print(distancia_total(["Teresina", "Altos", "Teresina"], G))

#rota aleatória
rota = rota_aleatoria()
print("Rota aleatória:")
print(" -> ".join(rota))
print(f"{distancia_total(rota, G):.1f} km")

#rota vizinho mais próximo
rota_vmp = vizinho_mais_proximo(G)
print("Vizinho mais próximo:")
print(" -> ".join(rota_vmp))
print(f"{distancia_total(rota_vmp, G):.1f} km")

#rota 2-opt
rota_2opt = dois_opt(rota_vmp, G)
print("2-opt:")
print(" -> ".join(rota_2opt))
print(f"{distancia_total(rota_2opt, G):.1f} km")

#comparação dos algoritmos
resultados = comparar_algoritmos(G)


#força bruta(tem que colocar true para rodar)
if EXECUTAR_FORCA_BRUTA:
    print("\nRodando força bruta, aguarde...")
    rota_otima, t_fb = medir_tempo(forca_bruta, G)
    exibir_rota("Força bruta (ótimo)", rota_otima, G)
    print(f"Tempo: {t_fb:.1f} s")


from dados import salvar_matriz_csv
salvar_matriz_csv(matriz)

desenhar_grafo(G, coords, titulo="Grafo completo de municípios", arquivo="grafo_completo.png")
desenhar_grafo(G, coords, rota=resultados["2opt"], titulo="Rota ótima (2-opt)", arquivo="rota_2opt.png")