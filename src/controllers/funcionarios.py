"""Cadastro de funcionários (CRUD), feito pela EMPRESA.

No banco, cada funcionário é um `usuario` mais uma linha em
`funcionariopadrao` (com setor) OU em `funcionariotecnico` (com equipe opcional).
"""
from flask import abort, redirect, render_template, request, session, url_for
from flask.views import MethodView
from werkzeug.security import generate_password_hash

from src.auth import login_obrigatorio
from src.controllers.equipes import listar_equipes, listar_setores
from src.db import consultar, consultar_um, executar, transacao
from src.utils import normalizar_usuario

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


def ler_form(campos):
    return {c: request.form.get(c, "").strip() for c in campos}


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
class Funcionarios(MethodView):
    decorators = [login_obrigatorio]

    def get(self):
        setores, equipes = listar_setores(session["empresa_id"]), listar_equipes(session["empresa_id"])
        return tela_cadastro(form_vazio(), {}, setores, equipes)

    def post(self):
        setores, equipes = listar_setores(session["empresa_id"]), listar_equipes(session["empresa_id"])
        form = ler_form(form_vazio())
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, setores, equipes)

        if erros:
            return tela_cadastro(form, erros, setores, equipes)

        with transacao():
            id_usuario = executar(
                "INSERT INTO usuario (IdEmpresa, NomeUsuario, SenhaHash) VALUES (%s, %s, %s)",
                (session["empresa_id"], normalizar_usuario(form["usuario"]),
                 generate_password_hash(senha)),  # nunca guarde a senha pura
            )
            salvar_tipo(id_usuario, form)
        return redirect(url_for("funcionarios", msg="criado"))


# UPDATE
class EditarFuncionario(MethodView):
    decorators = [login_obrigatorio]

    def carregar(self, func_id):
        func = buscar_funcionario(func_id)
        if func is None:
            abort(404)
        setores, equipes = listar_setores(session["empresa_id"]), listar_equipes(session["empresa_id"])
        return func, setores, equipes

    def get(self, func_id):
        func, setores, equipes = self.carregar(func_id)
        form = {
            "usuario": func["usuario"],
            "tipo": func["tipo"],
            "setor": str(func["setor_id"] or ""),
            "equipe": str(func["equipe_id"] or ""),
        }
        return tela_cadastro(form, {}, setores, equipes, editando_id=func_id)

    def post(self, func_id):
        func, setores, equipes = self.carregar(func_id)
        form = ler_form(form_vazio())
        senha = request.form.get("senha", "")
        erros = validar_funcionario(form, senha, setores, equipes, editando=func)

        if erros:
            return tela_cadastro(form, erros, setores, equipes, editando_id=func_id)

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


# DELETE
class ExcluirFuncionario(MethodView):
    decorators = [login_obrigatorio]

    def post(self, func_id):
        if buscar_funcionario(func_id) is None:
            abort(404)
        if tem_chamados(func_id):
            return redirect(url_for("funcionarios", msg="em_uso"))
        with transacao():
            executar("DELETE FROM funcionariopadrao WHERE IdUsuario = %s", (func_id,))
            executar("DELETE FROM funcionariotecnico WHERE IdUsuario = %s", (func_id,))
            executar("DELETE FROM usuario WHERE IdUsuario = %s", (func_id,))
        return redirect(url_for("funcionarios", msg="excluido"))
