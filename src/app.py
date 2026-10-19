import random
import re
from functools import wraps
from datetime import date, datetime, timedelta
from itertools import count

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# Chave usada para assinar a sessão de login. Troque por um valor secreto seu.
app.secret_key = "troque-esta-chave-secreta"

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
                return redirect(url_for("painel"))
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
            return redirect(url_for("painel"))
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
# Painel
# ---------------------------------------------------------------
@app.route("/painel")
@acesso_obrigatorio
def painel():
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
                "setor": form["setor"],
                "equipe": form["equipe"] if form["tipo"] == "tecnico" else "",
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
@login_obrigatorio
def excluir_funcionario(func_id):
    func = buscar_funcionario(func_id)
    if func is None:
        abort(404)
    FUNCIONARIOS.remove(func)
    return redirect(url_for("funcionarios", msg="excluido"))


if __name__ == "__main__":
    app.run(debug=True)