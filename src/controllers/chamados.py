"""Portal do FUNCIONÁRIO PADRÃO: abrir chamado e acompanhar "Meus chamados"."""
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for
from flask.views import MethodView

from src.auth import portal_obrigatorio
from src.db import consultar, consultar_um, executar

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


class AbrirChamado(MethodView):
    decorators = [portal_obrigatorio("padrao")]

    def tela(self, descricao="", erro=None):
        return render_template(
            "public/abrir_chamado.html",
            descricao=descricao, erro=erro, limite=LIMITE_DESCRICAO,
        )

    def get(self):
        return self.tela()

    def post(self):
        descricao = request.form.get("descricao", "").strip()

        if not descricao:
            return self.tela(descricao, "Descreva o problema antes de abrir o chamado.")
        if len(descricao) > LIMITE_DESCRICAO:
            return self.tela(descricao, f"A descrição pode ter no máximo {LIMITE_DESCRICAO} caracteres.")

        salvar_chamado(session.get("id_empresa"), session.get("id_funcionario"), descricao)
        flash("Chamado aberto com sucesso!")
        return redirect(url_for("meus_chamados"))


class MeusChamados(MethodView):
    decorators = [portal_obrigatorio("padrao")]

    def get(self):
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


class ExcluirMeuChamado(MethodView):
    decorators = [portal_obrigatorio("padrao")]

    def post(self, id_chamado):
        excluiu = excluir_chamado(session.get("id_empresa"), session.get("id_funcionario"), id_chamado)
        if not excluiu:
            abort(404)
        flash("Chamado excluído.")
        return redirect(url_for("meus_chamados"))
