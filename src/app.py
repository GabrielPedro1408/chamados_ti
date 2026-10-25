import random
from datetime import date, datetime, timedelta
from itertools import count

from flask import Flask, abort, flash, get_flashed_messages, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = "deskly-desenvolvimento"  

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
TECNICOS = ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Rocha", "Elisa Prado"]


# ---------------------------------------------------------------
# Dados de exemplo dos chamados (troque por consulta ao banco)
# ---------------------------------------------------------------
def gerar_chamados():
    random.seed(42)
    chamados = []
    inicio = date(2026, 4, 1)
    for i in range(1, 241):
        aberto_em = inicio + timedelta(days=random.randint(0, 182))
        resolvido = random.random() < 0.78
        resolvido_em = (aberto_em + timedelta(days=random.randint(0, 6))) if resolvido else None
        chamados.append({
            "id": i,
            "tecnico": random.choice(TECNICOS),
            "aberto_em": aberto_em,
            "resolvido_em": resolvido_em,
        })
    return chamados


CHAMADOS = gerar_chamados()


def parse_data(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None
    except ValueError:
        return None


# ---------------------------------------------------------------
# Painel
# ---------------------------------------------------------------
@app.route("/")
def index():
    data_inicio = request.args.get("data_inicio", "")
    data_final = request.args.get("data_final", "")
    ini = parse_data(data_inicio)
    fim = parse_data(data_final)

    dados = [
        c for c in CHAMADOS
        if (not ini or c["aberto_em"] >= ini) and (not fim or c["aberto_em"] <= fim)
    ]

    resolvidos = [c for c in dados if c["resolvido_em"]]

    tempo_medio = (
        sum((c["resolvido_em"] - c["aberto_em"]).days for c in resolvidos) / len(resolvidos)
        if resolvidos else 0
    )

    contagem = {}
    for c in resolvidos:
        contagem[c["tecnico"]] = contagem.get(c["tecnico"], 0) + 1
    ordenado = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
    maior = ordenado[0][1] if ordenado else 1
    ranking = [
        {"tecnico": t, "total": n, "largura": round(n / maior * 100)}
        for t, n in ordenado
    ]

    por_mes = {}
    for c in dados:
        chave = (c["aberto_em"].year, c["aberto_em"].month)
        por_mes[chave] = por_mes.get(chave, 0) + 1
    maior_mes = max(por_mes.values()) if por_mes else 1
    meses = [
        {"mes": f"{MESES[m - 1]}/{str(a)[2:]}", "total": t, "altura": round(t / maior_mes * 85)}
        for (a, m), t in sorted(por_mes.items())
    ]

    kpis = {
        "em_aberto": len(dados) - len(resolvidos),
        "resolvidos": len(resolvidos),
        "tempo_medio_dias": round(tempo_medio, 1),
        "atendimentos_por_tecnico": round(len(resolvidos) / len(ranking), 1) if ranking else 0,
    }

    return render_template(
        "public/index.html",
        kpis=kpis, meses=meses, ranking=ranking,
        data_inicio=data_inicio, data_final=data_final,
    )


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

    if not form["setor"]:
        erros["setor"] = "Informe o setor."

    if form["tipo"] not in ("padrao", "tecnico"):
        erros["tipo"] = "Escolha o tipo de funcionário."
    elif form["tipo"] == "tecnico" and not form["equipe"]:
        erros["equipe"] = "Informe a equipe do técnico."

    return erros


def tela_cadastro(form, erros, editando_id=None):
    return render_template(
        "public/funcionarios.html",
        form=form, erros=erros, lista=FUNCIONARIOS, editando_id=editando_id,
        mensagem=MENSAGENS.get(request.args.get("msg")),
    )


# CREATE + READ (lista)
@app.route("/funcionarios", methods=["GET", "POST"])
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
                "setor": form["setor"],
                "equipe": form["equipe"] if form["tipo"] == "tecnico" else "",
            })
            return redirect(url_for("funcionarios", msg="criado"))

    return tela_cadastro(form, erros)


# UPDATE
@app.route("/funcionarios/<int:func_id>/editar", methods=["GET", "POST"])
def editar_funcionario(func_id):
    func = buscar_funcionario(func_id)
    if func is None:
        abort(404)

    form = {c: func[c] for c in form_vazio()}
    erros = {}

    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in form}
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, editando_id=func_id)

        if not erros:
            func["usuario"] = form["usuario"]
            func["tipo"] = form["tipo"]
            func["setor"] = form["setor"]
            func["equipe"] = form["equipe"] if form["tipo"] == "tecnico" else ""
            if senha:
                func["senha_hash"] = generate_password_hash(senha)
            return redirect(url_for("funcionarios", msg="editado"))

    return tela_cadastro(form, erros, editando_id=func_id)


# DELETE
@app.route("/funcionarios/<int:func_id>/excluir", methods=["POST"])
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

    
