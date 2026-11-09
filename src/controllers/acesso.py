"""Tela inicial, cadastro/login da empresa, login do funcionário e logout.

Regra de negócio: a EMPRESA se cadastra sozinha; o FUNCIONÁRIO não tem
autocadastro, ele é criado pela empresa em /funcionarios.
O mesmo login serve para funcionário padrão e técnico: o tipo do usuário
decide qual tela ele vê depois de entrar.
"""
import re

from flask import redirect, render_template, request, session, url_for
from flask.views import MethodView
from werkzeug.security import check_password_hash, generate_password_hash

from src.auth import SQL_EMPRESA
from src.db import consultar_um, executar
from src.utils import cnpj_valido, normalizar_usuario, so_digitos


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


def buscar_empresa(cnpj):
    return consultar_um(SQL_EMPRESA + " WHERE Cnpj = %s", (cnpj,))


class Inicio(MethodView):
    def get(self):
        return render_template("public/inicio.html")


class LoginFuncionario(MethodView):
    def tela(self, usuario="", erros=None):
        return render_template("public/login_funcionario.html", usuario=usuario, erros=erros or {})

    def get(self):
        return self.tela()

    def post(self):
        usuario_digitado = normalizar_usuario(request.form.get("usuario", ""))
        senha = request.form.get("senha", "")
        conta = autenticar(usuario_digitado, senha)

        if conta is None:
            return self.tela(usuario_digitado, {"geral": "Usuário ou senha inválidos."})

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


class CadastroEmpresa(MethodView):
    def tela(self, cnpj="", razao_social="", erros=None):
        return render_template(
            "public/cadastro_empresa.html", titulo="Cadastro de empresa", botao="Cadastrar",
            cadastro=True, cnpj=cnpj, razao_social=razao_social, erros=erros or {}, mensagem=None,
        )

    def get(self):
        return self.tela()

    def post(self):
        razao = " ".join(request.form.get("razao_social", "").split())
        cnpj_digitado = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")
        cnpj = so_digitos(cnpj_digitado)
        erros = {}

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

        if erros:
            return self.tela(cnpj_digitado, razao, erros)

        executar(
            "INSERT INTO empresa (RazaoSocial, Cnpj, SenhaHash) VALUES (%s, %s, %s)",
            (razao, cnpj, generate_password_hash(senha)),  # nunca guarde a senha pura
        )
        return redirect(url_for("login_empresa", msg="cadastrada"))


class LoginEmpresa(MethodView):
    def tela(self, cnpj="", erros=None):
        mensagem = "Empresa cadastrada! Agora é só entrar." if request.args.get("msg") == "cadastrada" else None
        return render_template(
            "public/cadastro_empresa.html", titulo="Login", botao="Entrar",
            cadastro=False, cnpj=cnpj, razao_social="", erros=erros or {}, mensagem=mensagem,
        )

    def get(self):
        return self.tela()

    def post(self):
        cnpj_digitado = request.form.get("cnpj", "").strip()
        senha = request.form.get("senha", "")
        empresa = buscar_empresa(so_digitos(cnpj_digitado))

        if empresa and check_password_hash(empresa["senha_hash"], senha):
            session.clear()
            session["empresa_id"] = empresa["id"]
            return redirect(url_for("dashboard"))
        return self.tela(cnpj_digitado, {"geral": "CNPJ ou senha inválidos."})


class Sair(MethodView):
    def get(self):
        session.clear()
        return redirect(url_for("inicio"))
