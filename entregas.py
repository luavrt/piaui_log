import csv
import io
import unicodedata

COLUNAS_CIDADE = {"cidade", "municipio", "destino", "local"}
COLUNAS_CLIENTE = {"cliente", "nome", "destinatario", "pedido"}
COLUNAS_PESO = {"peso", "peso_kg", "pesokg", "kg"}


def sem_acento(texto):
    """minúsculas e sem acento, para comparar nomes (Parnaíba == parnaiba)."""
    sem = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode()
    return sem.strip().lower()


def _chave_coluna(texto):
    t = sem_acento(texto).replace(" ", "_").replace("(", "").replace(")", "")
    return t


def modelo_csv():
    """Modelo de planilha para o usuário baixar (abre direto no Excel brasileiro)."""
    texto = ("cidade;cliente;peso_kg\r\n"
             "Parnaíba;Mercado Central;120\r\n"
             "Piripiri;Farmácia São José;45,5\r\n"
             "Campo Maior;Loja do Bairro;80\r\n")
    return texto.encode("utf-8-sig")


def ler_planilha(nome_arquivo, conteudo):
    """Lê um .csv ou .xlsx e devolve uma lista de linhas (cada linha é uma lista de textos)."""
    if nome_arquivo.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
        planilha = wb.active
        return [["" if v is None else v for v in linha] for linha in planilha.iter_rows(values_only=True)]

    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("cp1252")
    primeira = texto.splitlines()[0] if texto.strip() else ""
    separador = max(";,\t", key=primeira.count)          # o separador que mais aparece
    return list(csv.reader(io.StringIO(texto), delimiter=separador))


def _numero(valor):
    if valor in ("", None):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    return float(str(valor).strip().replace(".", "").replace(",", ".")
                 if "," in str(valor) else str(valor).strip())


def interpretar_entregas(linhas, municipios):
    """Transforma as linhas da planilha em entregas.

    Precisa de uma coluna de cidade (cidade, municipio...). As colunas cliente e peso são opcionais.
    Devolve (entregas, erros). Cada entrega é {"cidade", "cliente", "peso"}, com a cidade já
    escrita como no cadastro dos 224 municípios."""
    linhas = [l for l in linhas if any(str(c).strip() for c in l)]
    if not linhas:
        return [], ["A planilha está vazia."]

    cabecalho = [_chave_coluna(c) for c in linhas[0]]
    def achar(opcoes):
        for i, nome in enumerate(cabecalho):
            if nome in opcoes:
                return i
        return None

    i_cidade = achar(COLUNAS_CIDADE)
    i_cliente = achar(COLUNAS_CLIENTE)
    i_peso = achar(COLUNAS_PESO)
    if i_cidade is None:
        return [], ["Não achei a coluna da cidade. Use um destes nomes na primeira linha: "
                    "cidade, municipio, destino ou local."]

    por_nome = {sem_acento(nome): nome for nome in municipios}
    entregas, erros = [], []
    for n, linha in enumerate(linhas[1:], start=2):
        def celula(i):
            return linha[i] if i is not None and i < len(linha) else ""
        texto = str(celula(i_cidade)).strip()
        if not texto:
            continue
        cidade = por_nome.get(sem_acento(texto))
        if cidade is None:
            erros.append(f"Linha {n}: não conheço o município \"{texto}\" (confira o nome).")
            continue
        try:
            peso = _numero(celula(i_peso))
        except ValueError:
            erros.append(f"Linha {n}: peso inválido \"{celula(i_peso)}\".")
            continue
        entregas.append({"cidade": cidade, "cliente": str(celula(i_cliente)).strip(), "peso": peso})

    if not entregas and not erros:
        erros.append("Não achei nenhuma entrega na planilha.")
    return entregas, erros
