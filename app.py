import datetime as dt
import random
import time

import streamlit as st
from streamlit_folium import st_folium

from dados import (CIDADES, carregar_municipios_pi, obter_matrizes_osrm,
                   obter_geometria_osrm, obter_rota_osrm)
from grafo import construir_grafo, desenhar_mapa
from algoritmos import (distancia_total, rota_aleatoria,
                        vizinho_mais_proximo, dois_opt_rapido)
from caminho import cidades_no_caminho
from entregas import (sem_acento, modelo_csv, ler_planilha, interpretar_entregas)
from logistica import (formatar_tempo, formatar_reais, hora, tempo_total, custo_rota,
                       cronograma, comparar_algoritmos, links_google, link_waze,
                       exportar_excel, exportar_pdf)

MODO_CAMINHO = "Origem → destino pelo caminho"
MODO_PASSEIO = "Passar por cidades escolhidas"
MODO_PLANILHA = "Importar planilha de entregas"
ALGORITMOS = ["Rota aleatória", "Vizinho mais próximo", "2-opt"]
SEM_FINAL = "Voltar à cidade de partida"
RAIO_KM = 5   # cidades cuja sede fica até 5 km da estrada entram na rota

st.set_page_config(page_title="Piauí Log", page_icon="🚚", layout="wide")

if "semente" not in st.session_state:
    st.session_state["semente"] = random.randint(0, 10**6)


@st.cache_data
def municipios():
    """Os 224 municípios do Piauí com suas coordenadas (arquivo municipios_pi.json)."""
    return carregar_municipios_pi()


@st.cache_data(show_spinner="Buscando distâncias e tempos por estrada (OSRM)...")
def carregar_matrizes(cidades):
    """Busca no OSRM só as distâncias e os tempos entre as cidades escolhidas.
    O Streamlit guarda o resultado enquanto a escolha for a mesma (e não a cada clique)."""
    return obter_matrizes_osrm(municipios(), list(cidades))


@st.cache_data(show_spinner="Traçando a rota pelas estradas (OSRM)...")
def carregar_geometria(rota):
    return obter_geometria_osrm(municipios(), list(rota))


@st.cache_data(show_spinner="Buscando a rota pela estrada (OSRM)...")
def carregar_rota(origem, destino):
    return obter_rota_osrm(municipios(), origem, destino)


def montar_grafo(cidades):
    km, minutos = carregar_matrizes(tuple(cidades))
    return construir_grafo(km, list(cidades), minutos)


def calcular_rota(algoritmo, G, origem, destino, cidades):
    if algoritmo == "Rota aleatória":
        random.seed(st.session_state["semente"])   # a rota só muda quando clicar em Calcular rota
        return rota_aleatoria(origem, cidades, destino)
    rota = vizinho_mais_proximo(G, origem, destino)
    if algoritmo == "Vizinho mais próximo":
        return rota
    return dois_opt_rapido(rota, G)   # 2-opt parte da rota do vizinho mais próximo


def mostrar_sequencia(rota):
    sequencia = " → ".join(rota)
    if len(rota) > 25:
        with st.expander("Ver a sequência completa das cidades"):
            st.write(sequencia)
    else:
        st.write(sequencia)


# ---------------------------------------------------------------- painel da rota
def painel_rota(rota, G, cidades, origem, destino, tempo_ms, p, coords, chave,
                por_cidade=None, estradas=True, conexoes=False, outros=False, legenda=""):
    """Tudo o que aparece para UMA rota: números, comparação, mapa, roteiro e exportação."""
    km = distancia_total(rota, G)
    minutos = tempo_total(rota, G)
    custo = custo_rota(km, p["consumo"], p["preco"], p["extra"])
    base = dt.datetime.combine(dt.date.today(), p["saida"])
    etapas, volta = cronograma(rota, G, base, p["parada"])
    fim = etapas[-1]["chegada"]
    total_min = (fim - base).total_seconds() / 60

    a, b, c = st.columns(3)
    a.metric("Distância total", f"{km:.1f} km")
    b.metric("Tempo de viagem", formatar_tempo(minutos), help="Só o tempo dirigindo, sem as paradas.")
    c.metric("Custo estimado", formatar_reais(custo))
    d, e, f = st.columns(3)
    d.metric("Cidades visitadas", len(G.nodes) - 1)
    e.metric("Tempo total com paradas", formatar_tempo(total_min))
    f.metric("Chegada prevista", hora(fim, base), help=f"Saindo às {p['saida'].strftime('%H:%M')}.")
    if por_cidade:
        pesos = [v["peso"] for v in por_cidade.values() if v["peso"] is not None]
        qtd = sum(len(v["clientes"]) for v in por_cidade.values())
        st.caption(f"{qtd} entregas em {len(por_cidade)} cidades"
                   + (f" · peso total {sum(pesos):,.1f} kg".replace(",", ".") if pesos else ""))
    mostrar_sequencia(rota)

    # ---- comparação dos algoritmos e economia
    comp = comparar_algoritmos(G, origem, destino, cidades)
    aleat = comp[0]
    custo_aleat = custo_rota(aleat["km"], p["consumo"], p["preco"], p["extra"])
    economia_km = aleat["km"] - km
    economia_rs = custo_aleat - custo
    with st.expander("Economia e comparação dos algoritmos", expanded=True):
        if economia_km > 0.05:
            st.success(f"**{p['algoritmo']}** economiza **{economia_km:.1f} km** "
                       f"({economia_km / aleat['km'] * 100:.0f}%), "
                       f"**{formatar_reais(economia_rs)}** e "
                       f"**{formatar_tempo(aleat['min'] - minutos)}** de viagem "
                       f"em relação a uma rota sem planejamento.")
        else:
            st.info("Esta rota fica perto da média das rotas sem planejamento, então não há economia a mostrar.")
        tabela = []
        for item in comp:
            c_item = custo_rota(item["km"], p["consumo"], p["preco"], p["extra"])
            tabela.append({"Algoritmo": item["algoritmo"],
                           "Distância (km)": round(item["km"], 1),
                           "Tempo de viagem": formatar_tempo(item["min"]),
                           "Custo": formatar_reais(c_item),
                           "Economia vs. aleatória": formatar_reais(custo_aleat - c_item)})
        st.dataframe(tabela, hide_index=True, width="stretch")

    # ---- roteiro parada a parada
    linhas = []
    for i, etapa in enumerate(etapas):
        if i == 0:
            parada = "Partida"
        elif i == len(etapas) - 1 and volta:
            parada = "Volta"
        else:
            parada = str(i)
        linha = {"Parada": parada,
                 "Cidade": etapa["cidade"],
                 "Trecho (km)": round(etapa["km"], 1),
                 "Dirigindo": formatar_tempo(etapa["min"]) if i else "—",
                 "Chegada": hora(etapa["chegada"], base) if etapa["chegada"] else "—",
                 "Saída": hora(etapa["saida"], base) if etapa["saida"] else "—"}
        if por_cidade is not None:
            dados_cidade = por_cidade.get(etapa["cidade"]) if parada != "Volta" else None
            linha["Cliente(s)"] = "; ".join(x for x in dados_cidade["clientes"] if x) if dados_cidade else ""
            tem_peso = dados_cidade is not None and dados_cidade["peso"] is not None
            linha["Peso (kg)"] = f"{dados_cidade['peso']:.1f}".replace(".", ",") if tem_peso else ""
        linhas.append(linha)

    geometria = carregar_geometria(tuple(rota)) if estradas else None
    if estradas and geometria is None:
        st.caption("Não consegui o traçado pelas estradas; o mapa mostra linhas retas entre as cidades.")

    esq, dir_ = st.columns([3, 2])
    with esq:
        mapa = desenhar_mapa(G, coords, rota, todas=coords if outros else None,
                             geometria=geometria, mostrar_conexoes=conexoes)
        st_folium(mapa, height=600, use_container_width=True, returned_objects=[],
                  key=f"mapa_{chave}_{p['algoritmo']}_{abs(hash(tuple(rota)))}")
        st.caption(f"{p['algoritmo']}. P = partida" + (", F = final" if destino else "") + ". "
                   + legenda)
    with dir_:
        st.markdown("**Roteiro**")
        st.dataframe(linhas, hide_index=True, width="stretch", height=600)

    # ---- levar a rota para o motorista
    st.markdown("**Levar a rota para o motorista**")
    resumo = {"Partida": origem,
              "Destino": destino if destino else f"{origem} (volta)",
              "Algoritmo": p["algoritmo"],
              "Distância total": f"{km:.1f} km",
              "Tempo de viagem": formatar_tempo(minutos),
              "Tempo total com paradas": formatar_tempo(total_min),
              "Custo estimado": formatar_reais(custo),
              "Horário de saída": p["saida"].strftime("%H:%M"),
              "Chegada prevista": hora(fim, base)}
    b1, b2, b3 = st.columns(3)
    b1.download_button("Baixar em Excel (.xlsx)", exportar_excel(resumo, linhas),
                       file_name=f"roteiro_{sem_acento(origem).replace(' ', '_')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=f"xlsx_{chave}", width="stretch")
    b2.download_button("Baixar em PDF", exportar_pdf(resumo, linhas),
                       file_name=f"roteiro_{sem_acento(origem).replace(' ', '_')}.pdf",
                       mime="application/pdf", key=f"pdf_{chave}", width="stretch")
    b3.link_button(f"Waze: ir para {rota[1]}", link_waze(rota[1], coords), width="stretch")
    for rotulo, url in links_google(rota, coords):
        st.link_button(rotulo, url)


# ---------------------------------------------------------------- modo caminho
def mostrar_caminho(p, coords):
    """Cidades que ficam na estrada entre a partida e o destino, ordenadas pelo algoritmo escolhido."""
    origem, destino = p["origem"], p["destino"]
    try:
        info = carregar_rota(origem, destino)
    except Exception as erro:
        st.error(f"Não consegui buscar a rota no OSRM: {erro}")
        st.stop()

    # cidades que ficam no caminho da estrada entre a partida e o destino
    achadas, _ = cidades_no_caminho(info["geometria"], coords, RAIO_KM,
                                    excluir=(origem, destino))
    cidades = [origem] + [nome for nome, _, _ in achadas] + [destino]

    try:
        G = montar_grafo(cidades)
    except Exception as erro:
        st.error(f"Não consegui buscar as distâncias no OSRM: {erro}")
        st.stop()

    inicio = time.perf_counter()
    rota = calcular_rota(p["algoritmo"], G, origem, destino, cidades)
    tempo_ms = (time.perf_counter() - inicio) * 1000
    painel_rota(rota, G, cidades, origem, destino, tempo_ms, p, coords,
                chave=f"caminho_{origem}_{destino}",
                legenda=f"Rota direta pela estrada: {info['km']:.1f} km.")


# ---------------------------------------------------------------- modo passeio
def mostrar_passeio(p, coords):
    cidades = list(p["cidades"])
    try:
        G = montar_grafo(cidades)
    except Exception as erro:
        st.error(f"Não consegui buscar as distâncias no OSRM: {erro}")
        st.stop()

    destino_final = None if p["final"] == SEM_FINAL else p["final"]

    # uma rota completa para cada cidade de partida escolhida
    resultados = []
    for origem in p["origens"]:
        destino = destino_final if destino_final != origem else None
        inicio = time.perf_counter()
        rota = calcular_rota(p["algoritmo"], G, origem, destino, cidades)
        tempo_ms = (time.perf_counter() - inicio) * 1000
        resultados.append({"origem": origem, "destino": destino, "rota": rota,
                           "km": distancia_total(rota, G), "min": tempo_total(rota, G),
                           "tempo_ms": tempo_ms})

    # comparação (só faz sentido com mais de uma partida)
    if len(resultados) > 1:
        melhor = min(resultados, key=lambda r: r["km"])
        st.subheader("Comparação entre as partidas")
        tabela = [{"Partida": r["origem"], "Distância (km)": round(r["km"], 1),
                   "Tempo de viagem": formatar_tempo(r["min"]),
                   "Custo": formatar_reais(custo_rota(r["km"], p["consumo"], p["preco"], p["extra"]))}
                  for r in sorted(resultados, key=lambda r: r["km"])]
        st.dataframe(tabela, hide_index=True, width="stretch")
        st.success(f"Menor distância: saindo de **{melhor['origem']}** "
                   f"({melhor['km']:.1f} km)")

    # uma aba por cidade de partida
    abas = st.tabs([r["origem"] for r in resultados])
    for aba, r in zip(abas, resultados):
        with aba:
            painel_rota(r["rota"], G, cidades, r["origem"], r["destino"], r["tempo_ms"], p, coords,
                        chave=f"passeio_{r['origem']}", estradas=p["estradas"],
                        conexoes=p["conexoes"], outros=p["outros"])


# ---------------------------------------------------------------- modo planilha
def mostrar_planilha(p, coords):
    entregas = p["entregas"]
    origem = p["origem"]
    final = None if p["final"] == SEM_FINAL else p["final"]

    cidades = [origem] + [c for c in dict.fromkeys(e["cidade"] for e in entregas) if c != origem]
    if final and final not in cidades:
        cidades.append(final)
    if len(cidades) < 2:
        st.warning("Todas as entregas são na cidade de partida: não há rota para calcular.")
        st.stop()

    # junta as entregas de cada cidade (clientes e peso)
    por_cidade = {}
    for e in entregas:
        item = por_cidade.setdefault(e["cidade"], {"clientes": [], "peso": None})
        item["clientes"].append(e["cliente"])
        if e["peso"] is not None:
            item["peso"] = (item["peso"] or 0) + e["peso"]

    try:
        G = montar_grafo(cidades)
    except Exception as erro:
        st.error(f"Não consegui buscar as distâncias no OSRM: {erro}")
        st.stop()

    destino = final if final != origem else None
    inicio = time.perf_counter()
    rota = calcular_rota(p["algoritmo"], G, origem, destino, cidades)
    tempo_ms = (time.perf_counter() - inicio) * 1000
    painel_rota(rota, G, cidades, origem, destino, tempo_ms, p, coords,
                chave=f"planilha_{origem}", por_cidade=por_cidade,
                legenda="Entregas vindas da planilha.")


# ---------------------------------------------------------------- tela
coords = municipios()
nomes = sorted(coords, key=sem_acento)

st.title("🚚 Piauí Log — Roteirizador de entregas")

with st.sidebar:
    st.header("Parâmetros")
    modo = st.radio("O que você quer ver?", [MODO_CAMINHO, MODO_PASSEIO, MODO_PLANILHA])

    if modo == MODO_CAMINHO:
        origem = st.selectbox("Cidade de partida", nomes, index=nomes.index("Teresina"))
        destino = st.selectbox("Cidade de destino", nomes, index=nomes.index("Parnaíba"))
        algoritmo = st.radio("Algoritmo", ALGORITMOS, index=2)

    elif modo == MODO_PASSEIO:
        usar_todas = st.checkbox(f"Usar todos os {len(nomes)} municípios do Piauí")
        if usar_todas:
            cidades = nomes
            st.caption("Com todos os municípios, a primeira busca das distâncias demora um pouco.")
        else:
            cidades = st.multiselect("Cidades da rota", nomes, default=CIDADES)

        origens = st.multiselect("Cidades de partida", cidades,
                                 default=["Teresina"] if "Teresina" in cidades else cidades[:1])
        final = st.selectbox("Cidade final (opcional)", [SEM_FINAL] + list(cidades))
        algoritmo = st.radio("Algoritmo", ALGORITMOS, index=2)
        estradas = st.checkbox("Desenhar a rota pelas estradas", value=True)
        conexoes = st.checkbox("Mostrar as conexões do grafo", value=False,
                               disabled=len(cidades) > 15,
                               help="Só disponível com até 15 cidades, para o mapa não ficar poluído.")
        outros = st.checkbox("Mostrar os outros municípios no mapa", value=False)

    else:
        arquivo = st.file_uploader("Planilha de entregas (CSV ou Excel)", type=["csv", "xlsx"])
        st.download_button("Baixar modelo da planilha", modelo_csv(),
                           file_name="modelo_entregas.csv", mime="text/csv")
        origem = st.selectbox("Cidade de partida (depósito)", nomes, index=nomes.index("Teresina"))
        final = st.selectbox("Cidade final (opcional)", [SEM_FINAL] + nomes)
        algoritmo = st.radio("Algoritmo", ALGORITMOS, index=2)

        entregas, erros = [], []
        if arquivo is not None:
            try:
                entregas, erros = interpretar_entregas(
                    ler_planilha(arquivo.name, arquivo.getvalue()), nomes)
            except Exception as erro:
                erros = [f"Não consegui ler o arquivo: {erro}"]
        if erros:
            st.error("\n\n".join(erros[:6]) + (f"\n\n... e mais {len(erros) - 6} problemas."
                                                if len(erros) > 6 else ""))
        elif entregas:
            st.success(f"{len(entregas)} entregas em {len({e['cidade'] for e in entregas})} cidades.")

    with st.expander("Custo e horário"):
        st.caption("Valores de exemplo: ajuste para a sua frota.")
        consumo = st.number_input("Consumo do caminhão (km por litro)", 0.5, 30.0, 3.0, 0.1)
        preco = st.number_input("Preço do combustível (R$ por litro)", 0.5, 30.0, 6.0, 0.1)
        extra = st.number_input("Outros custos (R$ por km)", 0.0, 30.0, 0.0, 0.1,
                                help="Motorista, manutenção, pedágio... Deixe em 0 para contar só o combustível.")
        saida = st.time_input("Horário de saída", value=dt.time(8, 0))
        parada = st.number_input("Tempo de parada por cidade (min)", 0, 480, 20, 5)

    botao = st.button("Calcular rota", type="primary", width="stretch")

if botao:
    # guarda as cidades escolhidas: elas só mudam quando clicar em "Calcular rota"
    # (cada mudança de cidades pede distâncias novas ao OSRM)
    st.session_state["semente"] = random.randint(0, 10**6)
    if modo == MODO_CAMINHO:
        st.session_state["escolha"] = {"modo": modo, "origem": origem, "destino": destino}
    elif modo == MODO_PASSEIO:
        st.session_state["escolha"] = {"modo": modo, "cidades": tuple(cidades),
                                       "origens": tuple(origens), "final": final}
    elif entregas and not erros:
        st.session_state["escolha"] = {"modo": modo, "origem": origem, "final": final,
                                       "entregas": entregas}
    else:
        st.session_state.pop("escolha", None)
        st.sidebar.warning("Envie uma planilha sem erros para calcular.")

escolha = st.session_state.get("escolha")
if not escolha or escolha["modo"] != modo:
    st.info("Escolha as cidades e o algoritmo na barra lateral e clique em **Calcular rota**.")
    st.stop()

# o algoritmo, o custo, o horário e as opções do mapa valem na hora, sem clicar de novo
p = dict(escolha)
p.update({"algoritmo": algoritmo, "consumo": consumo, "preco": preco, "extra": extra,
          "saida": saida, "parada": parada})
if modo == MODO_PASSEIO:
    p.update({"estradas": estradas, "conexoes": conexoes, "outros": outros})

if p["modo"] == MODO_CAMINHO:
    if p["origem"] == p["destino"]:
        st.warning("Escolha cidades diferentes para a partida e o destino.")
        st.stop()
    mostrar_caminho(p, coords)
elif p["modo"] == MODO_PASSEIO:
    if len(p["cidades"]) < 3:
        st.warning("Escolha pelo menos 3 cidades para a rota.")
        st.stop()
    if not p["origens"]:
        st.warning("Escolha pelo menos uma cidade de partida.")
        st.stop()
    mostrar_passeio(p, coords)
else:
    mostrar_planilha(p, coords)
