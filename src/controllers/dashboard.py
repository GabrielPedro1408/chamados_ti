"""Dashboard da EMPRESA: indicadores dos chamados abertos no período."""
from collections import Counter
from datetime import date

from flask import render_template, request, session
from flask.views import MethodView

from src.auth import login_obrigatorio
from src.db import consultar
from src.utils import formatar_duracao, parse_data, primeiro_dia_mes

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
MESES_COMPLETOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                   "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
# Cores dos técnicos no gráfico (se houver mais técnicos que cores, elas se repetem).
PALETA = ["#0f7c78", "#d97706", "#3b6fb6", "#b3446c", "#6b8e23", "#7a5195"]


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


class Dashboard(MethodView):
    decorators = [login_obrigatorio]

    def get(self):
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
            "public/dashboard_empresa.html",
            dados=montar_dashboard(chamados, ini, fim),
            data_inicio=ini.isoformat(), data_final=fim.isoformat(), erro_filtro=erro_filtro,
        )
