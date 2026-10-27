import re
from collections import Counter
from datetime import date, datetime
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from src.db import consultar, consultar_um, executar, fechar_conexao, transacao

app = Flask(__name__)
# Chave usada para assinar a sessão de login. Troque por um valor secreto seu.
app.secret_key = "troque-esta-chave-secreta"
app.teardown_appcontext(fechar_conexao)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
MESES_COMPLETOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                   "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
# Cores dos técnicos no gráfico (se houver mais técnicos que cores, elas se repetem).
PALETA = ["#0f7c78", "#d97706", "#3b6fb6", "#b3446c", "#6b8e23", "#7a5195"]


def primeiro_dia_mes(d, deslocamento=0):
    """Primeiro dia do mês de `d`, andando `deslocamento` meses (pode ser negativo)."""
    total = d.year * 12 + d.month - 1 + deslocamento
    return date(total // 12, total % 12 + 1, 1)


def parse_data(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None
    except ValueError:
        return None


def normalizar_usuario(texto):
    """Regra do banco: NomeUsuario em MAIÚSCULAS e sem espaços."""
    return re.sub(r"\s", "", texto).upper()


# ---------------------------------------------------------------
# Tela inicial e acessos
# ---------------------------------------------------------------
@app.route("/")
def inicio():
    return render_template("public/inicio.html")


# Regra de negócio: a EMPRESA se cadastra sozinha; o FUNCIONÁRIO não tem
# autocadastro, ele é criado pela empresa em /funcionarios.
# O mesmo login serve para funcionário padrão e técnico: o tipo do usuário
# decide qual tela ele vê depois de entrar.
def autenticar(usuario, senha):
    conta = consultar_um(
        """
        SELECT u.IdUsuario AS id, u.IdEmpresa AS id_empresa, u.NomeUsuario AS usuario,
               u.SenhaHash AS senha_hash,
               fp.IdFuncionario AS id_funcionario, ft.IdTecnico AS id_tecnico
          FROM usuario u
          LEFT JOIN funcionariopadrao fp ON fp.IdUsuario = u.IdUsuario
          LEFT JOIN funcionariotecnico ft ON ft.IdUsuario = u.IdUsuario
         WHERE u.NomeUsuario = %s
        """,
        (usuario,),
    )
    if conta and check_password_hash(conta["senha_hash"], senha):
        return conta
    return None


@app.route("/login/funcionario", methods=["GET", "POST"])
def login_funcionario():
    usuario_digitado, erros = "", {}

    if request.method == "POST":
        usuario_digitado = normalizar_usuario(request.form.get("usuario", ""))
        senha = request.form.get("senha", "")
        conta = autenticar(usuario_digitado, senha)

        if conta is None:
            erros["geral"] = "Usuário ou senha inválidos."
        else:
            session.clear()
            session["id_usuario"] = conta["id"]
            session["id_empresa"] = conta["id_empresa"]
            session["nome"] = conta["usuario"]

            if conta["id_tecnico"]:
                session["tipo"] = "tecnico"
                session["id_tecnico"] = conta["id_tecnico"]
                return redirect(url_for("dashboard_tecnico"))
            session["tipo"] = "padrao"
            session["id_funcionario"] = conta["id_funcionario"]
            return redirect(url_for("meus_chamados"))

    return render_template("public/loginFuncionario.html", usuario=usuario_digitado, erros=erros)


def portal_obrigatorio(tipo):
    """Só deixa entrar quem fez login como FUNCIONÁRIO do tipo indicado ('padrao' ou 'tecnico')."""
    sql = {
        "padrao": "SELECT 1 FROM funcionariopadrao WHERE IdFuncionario = %s AND IdUsuario = %s",
        "tecnico": "SELECT 1 FROM funcionariotecnico WHERE IdTecnico = %s AND IdUsuario = %s",
    }[tipo]
    chave = "id_funcionario" if tipo == "padrao" else "id_tecnico"

    def decorador(view):
        @wraps(view)
        def protegida(*args, **kwargs):
            if session.get("tipo") != tipo:
                return redirect(url_for("login_funcionario"))
            # Confere no banco: o usuário pode ter sido excluído ou mudado de tipo.
            if not consultar_um(sql, (session.get(chave), session.get("id_usuario"))):
                session.clear()
                return redirect(url_for("login_funcionario"))
            return view(*args, **kwargs)
        return protegida
    return decorador


# ---------------------------------------------------------------
# Empresa: cadastro, login e logout
# ---------------------------------------------------------------
SQL_EMPRESA = """
    SELECT IdEmpresa AS id, RazaoSocial AS razao_social, Cnpj AS cnpj, SenhaHash AS senha_hash
      FROM empresa
"""


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
    return consultar_um(SQL_EMPRESA + " WHERE Cnpj = %s", (cnpj,))


def empresa_logada():
    """Empresa que fez login (ou None)."""
    if "empresa_id" not in session:
        return None
    return consultar_um(SQL_EMPRESA + " WHERE IdEmpresa = %s", (session["empresa_id"],))


def login_obrigatorio(view):
    """Só deixa entrar quem fez login como EMPRESA."""
    @wraps(view)
    def protegida(*args, **kwargs):
        if not empresa_logada():
            session.clear()
            return redirect(url_for("login_empresa"))
        return view(*args, **kwargs)
    return protegida


@app.context_processor
def dados_do_menu():
    """Variáveis disponíveis em todos os templates (usadas no menu lateral)."""
    empresa = empresa_logada()
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
            executar(
                "INSERT INTO empresa (RazaoSocial, Cnpj, SenhaHash) VALUES (%s, %s, %s)",
                (razao, cnpj, generate_password_hash(senha)),  # nunca guarde a senha pura
            )
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
            session["empresa_id"] = empresa["id"]
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
def chamados_da_empresa(id_empresa, ini, fim):
    """Chamados ABERTOS no período, com as chaves que o montar_dashboard usa:
    id, tecnico, funcionario, aberto_em (datetime), resolvido_em (datetime ou None)."""
    return consultar(
        """
        SELECT c.IdChamado AS id, ut.NomeUsuario AS tecnico, uf.NomeUsuario AS funcionario,
               c.DataHoraAbertura AS aberto_em, c.DataHoraFechamento AS resolvido_em
          FROM chamado c
          JOIN funcionariopadrao fp ON fp.IdFuncionario = c.IdFuncionario
          JOIN usuario uf ON uf.IdUsuario = fp.IdUsuario
          LEFT JOIN funcionariotecnico ft ON ft.IdTecnico = c.IdTecnico
          LEFT JOIN usuario ut ON ut.IdUsuario = ft.IdUsuario
         WHERE c.IdEmpresa = %s AND DATE(c.DataHoraAbertura) BETWEEN %s AND %s
        """,
        (id_empresa, ini, fim),
    )


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
@login_obrigatorio
def dashboard():
    hoje = date.today()
    padrao_ini, padrao_fim = primeiro_dia_mes(hoje, -5), hoje  # padrão: últimos 6 meses

    ini = parse_data(request.args.get("data_inicio")) or padrao_ini
    fim = parse_data(request.args.get("data_final")) or padrao_fim
    erro_filtro = None
    if ini > fim:
        erro_filtro = "A data inicial não pode ser maior que a data final."
        ini, fim = padrao_ini, padrao_fim

    chamados = chamados_da_empresa(session["empresa_id"], ini, fim)
    return render_template(
        "public/dashboardEmpresa.html",
        dados=montar_dashboard(chamados, ini, fim),
        data_inicio=ini.isoformat(), data_final=fim.isoformat(), erro_filtro=erro_filtro,
    )


# ---------------------------------------------------------------
# Setores e equipes técnicas (cadastradas pela EMPRESA)
# ---------------------------------------------------------------
MSGS_SETOR_EQUIPE = {
    "setor_criado": "Setor adicionado.",
    "equipe_criada": "Equipe adicionada.",
    "setor_excluido": "Setor excluído.",
    "equipe_excluida": "Equipe excluída.",
    "setor_em_uso": "Não é possível excluir: há funcionários neste setor.",
    "equipe_em_uso": "Não é possível excluir: há técnicos nesta equipe.",
}


def listar_setores(id_empresa):
    return consultar(
        "SELECT IdSetor AS id, NomeSetor AS nome FROM setor WHERE IdEmpresa = %s ORDER BY NomeSetor",
        (id_empresa,),
    )


def listar_equipes(id_empresa):
    return consultar(
        "SELECT IdEquipe AS id, NomeEquipe AS nome FROM equipetecnica WHERE IdEmpresa = %s ORDER BY NomeEquipe",
        (id_empresa,),
    )


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
        setores=listar_setores(session["empresa_id"]),
        equipes=listar_equipes(session["empresa_id"]),
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
    erro = validar_nome(nome, listar_setores(session["empresa_id"]))
    if erro:
        return tela_equipes({"setor": erro}, {"setor": nome})
    executar("INSERT INTO setor (IdEmpresa, NomeSetor) VALUES (%s, %s)", (session["empresa_id"], nome))
    return redirect(url_for("equipes", msg="setor_criado"))


@app.route("/equipes/equipe", methods=["POST"])
@login_obrigatorio
def adicionar_equipe():
    nome = " ".join(request.form.get("nome", "").split())
    erro = validar_nome(nome, listar_equipes(session["empresa_id"]))
    if erro:
        return tela_equipes({"equipe": erro}, {"equipe": nome})
    executar("INSERT INTO equipetecnica (IdEmpresa, NomeEquipe) VALUES (%s, %s)", (session["empresa_id"], nome))
    return redirect(url_for("equipes", msg="equipe_criada"))


@app.route("/equipes/setor/<int:item_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_setor(item_id):
    if not consultar_um("SELECT 1 FROM setor WHERE IdSetor = %s AND IdEmpresa = %s",
                        (item_id, session["empresa_id"])):
        abort(404)
    if consultar_um("SELECT 1 FROM funcionariopadrao WHERE IdSetor = %s LIMIT 1", (item_id,)):
        return redirect(url_for("equipes", msg="setor_em_uso"))
    executar("DELETE FROM setor WHERE IdSetor = %s", (item_id,))
    return redirect(url_for("equipes", msg="setor_excluido"))


@app.route("/equipes/equipe/<int:item_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_equipe(item_id):
    if not consultar_um("SELECT 1 FROM equipetecnica WHERE IdEquipe = %s AND IdEmpresa = %s",
                        (item_id, session["empresa_id"])):
        abort(404)
    if consultar_um("SELECT 1 FROM funcionariotecnico WHERE IdEquipe = %s LIMIT 1", (item_id,)):
        return redirect(url_for("equipes", msg="equipe_em_uso"))
    executar("DELETE FROM equipetecnica WHERE IdEquipe = %s", (item_id,))
    return redirect(url_for("equipes", msg="equipe_excluida"))


# ---------------------------------------------------------------
# Cadastro de funcionários (CRUD)
# ---------------------------------------------------------------
# No banco, cada funcionário é um `usuario` mais uma linha em
# `funcionariopadrao` (com setor) OU em `funcionariotecnico` (com equipe opcional).
MENSAGENS = {
    "criado": "Funcionário cadastrado com sucesso.",
    "editado": "Funcionário atualizado com sucesso.",
    "excluido": "Funcionário excluído.",
    "em_uso": "Não é possível excluir: há chamados ligados a este funcionário.",
}

SQL_FUNCIONARIOS = """
    SELECT u.IdUsuario AS id, u.NomeUsuario AS usuario,
           IF(ft.IdTecnico IS NULL, 'padrao', 'tecnico') AS tipo,
           fp.IdSetor AS setor_id, ft.IdEquipe AS equipe_id,
           s.NomeSetor AS setor, e.NomeEquipe AS equipe
      FROM usuario u
      LEFT JOIN funcionariopadrao fp ON fp.IdUsuario = u.IdUsuario
      LEFT JOIN funcionariotecnico ft ON ft.IdUsuario = u.IdUsuario
      LEFT JOIN setor s ON s.IdSetor = fp.IdSetor
      LEFT JOIN equipetecnica e ON e.IdEquipe = ft.IdEquipe
     WHERE u.IdEmpresa = %s
"""


def form_vazio():
    # "setor" e "equipe" guardam o ID escolhido no campo de seleção (como texto).
    return {"usuario": "", "tipo": "padrao", "setor": "", "equipe": ""}


def buscar_funcionario(func_id):
    return consultar_um(SQL_FUNCIONARIOS + " AND u.IdUsuario = %s", (session["empresa_id"], func_id))


def tem_chamados(func_id):
    """True se o usuário abriu ou atendeu algum chamado."""
    return consultar_um(
        """
        SELECT 1 FROM chamado c
          LEFT JOIN funcionariopadrao fp ON fp.IdFuncionario = c.IdFuncionario
          LEFT JOIN funcionariotecnico ft ON ft.IdTecnico = c.IdTecnico
         WHERE fp.IdUsuario = %s OR ft.IdUsuario = %s
         LIMIT 1
        """,
        (func_id, func_id),
    ) is not None


def validar_funcionario(form, senha, setores, equipes, editando=None):
    erros = {}

    usuario = form["usuario"]
    if not usuario:
        erros["usuario"] = "Informe o nome de usuário."
    elif " " in usuario:
        erros["usuario"] = "O nome de usuário não pode ter espaços."
    elif consultar_um("SELECT 1 FROM usuario WHERE NomeUsuario = %s AND IdUsuario <> %s",
                      (normalizar_usuario(usuario), editando["id"] if editando else 0)):
        erros["usuario"] = "Esse nome de usuário já está em uso."

    # Ao editar, senha em branco significa "manter a atual".
    if (editando is None or senha) and len(senha) < 6:
        erros["senha"] = "A senha precisa ter pelo menos 6 caracteres."

    # Funcionário padrão precisa de setor; técnico pode ter equipe (opcional).
    if form["tipo"] not in ("padrao", "tecnico"):
        erros["tipo"] = "Escolha o tipo de funcionário."
    elif form["tipo"] == "padrao" and form["setor"] not in {str(s["id"]) for s in setores}:
        erros["setor"] = "Selecione o setor."
    elif form["tipo"] == "tecnico" and form["equipe"] and form["equipe"] not in {str(e["id"]) for e in equipes}:
        erros["equipe"] = "Selecione uma equipe válida."

    if editando and form["tipo"] != editando["tipo"] and tem_chamados(editando["id"]):
        erros["tipo"] = "Não é possível mudar o tipo: há chamados ligados a este funcionário."

    return erros


def salvar_tipo(id_usuario, form):
    """Grava a linha de funcionariopadrao ou funcionariotecnico do usuário."""
    if form["tipo"] == "tecnico":
        executar("INSERT INTO funcionariotecnico (IdUsuario, IdEquipe) VALUES (%s, %s)",
                 (id_usuario, int(form["equipe"]) if form["equipe"] else None))
    else:
        executar("INSERT INTO funcionariopadrao (IdUsuario, IdSetor) VALUES (%s, %s)",
                 (id_usuario, int(form["setor"])))


def tela_cadastro(form, erros, setores, equipes, editando_id=None):
    msg = request.args.get("msg")
    return render_template(
        "public/funcionarios.html",
        form=form, erros=erros, editando_id=editando_id,
        lista=consultar(SQL_FUNCIONARIOS + " ORDER BY u.NomeUsuario", (session["empresa_id"],)),
        setores=setores, equipes=equipes,
        mensagem=MENSAGENS.get(msg), mensagem_erro=msg == "em_uso",
    )


# CREATE + READ (lista)
@app.route("/funcionarios", methods=["GET", "POST"])
@login_obrigatorio
def funcionarios():
    form, erros = form_vazio(), {}
    setores, equipes = listar_setores(session["empresa_id"]), listar_equipes(session["empresa_id"])

    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in form}
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, setores, equipes)

        if not erros:
            with transacao():
                id_usuario = executar(
                    "INSERT INTO usuario (IdEmpresa, NomeUsuario, SenhaHash) VALUES (%s, %s, %s)",
                    (session["empresa_id"], normalizar_usuario(form["usuario"]),
                     generate_password_hash(senha)),  # nunca guarde a senha pura
                )
                salvar_tipo(id_usuario, form)
            return redirect(url_for("funcionarios", msg="criado"))

    return tela_cadastro(form, erros, setores, equipes)


# UPDATE
@app.route("/funcionarios/<int:func_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar_funcionario(func_id):
    func = buscar_funcionario(func_id)
    if func is None:
        abort(404)
    setores, equipes = listar_setores(session["empresa_id"]), listar_equipes(session["empresa_id"])

    form = {
        "usuario": func["usuario"],
        "tipo": func["tipo"],
        "setor": str(func["setor_id"] or ""),
        "equipe": str(func["equipe_id"] or ""),
    }
    erros = {}

    if request.method == "POST":
        form = {c: request.form.get(c, "").strip() for c in form}
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, setores, equipes, editando=func)

        if not erros:
            with transacao():
                executar("UPDATE usuario SET NomeUsuario = %s WHERE IdUsuario = %s",
                         (normalizar_usuario(form["usuario"]), func_id))
                if senha:
                    executar("UPDATE usuario SET SenhaHash = %s WHERE IdUsuario = %s",
                             (generate_password_hash(senha), func_id))
                if form["tipo"] == func["tipo"] == "padrao":
                    executar("UPDATE funcionariopadrao SET IdSetor = %s WHERE IdUsuario = %s",
                             (int(form["setor"]), func_id))
                elif form["tipo"] == func["tipo"] == "tecnico":
                    executar("UPDATE funcionariotecnico SET IdEquipe = %s WHERE IdUsuario = %s",
                             (int(form["equipe"]) if form["equipe"] else None, func_id))
                else:  # mudou de tipo (só é permitido se não houver chamados ligados)
                    executar("DELETE FROM funcionariopadrao WHERE IdUsuario = %s", (func_id,))
                    executar("DELETE FROM funcionariotecnico WHERE IdUsuario = %s", (func_id,))
                    salvar_tipo(func_id, form)
            return redirect(url_for("funcionarios", msg="editado"))

    return tela_cadastro(form, erros, setores, equipes, editando_id=func_id)


# DELETE
@app.route("/funcionarios/<int:func_id>/excluir", methods=["POST"])
@login_obrigatorio
def excluir_funcionario(func_id):
    if buscar_funcionario(func_id) is None:
        abort(404)
    if tem_chamados(func_id):
        return redirect(url_for("funcionarios", msg="em_uso"))
    with transacao():
        executar("DELETE FROM funcionariopadrao WHERE IdUsuario = %s", (func_id,))
        executar("DELETE FROM funcionariotecnico WHERE IdUsuario = %s", (func_id,))
        executar("DELETE FROM usuario WHERE IdUsuario = %s", (func_id,))
    return redirect(url_for("funcionarios", msg="excluido"))


# Abrir chamado (funcionário padrão)

LIMITE_DESCRICAO = 500
PRIORIDADE_PADRAO = 4  # "Baixa": o técnico ajusta depois, se precisar


def salvar_chamado(id_empresa, id_funcionario, descricao):
    executar(
        """
        INSERT INTO chamado (IdEmpresa, IdFuncionario, IdPrioridade, Descricao, DataHoraAbertura, Status)
        VALUES (%s, %s, %s, %s, %s, 'aguardando')
        """,
        (id_empresa, id_funcionario, PRIORIDADE_PADRAO, descricao, datetime.now()),
    )


@app.route("/abrir-chamado", methods=["GET", "POST"])
@portal_obrigatorio("padrao")
def abrir_chamado():
    descricao, erro = "", None

    if request.method == "POST":
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            erro = "Descreva o problema antes de abrir o chamado."
        elif len(descricao) > LIMITE_DESCRICAO:
            erro = f"A descrição pode ter no máximo {LIMITE_DESCRICAO} caracteres."
        else:
            salvar_chamado(session.get("id_empresa"), session.get("id_funcionario"), descricao)
            flash("Chamado aberto com sucesso!")
            return redirect(url_for("meus_chamados"))

    return render_template(
        "public/abrir_chamado.html",
        descricao=descricao, erro=erro, limite=LIMITE_DESCRICAO,
    )



# Meus chamados (funcionário padrão)

def listar_chamados_do_funcionario(id_empresa, id_funcionario):
    return consultar(
        """
        SELECT IdChamado AS id, IdEmpresa AS id_empresa, Descricao AS descricao, Status AS status,
               DataHoraAbertura AS aberto_em, IdPrioridade AS id_prioridade
          FROM chamado
         WHERE IdEmpresa = %s AND IdFuncionario = %s
         ORDER BY DataHoraAbertura DESC
        """,
        (id_empresa, id_funcionario),
    )


def posicao_na_fila(chamado):
    # A fila é a mesma que o técnico vê: primeiro a prioridade, depois a ordem de
    # abertura (IdChamado cresce na ordem em que os chamados são abertos).
    na_frente = consultar_um(
        """
        SELECT COUNT(*) AS total FROM chamado
         WHERE IdEmpresa = %s AND Status = 'aguardando'
           AND (IdPrioridade < %s OR (IdPrioridade = %s AND IdChamado < %s))
        """,
        (chamado["id_empresa"], chamado["id_prioridade"], chamado["id_prioridade"], chamado["id"]),
    )
    return na_frente["total"] + 1


def excluir_chamado(id_empresa, id_funcionario, id_chamado):
    apagados = executar(
        "DELETE FROM chamado WHERE IdChamado = %s AND IdEmpresa = %s AND IdFuncionario = %s",
        (id_chamado, id_empresa, id_funcionario),
    )
    return apagados > 0


@app.route("/meus-chamados")
@portal_obrigatorio("padrao")
def meus_chamados():
    chamados = listar_chamados_do_funcionario(session.get("id_empresa"), session.get("id_funcionario"))

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
@portal_obrigatorio("padrao")
def excluir_meu_chamado(id_chamado):
    excluiu = excluir_chamado(session.get("id_empresa"), session.get("id_funcionario"), id_chamado)
    if not excluiu:
        abort(404)
    flash("Chamado excluído.")
    return redirect(url_for("meus_chamados"))


# ---------------------------------------------------------------
# Dashboard do técnico
# ---------------------------------------------------------------
SQL_CHAMADOS_TECNICO = """
    SELECT c.IdChamado AS id, c.Descricao AS descricao, c.Status AS status,
           c.DataHoraAbertura AS aberto_em, c.Previsao AS previsao, c.IdTecnico AS id_tecnico,
           c.IdPrioridade AS id_prioridade, p.DescricaoPrioridade AS prioridade,
           u.NomeUsuario AS funcionario
      FROM chamado c
      JOIN prioridade p ON p.IdPrioridade = c.IdPrioridade
      JOIN funcionariopadrao fp ON fp.IdFuncionario = c.IdFuncionario
      JOIN usuario u ON u.IdUsuario = fp.IdUsuario
"""


def listar_prioridades():
    return consultar("SELECT IdPrioridade AS id, DescricaoPrioridade AS descricao FROM prioridade ORDER BY IdPrioridade")


def listar_chamados_pendentes(id_empresa):
    return consultar(
        SQL_CHAMADOS_TECNICO
        + " WHERE c.IdEmpresa = %s AND c.Status <> 'finalizado' ORDER BY c.IdPrioridade, c.IdChamado",
        (id_empresa,),
    )


def contar_resolvidos_hoje(id_tecnico):
    resultado = consultar_um(
        """
        SELECT COUNT(*) AS total FROM chamado
         WHERE IdTecnico = %s AND Status = 'finalizado' AND DATE(DataHoraFechamento) = %s
        """,
        (id_tecnico, date.today()),
    )
    return resultado["total"]


def tela_tecnico(chamado_aberto=None):
    pendentes = listar_chamados_pendentes(session.get("id_empresa"))
    resolvidos_hoje = contar_resolvidos_hoje(session.get("id_tecnico"))
    return render_template(
        "public/dashboard_tecnico.html",
        chamados=pendentes, resolvidos_hoje=resolvidos_hoje,
        aberto=chamado_aberto, prioridades=listar_prioridades(),
    )


@app.route("/tecnico")
@portal_obrigatorio("tecnico")
def dashboard_tecnico():
    return tela_tecnico()



# Modal de atendimento (técnico)

def buscar_chamado(id_empresa, id_chamado):
    chamado = consultar_um(SQL_CHAMADOS_TECNICO + " WHERE c.IdEmpresa = %s AND c.IdChamado = %s",
                           (id_empresa, id_chamado))
    if chamado:
        chamado["comentarios"] = consultar(
            """
            SELECT u.NomeUsuario AS autor, c.Texto AS texto, c.DataHora AS em
              FROM comentario c JOIN usuario u ON u.IdUsuario = c.IdUsuario
             WHERE c.IdChamado = %s ORDER BY c.DataHora
            """,
            (id_chamado,),
        )
    return chamado


def chamado_em_aberto(id_chamado):
    """Chamado da empresa do técnico que ainda não foi finalizado (senão, 404)."""
    chamado = buscar_chamado(session.get("id_empresa"), id_chamado)
    if chamado is None or chamado["status"] == "finalizado":
        abort(404)
    return chamado


def erro_de_atendimento(chamado):
    # Só o técnico que assumiu o chamado pode alterá-lo.
    if chamado["id_tecnico"] is None:
        return "Assuma o chamado antes de fazer alterações."
    if chamado["id_tecnico"] != session.get("id_tecnico"):
        return "Este chamado já foi assumido por outro técnico."
    return None


@app.route("/tecnico/chamado/<int:id_chamado>")
@portal_obrigatorio("tecnico")
def ver_chamado(id_chamado):
    return tela_tecnico(chamado_em_aberto(id_chamado))


@app.route("/tecnico/chamado/<int:id_chamado>/assumir", methods=["POST"])
@portal_obrigatorio("tecnico")
def assumir_chamado(id_chamado):
    chamado = chamado_em_aberto(id_chamado)

    if chamado["id_tecnico"] is not None and chamado["id_tecnico"] != session.get("id_tecnico"):
        flash("Este chamado já foi assumido por outro técnico.", "erro")
        return redirect(url_for("dashboard_tecnico"))

    executar(
        "UPDATE chamado SET IdTecnico = %s, Status = 'em_andamento' WHERE IdChamado = %s AND IdTecnico IS NULL",
        (session.get("id_tecnico"), id_chamado),
    )
    flash("Chamado assumido.")
    return redirect(url_for("ver_chamado", id_chamado=id_chamado))


@app.route("/tecnico/chamado/<int:id_chamado>/atualizar", methods=["POST"])
@portal_obrigatorio("tecnico")
def atualizar_chamado(id_chamado):
    chamado = chamado_em_aberto(id_chamado)

    erro = erro_de_atendimento(chamado)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("dashboard_tecnico"))

    id_prioridade = request.form.get("id_prioridade", type=int)
    if id_prioridade not in {p["id"] for p in listar_prioridades()}:
        id_prioridade = chamado["id_prioridade"]

    previsao = request.form.get("previsao", "").strip()
    comentario = request.form.get("comentario", "").strip()
    with transacao():
        executar("UPDATE chamado SET IdPrioridade = %s, Previsao = %s WHERE IdChamado = %s",
                 (id_prioridade, previsao[:25] or None, id_chamado))
        if comentario:
            executar(
                "INSERT INTO comentario (IdChamado, IdUsuario, Texto, DataHora) VALUES (%s, %s, %s, %s)",
                (id_chamado, session.get("id_usuario"), comentario[:500], datetime.now()),
            )

    flash("Alterações salvas.")
    return redirect(url_for("ver_chamado", id_chamado=id_chamado))


@app.route("/tecnico/chamado/<int:id_chamado>/finalizar", methods=["POST"])
@portal_obrigatorio("tecnico")
def finalizar_chamado(id_chamado):
    chamado = chamado_em_aberto(id_chamado)

    erro = erro_de_atendimento(chamado)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("dashboard_tecnico"))

    solucao = request.form.get("solucao", "").strip()
    if not solucao:
        flash("Descreva a solução antes de finalizar o chamado.", "erro")
        return redirect(url_for("ver_chamado", id_chamado=id_chamado))

    agora = datetime.now()
    minutos = int((agora - chamado["aberto_em"]).total_seconds() // 60)
    executar(
        """
        UPDATE chamado SET Solucao = %s, Status = 'finalizado', DataHoraFechamento = %s, TempoGasto = %s
         WHERE IdChamado = %s
        """,
        (solucao[:1000], agora, minutos, id_chamado),
    )
    flash("Chamado finalizado.")
    return redirect(url_for("dashboard_tecnico"))


if __name__ == "__main__":
    app.run(debug=True)
