import random
from datetime import date, datetime, timedelta

from flask import Flask, render_template, request

app = Flask(__name__)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
TECNICOS = ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Rocha", "Elisa Prado"]


def gerar_chamados():
    """Dados de exemplo. Troque por uma consulta ao seu banco (SQLite, MySQL...)."""
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


if __name__ == "__main__":
    app.run(debug=True)