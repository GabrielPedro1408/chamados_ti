"""Mapa de rotas do sistema: (URL, view do controller).

O nome passado em `as_view(...)` é o endpoint usado no `url_for(...)` dos
templates e dos redirects, por isso não deve ser alterado sem atualizar
esses pontos. Os métodos aceitos (GET/POST) vêm dos métodos definidos em
cada classe do controller.
"""
from src.controllers.acesso import CadastroEmpresa, Inicio, LoginEmpresa, LoginFuncionario, Sair
from src.controllers.chamados import AbrirChamado, ExcluirMeuChamado, MeusChamados
from src.controllers.dashboard import Dashboard
from src.controllers.equipes import AdicionarEquipe, AdicionarSetor, Equipes, ExcluirEquipe, ExcluirSetor
from src.controllers.funcionarios import EditarFuncionario, ExcluirFuncionario, Funcionarios
from src.controllers.tecnico import (AssumirChamado, AtualizarChamado, DashboardTecnico, FinalizarChamado,
                                     VerChamado)

routes = [
    # Tela inicial e acessos
    ("/", Inicio.as_view("inicio")),
    ("/login/funcionario", LoginFuncionario.as_view("login_funcionario")),
    ("/cadastro/empresa", CadastroEmpresa.as_view("cadastro_empresa")),
    ("/login/empresa", LoginEmpresa.as_view("login_empresa")),
    ("/sair", Sair.as_view("sair")),

    # Empresa: dashboard
    ("/dashboard", Dashboard.as_view("dashboard")),

    # Empresa: setores e equipes técnicas
    ("/equipes", Equipes.as_view("equipes")),
    ("/equipes/setor", AdicionarSetor.as_view("adicionar_setor")),
    ("/equipes/equipe", AdicionarEquipe.as_view("adicionar_equipe")),
    ("/equipes/setor/<int:item_id>/excluir", ExcluirSetor.as_view("excluir_setor")),
    ("/equipes/equipe/<int:item_id>/excluir", ExcluirEquipe.as_view("excluir_equipe")),

    # Empresa: cadastro de funcionários (CRUD)
    ("/funcionarios", Funcionarios.as_view("funcionarios")),
    ("/funcionarios/<int:func_id>/editar", EditarFuncionario.as_view("editar_funcionario")),
    ("/funcionarios/<int:func_id>/excluir", ExcluirFuncionario.as_view("excluir_funcionario")),

    # Funcionário padrão: abrir chamado e meus chamados
    ("/abrir-chamado", AbrirChamado.as_view("abrir_chamado")),
    ("/meus-chamados", MeusChamados.as_view("meus_chamados")),
    ("/meus-chamados/<int:id_chamado>/excluir", ExcluirMeuChamado.as_view("excluir_meu_chamado")),

    # Técnico: fila de chamados e modal de atendimento
    ("/tecnico", DashboardTecnico.as_view("dashboard_tecnico")),
    ("/tecnico/chamado/<int:id_chamado>", VerChamado.as_view("ver_chamado")),
    ("/tecnico/chamado/<int:id_chamado>/assumir", AssumirChamado.as_view("assumir_chamado")),
    ("/tecnico/chamado/<int:id_chamado>/atualizar", AtualizarChamado.as_view("atualizar_chamado")),
    ("/tecnico/chamado/<int:id_chamado>/finalizar", FinalizarChamado.as_view("finalizar_chamado")),
]
