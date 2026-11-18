import datetime as dt
import io
import random
import urllib.parse
from xml.sax.saxutils import escape

from algoritmos import distancia_total, vizinho_mais_proximo, dois_opt_rapido


# ------------------------------------------------------------------ formatação
def formatar_tempo(minutos):
    horas, mins = divmod(int(round(minutos)), 60)
    return f"{horas} h {mins:02d} min" if horas else f"{mins} min"


def formatar_reais(valor):
    texto = f"{valor:,.2f}"                     # 1,234.56
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def hora(momento, base):
    """HH:MM; se já passou para outro dia, avisa com (+1d), (+2d)..."""
    texto = momento.strftime("%H:%M")
    dias = (momento.date() - base.date()).days
    return texto + (f" (+{dias}d)" if dias > 0 else "")


# ------------------------------------------------------------------ tempo e custo
def tempo_total(rota, G):
    """Soma dos minutos dirigindo, trecho a trecho (as arestas guardam o atributo "tempo")."""
    return sum(G[a][b]["tempo"] for a, b in zip(rota, rota[1:]))


def custo_rota(km, consumo, preco, extra_por_km=0.0):
    """Combustível (km / consumo * preço) mais outros custos por km."""
    return km / consumo * preco + km * extra_por_km


def cronograma(rota, G, saida, parada_min):
    """Horário de chegada e de saída em cada cidade.
    saida: datetime da partida; parada_min: minutos parado em cada cidade visitada.
    Na volta à cidade de partida não há parada."""
    etapas = [{"cidade": rota[0], "km": 0.0, "min": 0.0, "chegada": None, "saida": saida}]
    atual = saida
    volta = rota[-1] == rota[0]
    for k in range(1, len(rota)):
        a, b = rota[k - 1], rota[k]
        chegada = atual + dt.timedelta(minutes=G[a][b]["tempo"])
        ultimo = k == len(rota) - 1
        if ultimo:
            saida_cidade = None
        else:
            saida_cidade = chegada + dt.timedelta(minutes=parada_min)
        etapas.append({"cidade": b, "km": G[a][b]["weight"], "min": G[a][b]["tempo"],
                       "chegada": chegada, "saida": saida_cidade})
        atual = saida_cidade if saida_cidade else chegada
    return etapas, volta


# ------------------------------------------------------------------ economia
def media_aleatoria(G, origem, destino, cidades, n=500, semente=42):
    """Média de km e de minutos de n rotas aleatórias (como seria sem planejamento)."""
    rng = random.Random(semente)
    if destino is None:
        destino = origem
    meio = [c for c in cidades if c != origem and c != destino]
    soma_km = soma_min = 0.0
    for _ in range(n):
        rng.shuffle(meio)
        rota = [origem] + meio + [destino]
        soma_km += distancia_total(rota, G)
        soma_min += tempo_total(rota, G)
    return soma_km / n, soma_min / n


def comparar_algoritmos(G, origem, destino, cidades, n=500):
    """Resultado dos três algoritmos na mesma situação (a aleatória é a média de n rotas)."""
    media_km, media_min = media_aleatoria(G, origem, destino, cidades, n)
    vmp = vizinho_mais_proximo(G, origem, destino)
    opt = dois_opt_rapido(vmp, G)
    return [
        {"algoritmo": f"Rota aleatória (média de {n})", "km": media_km, "min": media_min},
        {"algoritmo": "Vizinho mais próximo", "km": distancia_total(vmp, G), "min": tempo_total(vmp, G)},
        {"algoritmo": "2-opt", "km": distancia_total(opt, G), "min": tempo_total(opt, G)},
    ]


# ------------------------------------------------------------------ links para o motorista
def links_google(rota, coords, max_pontos=10):
    """Links do Google Maps com a rota. O Google aceita poucas paradas por link,
    então rotas longas são divididas em partes (a última cidade de uma é a primeira da próxima)."""
    partes = []
    i = 0
    while i < len(rota) - 1:
        partes.append(rota[i:i + max_pontos])
        i += max_pontos - 1

    def ponto(c):
        return f"{coords[c][0]},{coords[c][1]}"

    links = []
    for n, trecho in enumerate(partes, 1):
        params = {"api": "1", "origin": ponto(trecho[0]), "destination": ponto(trecho[-1]),
                  "travelmode": "driving"}
        if len(trecho) > 2:
            params["waypoints"] = "|".join(ponto(c) for c in trecho[1:-1])
        url = "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params)
        if len(partes) == 1:
            rotulo = "Abrir a rota no Google Maps"
        else:
            rotulo = f"Google Maps, parte {n} de {len(partes)}: {trecho[0]} → {trecho[-1]}"
        links.append((rotulo, url))
    return links


def link_waze(cidade, coords):
    """O Waze só aceita um destino por link: usamos a próxima parada."""
    lat, lon = coords[cidade]
    return f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"


# ------------------------------------------------------------------ exportação
def exportar_excel(resumo, linhas):
    """Planilha .xlsx com o resumo no topo e o roteiro parada a parada."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Roteiro"
    ws.append(["Piauí Log - Roteiro de entrega"])
    ws["A1"].font = Font(bold=True, size=14)
    for chave, valor in resumo.items():
        ws.append([chave, valor])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    ws.append([])

    cabecalho = list(linhas[0].keys())
    ws.append(cabecalho)
    for celula in ws[ws.max_row]:
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor="12262B")
    for linha in linhas:
        ws.append([linha[c] for c in cabecalho])

    for coluna in ws.columns:
        maior = max(len(str(c.value)) for c in coluna if c.value is not None)
        ws.column_dimensions[coluna[0].column_letter].width = min(max(12, maior + 2), 45)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def exportar_pdf(resumo, linhas):
    """PDF em paisagem com o resumo e o roteiro, para imprimir ou mandar ao motorista."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    estilos = getSampleStyleSheet()
    pequeno = ParagraphStyle("pequeno", parent=estilos["Normal"], fontSize=8, leading=10)
    cab_estilo = ParagraphStyle("cab", parent=pequeno, textColor=colors.white, fontName="Helvetica-Bold")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=28, rightMargin=28,
                            topMargin=28, bottomMargin=28, title="Roteiro de entrega - Piauí Log")
    elementos = [Paragraph("Piauí Log - Roteiro de entrega", estilos["Title"])]
    for chave, valor in resumo.items():
        elementos.append(Paragraph(f"<b>{escape(str(chave))}:</b> {escape(str(valor))}", estilos["Normal"]))
    elementos.append(Spacer(1, 12))

    cabecalho = list(linhas[0].keys())
    dados = [[Paragraph(escape(c), cab_estilo) for c in cabecalho]]
    for linha in linhas:
        dados.append([Paragraph(escape(str(linha[c])), pequeno) for c in cabecalho])
    tabela = Table(dados, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12262B")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3EEE2")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    return buf.getvalue()
