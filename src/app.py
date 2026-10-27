import random
import re
from collections import Counter
from datetime import date, datetime, time, timedelta
from functools import wraps
from itertools import count

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# Chave usada para assinar a sessão de login. Troque por um valor secreto seu.
app.secret_key = "troque-esta-chave-secreta"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
MESES_COMPLETOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                   "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
# Cores dos técnicos no gráfico (se houver mais técnicos que cores, elas se repetem).
PALETA = ["#0f7c78", "#d97706", "#3b6fb6", "#b3446c", "#6b8e23", "#7a5195"]

# ---------------------------------------------------------------
# Dados de exemplo dos chamados
# ---------------------------------------------------------------
# Ainda não existe cadastro de chamados no sistema: estes são FICTÍCIOS, só para
# o dashboard ter o que mostrar. Quando houver banco, troque esta função por uma
# consulta que devolva uma lista de dicionários com as mesmas chaves:
#   id, tecnico, funcionario, aberto_em (datetime), resolvido_em (datetime ou None)
TECNICOS_EXEMPLO = ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Rocha"]
FUNCIONARIOS_EXEMPLO = ["Fernanda Alves", "Gustavo Reis", "Helena Costa",
                        "Igor Martins", "Júlia Pires", "Lucas Nunes"]


def primeiro_dia_mes(d, deslocamento=0):
    """Primeiro dia do mês de `d`, andando `deslocamento` meses (pode ser negativo)."""
    total = d.year * 12 + d.month - 1 + deslocamento
    return date(total // 12, total % 12 + 1, 1)


def chamados_exemplo():
    rnd = random.Random(42)  # semente fixa: os números não mudam a cada atualização
    hoje = date.today()
    inicio = primeiro_dia_mes(hoje, -5)
    dias = (hoje - inicio).days + 1
    agora = datetime.now()

    chamados = []
    for i in range(1, 221):
        dia = inicio + timedelta(days=rnd.randrange(dias))
        aberto_em = datetime.combine(dia, time(rnd.randint(8, 17), rnd.choice([0, 15, 30, 45])))
        foi_resolvido = rnd.random() < 0.75
        horas = rnd.uniform(1, 80)
        tecnico = rnd.choice(TECNICOS_EXEMPLO)
        funcionario = rnd.choice(FUNCIONARIOS_EXEMPLO)

        resolvido_em = aberto_em + timedelta(hours=horas) if foi_resolvido else None
        if resolvido_em and resolvido_em > agora:  # ainda não deu tempo de resolver
            resolvido_em = None
        chamados.append({
            "id": i, "tecnico": tecnico, "funcionario": funcionario,
            "aberto_em": aberto_em, "resolvido_em": resolvido_em,
        })
    return chamados


def parse_data(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None
    except ValueError:
        return None


# ---------------------------------------------------------------
# Tela inicial e acessos
# ---------------------------------------------------------------
@app.route("/")
def inicio():
    return render_template("public/inicio.html")


# Regra de negócio: a EMPRESA se cadastra sozinha; o FUNCIONÁRIO não tem
# autocadastro, ele é criado pela empresa em /funcionarios.
@app.route("/login/funcionario", methods=["GET", "POST"])
def login_funcionario():
    usuario_digitado, erros = "", {}

    if request.method == "POST":
        usuario_digitado = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        if " " in usuario_digitado:
            erros["usuario"] = "O nome de usuário não pode ter espaços."
        else:
            func = next(
                (f for f in FUNCIONARIOS if f["usuario"].lower() == usuario_digitado.lower()),
                None,
            )
            if func and check_password_hash(func["senha_hash"], senha):
                session.clear()
                session["funcionario_id"] = func["id"]
                return redirect(url_for("dashboard"))
            erros["geral"] = "Usuário ou senha inválidos."

    return render_template("public/loginFuncionario.html", usuario=usuario_digitado, erros=erros)


# ---------------------------------------------------------------
# Empresa: cadastro, login e logout
# ---------------------------------------------------------------
# Lista em memória (some ao reiniciar o servidor). Troque por banco depois.
EMPRESAS = []


def so_digitos(texto):
    return re.sub(r"\D", "", texto)


def formatar_cnpj(d):
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def cnpj_valido(d):
    """Confere 14 dígitos e os dois dígitos verificadores."""
    if len(d) != 14 or d == d[0] * 14:
        return False
    for tam in (12, 13):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos = ([6] + pesos) if tam == 13 else pesos
        soma = sum(int(n) * p for n, p in zip(d[:tam], pesos))
        digito = 11 - soma % 11
        digito = 0 if digito >= 10 else digito
        if int(d[tam]) != digito:
            return False
    return True


def buscar_empresa(cnpj):
    return next((e for e in EMPRESAS if e["cnpj"] == cnpj), None)


def login_obrigatorio(view):
    """Só deixa entrar quem fez login como EMPRESA."""
    @wraps(view)
    def protegida(*args, **kwargs):
        if not buscar_empresa(session.get("empresa_cnpj", "")):
            session.clear()
            return redirect(url_for("login_empresa"))
        return view(*args, **kwargs)
    return protegida


def acesso_obrigatorio(view):
    """Deixa entrar quem fez login como EMPRESA ou como FUNCIONÁRIO."""
    @wraps(view)
    def protegida(*args, **kwargs):
        empresa_ok = buscar_empresa(session.get("empresa_cnpj", ""))
        funcionario_ok = buscar_funcionario(session.get("funcionario_id", -1))
        if not (empresa_ok or funcionario_ok):
            session.clear()
            return redirect(url_for("inicio"))
        return view(*args, **kwargs)
    return protegida


@app.context_processor
def dados_do_menu():
    """Variáveis disponíveis em todos os templates (usadas no menu lateral)."""
    empresa = buscar_empresa(session.get("empresa_cnpj", ""))
    return {"empresa_atual": empresa, "e_empresa": empresa is not None}


@app.route("/cadastro/empresa", methods=["GET", "POST"])
def cadastro_empresa():
    cnpj_digitado, razao, erros = "", "", {}

    if request.method == "POST":
        razao = " ".join(request.form.get("razao_social", "").split())
        cnpj_digitado = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")
        cnpj = so_digitos(cnpj_digitado)

        if len(razao) < 3:
            erros["razao_social"] = "Informe a razão social da empresa."
        elif len(razao) > 120:
            erros["razao_social"] = "A razão social deve ter no máximo 120 caracteres."

        if re.search(r"[^\d./-]", cnpj_digitado):
            erros["cnpj"] = "O CNPJ deve ter apenas números."
        elif not cnpj_valido(cnpj):
            erros["cnpj"] = "Informe um CNPJ válido (14 números)."
        elif buscar_empresa(cnpj):
            erros["cnpj"] = "Esse CNPJ já está cadastrado."
        if len(senha) < 6:
            erros["senha"] = "A senha precisa ter pelo menos 6 caracteres."

        if not erros:
            EMPRESAS.append({
                "razao_social": razao,
                "cnpj": cnpj,
                "senha_hash": generate_password_hash(senha),  # nunca guarde a senha pura
            })
            return redirect(url_for("login_empresa", msg="cadastrada"))

    return render_template(
        "public/cadastroEmpresa.html", titulo="Cadastro de empresa", botao="Cadastrar",
        cadastro=True, cnpj=cnpj_digitado, razao_social=razao, erros=erros, mensagem=None,
    )


@app.route("/login/empresa", methods=["GET", "POST"])
def login_empresa():
    cnpj_digitado, erros = "", {}

    if request.method == "POST":
        cnpj_digitado = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")
        empresa = buscar_empresa(so_digitos(cnpj_digitado))

        if empresa and check_password_hash(empresa["senha_hash"], senha):
            session.clear()
            session["empresa_cnpj"] = empresa["cnpj"]
            return redirect(url_for("dashboard"))
        erros["geral"] = "CNPJ ou senha inválidos."

    mensagem = "Empresa cadastrada! Agora é só entrar." if request.args.get("msg") == "cadastrada" else None
    return render_template(
        "public/cadastroEmpresa.html", titulo="Login", botao="Entrar",
        cadastro=False, cnpj=cnpj_digitado, razao_social="", erros=erros, mensagem=mensagem,
    )


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("inicio"))


# ---------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------
def formatar_duracao(horas):
    if horas is None:
        return "–"
    if horas < 1:
        return f"{round(horas * 60)} min"
    if horas < 48:
        return f"{horas:.1f} h".replace(".", ",")
    return f"{horas / 24:.1f} dias".replace(".", ",")


def meses_do_periodo(ini, fim, limite=12):
    """Lista de (ano, mês) entre as duas datas; devolve no máximo os últimos `limite`."""
    atual, ultimo = primeiro_dia_mes(ini), primeiro_dia_mes(fim)
    meses = []
    while atual <= ultimo:
        meses.append((atual.year, atual.month))
        atual = primeiro_dia_mes(atual, 1)
    return meses[-limite:], len(meses) > limite


def montar_dashboard(chamados, ini, fim):
    """Calcula tudo que o dashboard mostra. Regra: só entram chamados ABERTOS no período."""
    no_periodo = [c for c in chamados if ini <= c["aberto_em"].date() <= fim]
    resolvidos = [c for c in no_periodo if c["resolvido_em"]]
    abertos = [c for c in no_periodo if not c["resolvido_em"]]

    tempo_medio = None
    if resolvidos:
        total_horas = sum((c["resolvido_em"] - c["aberto_em"]).total_seconds() / 3600 for c in resolvidos)
        tempo_medio = total_horas / len(resolvidos)

    # Card 2: chamados em aberto por funcionário, no mês da Data final
    inicio_mes = max(ini, fim.replace(day=1))
    abertos_mes = [c for c in abertos if inicio_mes <= c["aberto_em"].date() <= fim]
    por_funcionario = Counter(c["funcionario"] for c in abertos_mes).most_common()
    por_funcionario.sort(key=lambda x: (-x[1], x[0]))
    maior = por_funcionario[0][1] if por_funcionario else 1
    lista = [{"nome": n, "total": t, "largura": round(t / maior * 100)} for n, t in por_funcionario]

    # Gráfico: atendimentos (chamados resolvidos) por mês e por técnico
    tecnicos = sorted({c["tecnico"] for c in resolvidos})
    cores = {t: PALETA[i % len(PALETA)] for i, t in enumerate(tecnicos)}
    contagem = Counter((c["aberto_em"].year, c["aberto_em"].month, c["tecnico"]) for c in resolvidos)
    maximo = max(contagem.values(), default=1)
    meses, cortado = meses_do_periodo(ini, fim)
    grafico = [
        {
            "rotulo": f"{MESES[m - 1]}/{str(a)[2:]}",
            "barras": [
                {"tecnico": t, "total": contagem[(a, m, t)],
                 "altura": round(contagem[(a, m, t)] / maximo * 100), "cor": cores[t]}
                for t in tecnicos
            ],
        }
        for a, m in meses
    ]

    return {
        "abertos": len(abertos), "resolvidos": len(resolvidos),
        "tempo_medio": formatar_duracao(tempo_medio),
        "mes_lista": f"{MESES_COMPLETOS[fim.month - 1].capitalize()}/{fim.year}",
        "total_abertos_mes": len(abertos_mes), "lista": lista,
        "tecnicos": tecnicos, "cores": cores, "grafico": grafico, "grafico_cortado": cortado,
    }


@app.route("/dashboard")
@acesso_obrigatorio
def dashboard():
    hoje = date.today()
    padrao_ini, padrao_fim = primeiro_dia_mes(hoje, -5), hoje  # padrão: últimos 6 meses

    ini = parse_data(request.args.get("data_inicio")) or padrao_ini
    fim = parse_data(request.args.get("data_final")) or padrao_fim
    erro_filtro = None
    if ini > fim:
        erro_filtro = "A data inicial não pode ser maior que a data final."
        ini, fim = padrao_ini, padrao_fim

    return render_template(
        "public/dashboardEmpresa.html",
        dados=montar_dashboard(chamados_exemplo(), ini, fim),
        data_inicio=ini.isoformat(), data_final=fim.isoformat(), erro_filtro=erro_filtro,
    )


# ---------------------------------------------------------------
# Setores e equipes técnicas (cadastradas pela EMPRESA)
# ---------------------------------------------------------------
# Listas em memória (somem ao reiniciar o servidor). Troque por banco depois.
SETORES = []
EQUIPES = []
_proximo_setor = count(1)
_proximo_equipe = count(1)

MSGS_SETOR_EQUIPE = {
    "setor_criado": "Setor adicionado.",
    "equipe_criada": "Equipe adicionada.",
    "setor_excluido": "Setor excluído.",
    "equipe_excluida": "Equipe excluída.",
    "setor_em_uso": "Não é possível excluir: há funcionários neste setor.",
    "equipe_em_uso": "Não é possível excluir: há técnicos nesta equipe.",
}


def nome_por_id(lista, item_id):
    return next((i["nome"] for i in lista if i["id"] == item_id), "")


def validar_nome(nome, lista):
    if len(nome) < 2:
        return "Informe o nome (mínimo 2 letras)."
    if len(nome) > 50:
        return "Use no máximo 50 caracteres."
    if any(i["nome"].lower() == nome.lower() for i in lista):
        return "Já existe um item com esse nome."
    return None


def tela_equipes(erros=None, digitado=None):
    msg = request.args.get("msg")
    return render_template(
        "public/setoresEquipes.html",
        setores=sorted(SETORES, key=lambda i: i["nome"].lower()),
        equipes=sorted(EQUIPES, key=lambda i: i["nome"].lower()),
        erros=erros or {}, digitado=digitado or {},
        mensagem=MSGS_SETOR_EQUIPE.get(msg),
        mensagem_erro=msg in ("setor_em_uso", "equipe_em_uso"),
    )


@app.route("/equipes")
@login_obrigatorio
def equipes():
    return tela_equipes()


@app.route("/equipes/setor", methods=["POST"])
@login_obrigatorio
def adicionar_setor():
    nome = " ".join(request.form.get("nome", "").split())
    erro = validar_nome(nome, SETORES)
    if erro:
        return tela_equipes({"setor": erro}, {"setor": nome})
    SETORES.append({"id": next(_proximo_setor), "nome": nome})
    return redirect(url_for("equipes", msg="setor_criado"))


@app.route("/equipes/equipe", methods=["POST"])
@login_obrigatorio
def adicionar_equipe():
    nome = " ".join(request.form.get("nome", "").split())
    erro = validar_nome(nome, EQUIPES)
    if erro:
        return tela_equipes({"equipe": erro}, {"equipe": nome})
    EQUIPES.append({"id": next(_proximo_equipe), "nome": nome})
    return redirect(url_for("equipes", msg="equipe_criada"))


@app.route("/equipes/setor/<int:item_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_setor(item_id):
    setor = next((i for i in SETORES if i["id"] == item_id), None)
    if setor is None:
        abort(404)
    if any(f["setor_id"] == item_id for f in FUNCIONARIOS):
        return redirect(url_for("equipes", msg="setor_em_uso"))
    SETORES.remove(setor)
    return redirect(url_for("equipes", msg="setor_excluido"))


@app.route("/equipes/equipe/<int:item_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_equipe(item_id):
    equipe = next((i for i in EQUIPES if i["id"] == item_id), None)
    if equipe is None:
        abort(404)
    if any(f["equipe_id"] == item_id for f in FUNCIONARIOS):
        return redirect(url_for("equipes", msg="equipe_em_uso"))
    EQUIPES.remove(equipe)
    return redirect(url_for("equipes", msg="equipe_excluida"))


# ---------------------------------------------------------------
# Cadastro de funcionários (CRUD)
# ---------------------------------------------------------------
# Lista em memória (some ao reiniciar o servidor). Troque por banco depois.
FUNCIONARIOS = []
_proximo_id = count(1)

MENSAGENS = {
    "criado": "Funcionário cadastrado com sucesso.",
    "editado": "Funcionário atualizado com sucesso.",
    "excluido": "Funcionário excluído.",
}


def form_vazio():
    # "setor" e "equipe" guardam o ID escolhido no campo de seleção (como texto).
    return {"usuario": "", "tipo": "padrao", "setor": "", "equipe": ""}


def buscar_funcionario(func_id):
    return next((f for f in FUNCIONARIOS if f["id"] == func_id), None)


def validar_funcionario(form, senha, editando_id=None):
    erros = {}

    usuario = form["usuario"]
    if not usuario:
        erros["usuario"] = "Informe o nome de usuário."
    elif " " in usuario:
        erros["usuario"] = "O nome de usuário não pode ter espaços."
    elif any(f["usuario"].lower() == usuario.lower() and f["id"] != editando_id
             for f in FUNCIONARIOS):
        erros["usuario"] = "Esse nome de usuário já está em uso."

    # Ao editar, senha em branco significa "manter a atual".
    if (editando_id is None or senha) and len(senha) < 6:
        erros["senha"] = "A senha precisa ter pelo menos 6 caracteres."

    if form["setor"] not in {str(s["id"]) for s in SETORES}:
        erros["setor"] = "Selecione o setor."

    if form["tipo"] not in ("padrao", "tecnico"):
        erros["tipo"] = "Escolha o tipo de funcionário."
    elif form["tipo"] == "tecnico" and form["equipe"] not in {str(e["id"]) for e in EQUIPES}:
        erros["equipe"] = "Selecione a equipe do técnico."

    return erros


def tela_cadastro(form, erros, editando_id=None):
    # A tabela mostra os NOMES do setor e da equipe (o funcionário guarda só os ids).
    lista = [
        {**f, "setor": nome_por_id(SETORES, f["setor_id"]), "equipe": nome_por_id(EQUIPES, f["equipe_id"])}
        for f in FUNCIONARIOS
    ]
    return render_template(
        "public/funcionarios.html",
        form=form, erros=erros, lista=lista, editando_id=editando_id,
        setores=sorted(SETORES, key=lambda i: i["nome"].lower()),
        equipes=sorted(EQUIPES, key=lambda i: i["nome"].lower()),
        mensagem=MENSAGENS.get(request.args.get("msg")),
    )


# CREATE + READ (lista)
@app.route("/funcionarios", methods=["GET", "POST"])
@login_obrigatorio
def funcionarios():
    form, erros = form_vazio(), {}

    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in form}
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha)

        if not erros:
            FUNCIONARIOS.append({
                "id": next(_proximo_id),
                "usuario": form["usuario"],
                "senha_hash": generate_password_hash(senha),  # nunca guarde a senha pura
                "tipo": form["tipo"],
                "setor_id": int(form["setor"]),
                "equipe_id": int(form["equipe"]) if form["tipo"] == "tecnico" else None,
            })
            return redirect(url_for("funcionarios", msg="criado"))

    return tela_cadastro(form, erros)


# UPDATE
@app.route("/funcionarios/<int:func_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_funcionario(func_id):
    func = buscar_funcionario(func_id)
    if func is None:
        abort(404)

    form = {
        "usuario": func["usuario"],
        "tipo": func["tipo"],
        "setor": str(func["setor_id"]),
        "equipe": str(func["equipe_id"] or ""),
    }
    erros = {}

    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in form}
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, editando_id=func_id)

        if not erros:
            func["usuario"] = form["usuario"]
            func["tipo"] = form["tipo"]
            func["setor_id"] = int(form["setor"])
            func["equipe_id"] = int(form["equipe"]) if form["tipo"] == "tecnico" else None
            if senha:
                func["senha_hash"] = generate_password_hash(senha)
            return redirect(url_for("funcionarios", msg="editado"))

    return tela_cadastro(form, erros, editando_id=func_id)


# DELETE
@app.route("/funcionarios/<int:func_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_funcionario(func_id):
    func = buscar_funcionario(func_id)
    if func is None:
        abort(404)
    FUNCIONARIOS.remove(func)
    return redirect(url_for("funcionarios", msg="excluido"))




# Login

USUARIOS_MOCK = [
    {"id": 1, "usuario": "FELIPE", "senha": "123456", "tipo": "padrao", "id_empresa": 1},
    {"id": 2, "usuario": "RAPHAEL", "senha": "654321", "tipo": "tecnico", "id_empresa": 1},
    {"id": 3, "usuario": "GABRIEL", "senha": "111111", "tipo": "tecnico", "id_empresa": 1},
]


def autenticar(usuario, senha):
    for conta in USUARIOS_MOCK:
        if conta["usuario"] == usuario and conta["senha"] == senha:
            return conta
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    usuario = ""

    if request.method == "POST":
        usuario = request.form.get("usuario", "").upper().replace(" ", "")
        senha = request.form.get("senha", "")
        conta = autenticar(usuario, senha)

        if conta is None:
            flash("Usuário ou senha inválidos.")
        else:
            session["id_usuario"] = conta["id"]
            session["id_empresa"] = conta["id_empresa"]
            session["tipo"] = conta["tipo"]

            if conta["tipo"] == "tecnico":
                return redirect(url_for("dashboard_tecnico"))
            return redirect(url_for("meus_chamados"))

    return render_template("public/login.html", usuario=usuario)





# Abrir chamado (funcionário padrão)

LIMITE_DESCRICAO = 500


CHAMADOS_MOCK = []
_proximo_chamado = count(1)


def salvar_chamado(id_empresa, id_funcionario, descricao):
    
    CHAMADOS_MOCK.append({
        "id": next(_proximo_chamado),
        "id_empresa": id_empresa,
        "id_funcionario": id_funcionario,
        "descricao": descricao,
        "status": "aguardando",
        "aberto_em": datetime.now(),
        "id_prioridade": 1,
        "id_tecnico": None,
        "previsao": None,
        "resolvido_em": None,
        "comentarios": [],
        "solucao": None,
    })


@app.route("/abrir-chamado", methods=["GET", "POST"])
def abrir_chamado():
    descricao, erro = "", None

    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            erro = "Descreva o problema antes de abrir o chamado."
        elif len(descricao) > LIMITE_DESCRICAO:
            erro = f"A descrição pode ter no máximo {LIMITE_DESCRICAO} caracteres."
        else:
            salvar_chamado(session.get("id_empresa"), session.get("id_usuario"), descricao)
            flash("Chamado aberto com sucesso!")
            return redirect(url_for("meus_chamados"))

    return render_template(
        "public/abrir_chamado.html",
        descricao=descricao, erro=erro, limite=LIMITE_DESCRICAO,
    )



# Meus chamados (funcionário padrão)

def listar_chamados_do_funcionario(id_empresa, id_funcionario):
    meus = []
    for chamado in CHAMADOS_MOCK:
        if chamado["id_empresa"] == id_empresa and chamado["id_funcionario"] == id_funcionario:
            meus.append(chamado)
    return meus


def posicao_na_fila(chamado):
    posicao = 1
    for outro in CHAMADOS_MOCK:
        if (outro["id_empresa"] == chamado["id_empresa"]
                and outro["status"] == "aguardando"
                and outro["aberto_em"] < chamado["aberto_em"]):
            posicao += 1
    return posicao


def excluir_chamado(id_empresa, id_funcionario, id_chamado):
    for chamado in CHAMADOS_MOCK:
        if (chamado["id"] == id_chamado
                and chamado["id_empresa"] == id_empresa
                and chamado["id_funcionario"] == id_funcionario):
            CHAMADOS_MOCK.remove(chamado)
            return True
    return False


@app.route("/meus-chamados")
def meus_chamados():
    chamados = listar_chamados_do_funcionario(session.get("id_empresa"), session.get("id_usuario"))

    agora = datetime.now()
    total_mes = 0
    for chamado in chamados:
        if chamado["aberto_em"].month == agora.month and chamado["aberto_em"].year == agora.year:
            total_mes += 1

        if chamado["status"] == "aguardando":
            chamado["posicao"] = posicao_na_fila(chamado)
        else:
            chamado["posicao"] = None

    return render_template("public/meus_chamados.html", chamados=chamados, total_mes=total_mes)


@app.route("/meus-chamados/<int:id_chamado>/excluir", methods=["POST"])
def excluir_meu_chamado(id_chamado):
    excluiu = excluir_chamado(session.get("id_empresa"), session.get("id_usuario"), id_chamado)
    if not excluiu:
        abort(404)
    flash("Chamado excluído.")
    return redirect(url_for("meus_chamados"))


# ---------------------------------------------------------------
# Dashboard do técnico
# ---------------------------------------------------------------
PRIORIDADES_MOCK = [
    {"id": 1, "descricao": "Baixa"},
    {"id": 2, "descricao": "Média"},
    {"id": 3, "descricao": "Alta"},
]


def nome_da_prioridade(id_prioridade):
    for prioridade in PRIORIDADES_MOCK:
        if prioridade["id"] == id_prioridade:
            return prioridade["descricao"]
    return "–"


def nome_do_usuario(id_usuario):
    for conta in USUARIOS_MOCK:
        if conta["id"] == id_usuario:
            return conta["usuario"]
    return "–"


def listar_chamados_pendentes(id_empresa):
    pendentes = []
    for chamado in CHAMADOS_MOCK:
        if chamado["id_empresa"] == id_empresa and chamado["status"] != "finalizado":
            pendentes.append(chamado)
    return pendentes


def contar_resolvidos_hoje(id_tecnico):
    hoje = date.today()
    total = 0
    for chamado in CHAMADOS_MOCK:
        if (chamado["id_tecnico"] == id_tecnico
                and chamado["status"] == "finalizado"
                and chamado["resolvido_em"].date() == hoje):
            total += 1
    return total


def tela_tecnico(chamado_aberto=None):
    pendentes = listar_chamados_pendentes(session.get("id_empresa"))
    for chamado in pendentes:
        chamado["funcionario"] = nome_do_usuario(chamado["id_funcionario"])
        chamado["prioridade"] = nome_da_prioridade(chamado["id_prioridade"])

    resolvidos_hoje = contar_resolvidos_hoje(session.get("id_usuario"))
    return render_template(
        "public/dashboard_tecnico.html",
        chamados=pendentes, resolvidos_hoje=resolvidos_hoje,
        aberto=chamado_aberto, prioridades=PRIORIDADES_MOCK,
    )


@app.route("/tecnico")
def dashboard_tecnico():
    return tela_tecnico()



# Modal de atendimento (técnico)

def buscar_chamado(id_empresa, id_chamado):
    for chamado in CHAMADOS_MOCK:
        if chamado["id"] == id_chamado and chamado["id_empresa"] == id_empresa:
            return chamado
    return None


def erro_de_atendimento(chamado):
    # Só o técnico que assumiu o chamado pode alterá-lo.
    if chamado["id_tecnico"] is None:
        return "Assuma o chamado antes de fazer alterações."
    if chamado["id_tecnico"] != session.get("id_usuario"):
        return "Este chamado já foi assumido por outro técnico."
    return None


@app.route("/tecnico/chamado/<int:id_chamado>")
def ver_chamado(id_chamado):
    chamado = buscar_chamado(session.get("id_empresa"), id_chamado)
    if chamado is None or chamado["status"] == "finalizado":
        abort(404)
    return tela_tecnico(chamado)


@app.route("/tecnico/chamado/<int:id_chamado>/assumir", methods=["POST"])
def assumir_chamado(id_chamado):
    chamado = buscar_chamado(session.get("id_empresa"), id_chamado)
    if chamado is None:
        abort(404)

    if chamado["id_tecnico"] is not None and chamado["id_tecnico"] != session.get("id_usuario"):
        flash("Este chamado já foi assumido por outro técnico.", "erro")
        return redirect(url_for("dashboard_tecnico"))

    chamado["id_tecnico"] = session.get("id_usuario")
    chamado["status"] = "em_andamento"
    flash("Chamado assumido.")
    return redirect(url_for("ver_chamado", id_chamado=id_chamado))


@app.route("/tecnico/chamado/<int:id_chamado>/atualizar", methods=["POST"])
def atualizar_chamado(id_chamado):
    chamado = buscar_chamado(session.get("id_empresa"), id_chamado)
    if chamado is None:
        abort(404)

    erro = erro_de_atendimento(chamado)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("dashboard_tecnico"))

    id_prioridade = request.form.get("id_prioridade", type=int)
    if nome_da_prioridade(id_prioridade) != "–":
        chamado["id_prioridade"] = id_prioridade

    previsao = request.form.get("previsao", "").strip()
    chamado["previsao"] = previsao[:25] or None

    comentario = request.form.get("comentario", "").strip()
    if comentario:
        chamado["comentarios"].append({
            "autor": nome_do_usuario(session.get("id_usuario")),
            "texto": comentario,
            "em": datetime.now(),
        })

    flash("Alterações salvas.")
    return redirect(url_for("ver_chamado", id_chamado=id_chamado))


@app.route("/tecnico/chamado/<int:id_chamado>/finalizar", methods=["POST"])
def finalizar_chamado(id_chamado):
    chamado = buscar_chamado(session.get("id_empresa"), id_chamado)
    if chamado is None:
        abort(404)

    erro = erro_de_atendimento(chamado)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("dashboard_tecnico"))

    solucao = request.form.get("solucao", "").strip()
    if not solucao:
        flash("Descreva a solução antes de finalizar o chamado.", "erro")
        return redirect(url_for("ver_chamado", id_chamado=id_chamado))

    chamado["solucao"] = solucao
    chamado["status"] = "finalizado"
    chamado["resolvido_em"] = datetime.now()
    flash("Chamado finalizado.")
    return redirect(url_for("dashboard_tecnico"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True)

    
