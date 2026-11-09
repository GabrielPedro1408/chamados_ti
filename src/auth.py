"""Controle de acesso: quem está logado e quais telas cada perfil pode abrir.

Os decoradores daqui são usados nos controllers pelo atributo `decorators`
das classes MethodView, por exemplo:

    class Dashboard(MethodView):
        decorators = [login_obrigatorio]
"""
from functools import wraps

from flask import redirect, session, url_for

from src.db import consultar_um

SQL_EMPRESA = """
    SELECT IdEmpresa AS id, RazaoSocial AS razao_social, Cnpj AS cnpj, SenhaHash AS senha_hash
      FROM empresa
"""


# ---------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------
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


def dados_do_menu():
    """Variáveis disponíveis em todos os templates (usadas no menu lateral)."""
    empresa = empresa_logada()
    return {"empresa_atual": empresa, "e_empresa": empresa is not None}


# ---------------------------------------------------------------
# Funcionário (padrão ou técnico)
# ---------------------------------------------------------------
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
