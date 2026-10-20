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



@app.route("/meus-chamados")
def meus_chamados():
    avisos = " ".join(get_flashed_messages())
    total = len(CHAMADOS_MOCK)
    return (
        f'{avisos} Meus chamados (em construção): {total} chamado(s) | '
        f'<a href="{url_for("abrir_chamado")}">Abrir chamado</a> | '
        f'<a href="{url_for("logout")}">Sair</a>'
    )


@app.route("/tecnico")
def dashboard_tecnico():
    return f'Dashboard do técnico (em construção) | <a href="{url_for("logout")}">Sair</a>'



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



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



if __name__ == "__main__":
    app.run(debug=True)

    
