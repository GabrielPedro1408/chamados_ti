"""Cria uma empresa de demonstração com setores, equipes, funcionários e chamados.

Rode a partir da pasta do projeto, depois de criar o banco (deskly.sql):
    python -m database.popular_exemplo

Se a empresa de exemplo já existir, nada é feito.
"""
import random
from datetime import datetime, time, timedelta

from werkzeug.security import generate_password_hash

from src.app import app, primeiro_dia_mes
from src.db import consultar_um, executar, transacao

CNPJ = "11222333000181"
SENHA = "123456"  # mesma senha para a empresa e todos os usuários de exemplo
SETORES = ["Financeiro", "Recursos Humanos", "Comercial"]
EQUIPES = ["Suporte N1", "Infraestrutura"]
TECNICOS = [("ANA", "Suporte N1"), ("BRUNO", "Suporte N1"), ("CARLA", "Infraestrutura")]
PADRAO = [("FERNANDA", "Financeiro"), ("GUSTAVO", "Financeiro"), ("HELENA", "Recursos Humanos"),
          ("IGOR", "Comercial"), ("JULIA", "Comercial")]
PROBLEMAS = ["Computador não liga", "Impressora sem conexão", "Sem acesso ao e-mail",
             "Internet lenta", "Esqueci a senha do sistema", "Monitor piscando",
             "Instalar programa", "VPN não conecta"]


def popular():
    if consultar_um("SELECT 1 FROM empresa WHERE Cnpj = %s", (CNPJ,)):
        print("A empresa de exemplo já existe. Nada foi feito.")
        return

    rnd = random.Random(42)
    senha_hash = generate_password_hash(SENHA)
    with transacao():
        id_empresa = executar("INSERT INTO empresa (RazaoSocial, Cnpj, SenhaHash) VALUES (%s, %s, %s)",
                              ("Deskly Demonstração LTDA", CNPJ, senha_hash))
        setores = {n: executar("INSERT INTO setor (IdEmpresa, NomeSetor) VALUES (%s, %s)", (id_empresa, n))
                   for n in SETORES}
        equipes = {n: executar("INSERT INTO equipetecnica (IdEmpresa, NomeEquipe) VALUES (%s, %s)", (id_empresa, n))
                   for n in EQUIPES}

        def novo_usuario(nome):
            return executar("INSERT INTO usuario (IdEmpresa, NomeUsuario, SenhaHash) VALUES (%s, %s, %s)",
                            (id_empresa, nome, senha_hash))

        tecnicos = [executar("INSERT INTO funcionariotecnico (IdUsuario, IdEquipe) VALUES (%s, %s)",
                             (novo_usuario(nome), equipes[equipe])) for nome, equipe in TECNICOS]
        funcionarios = [executar("INSERT INTO funcionariopadrao (IdUsuario, IdSetor) VALUES (%s, %s)",
                                 (novo_usuario(nome), setores[setor])) for nome, setor in PADRAO]

        # Chamados espalhados pelos últimos 6 meses; os mais antigos quase todos resolvidos.
        agora = datetime.now()
        inicio = primeiro_dia_mes(agora.date(), -5)
        dias = (agora.date() - inicio).days + 1
        aberturas = sorted(
            min(datetime.combine(inicio + timedelta(days=rnd.randrange(dias)),
                                 time(rnd.randint(8, 17), rnd.choice([0, 15, 30, 45]))),
                agora - timedelta(hours=1))
            for _ in range(80)
        )
        for aberto_em in aberturas:  # em ordem, para o IdChamado seguir a data de abertura
            fechado_em = aberto_em + timedelta(hours=rnd.uniform(1, 60))
            if rnd.random() < 0.75 and fechado_em < agora:
                status, tecnico = "finalizado", rnd.choice(tecnicos)
            elif rnd.random() < 0.4:
                status, tecnico, fechado_em = "em_andamento", rnd.choice(tecnicos), None
            else:
                status, tecnico, fechado_em = "aguardando", None, None

            executar(
                """
                INSERT INTO chamado (IdEmpresa, IdTecnico, IdFuncionario, IdPrioridade, Descricao,
                                     DataHoraAbertura, Status, Solucao, DataHoraFechamento, TempoGasto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (id_empresa, tecnico, rnd.choice(funcionarios), rnd.randint(1, 4), rnd.choice(PROBLEMAS),
                 aberto_em, status, "Resolvido no atendimento." if fechado_em else None, fechado_em,
                 int((fechado_em - aberto_em).total_seconds() // 60) if fechado_em else None),
            )

    print("Dados de exemplo criados.")
    print(f"  Empresa: CNPJ {CNPJ} / senha {SENHA}")
    print(f"  Técnicos: {', '.join(n for n, _ in TECNICOS)} / senha {SENHA}")
    print(f"  Funcionários: {', '.join(n for n, _ in PADRAO)} / senha {SENHA}")


if __name__ == "__main__":
    with app.app_context():
        popular()
