"""Portal do TÉCNICO: fila de chamados pendentes e modal de atendimento."""
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, session, url_for
from flask.views import MethodView

from src.auth import portal_obrigatorio
from src.db import consultar, consultar_um, executar, transacao

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


class DashboardTecnico(MethodView):
    decorators = [portal_obrigatorio("tecnico")]

    def get(self):
        return tela_tecnico()


# Modal de atendimento
class VerChamado(MethodView):
    decorators = [portal_obrigatorio("tecnico")]

    def get(self, id_chamado):
        return tela_tecnico(chamado_em_aberto(id_chamado))


class AssumirChamado(MethodView):
    decorators = [portal_obrigatorio("tecnico")]

    def post(self, id_chamado):
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


class AtualizarChamado(MethodView):
    decorators = [portal_obrigatorio("tecnico")]

    def post(self, id_chamado):
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


class FinalizarChamado(MethodView):
    decorators = [portal_obrigatorio("tecnico")]

    def post(self, id_chamado):
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
