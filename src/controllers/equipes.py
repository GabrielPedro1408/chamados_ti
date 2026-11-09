"""Setores e equipes técnicas (cadastradas pela EMPRESA)."""
from flask import abort, redirect, render_template, request, session, url_for
from flask.views import MethodView

from src.auth import login_obrigatorio
from src.db import consultar, consultar_um, executar

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
        "public/setores_equipes.html",
        setores=listar_setores(session["empresa_id"]),
        equipes=listar_equipes(session["empresa_id"]),
        erros=erros or {}, digitado=digitado or {},
        mensagem=MSGS_SETOR_EQUIPE.get(msg),
        mensagem_erro=msg in ("setor_em_uso", "equipe_em_uso"),
    )


class Equipes(MethodView):
    decorators = [login_obrigatorio]

    def get(self):
        return tela_equipes()


class AdicionarSetor(MethodView):
    decorators = [login_obrigatorio]

    def post(self):
        nome = " ".join(request.form.get("nome", "").split())
        erro = validar_nome(nome, listar_setores(session["empresa_id"]))
        if erro:
            return tela_equipes({"setor": erro}, {"setor": nome})
        executar("INSERT INTO setor (IdEmpresa, NomeSetor) VALUES (%s, %s)", (session["empresa_id"], nome))
        return redirect(url_for("equipes", msg="setor_criado"))


class AdicionarEquipe(MethodView):
    decorators = [login_obrigatorio]

    def post(self):
        nome = " ".join(request.form.get("nome", "").split())
        erro = validar_nome(nome, listar_equipes(session["empresa_id"]))
        if erro:
            return tela_equipes({"equipe": erro}, {"equipe": nome})
        executar("INSERT INTO equipetecnica (IdEmpresa, NomeEquipe) VALUES (%s, %s)", (session["empresa_id"], nome))
        return redirect(url_for("equipes", msg="equipe_criada"))


class ExcluirSetor(MethodView):
    decorators = [login_obrigatorio]

    def post(self, item_id):
        if not consultar_um("SELECT 1 FROM setor WHERE IdSetor = %s AND IdEmpresa = %s",
                            (item_id, session["empresa_id"])):
            abort(404)
        if consultar_um("SELECT 1 FROM funcionariopadrao WHERE IdSetor = %s LIMIT 1", (item_id,)):
            return redirect(url_for("equipes", msg="setor_em_uso"))
        executar("DELETE FROM setor WHERE IdSetor = %s", (item_id,))
        return redirect(url_for("equipes", msg="setor_excluido"))


class ExcluirEquipe(MethodView):
    decorators = [login_obrigatorio]

    def post(self, item_id):
        if not consultar_um("SELECT 1 FROM equipetecnica WHERE IdEquipe = %s AND IdEmpresa = %s",
                            (item_id, session["empresa_id"])):
            abort(404)
        if consultar_um("SELECT 1 FROM funcionariotecnico WHERE IdEquipe = %s LIMIT 1", (item_id,)):
            return redirect(url_for("equipes", msg="equipe_em_uso"))
        executar("DELETE FROM equipetecnica WHERE IdEquipe = %s", (item_id,))
        return redirect(url_for("equipes", msg="equipe_excluida"))
