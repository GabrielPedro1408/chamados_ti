## Libs
Estão em `requirements.txt` (Flask, PyMySQL e cryptography):

    pip install -r requirements.txt


### Banco de dados (MySQL / XAMPP)
1. Inicie o MySQL (no XAMPP: botão **Start** do MySQL).
2. Crie o banco executando o script (ou importe `database/deskly.sql` pelo phpMyAdmin):

       mysql -u root < database/deskly.sql

   O script pode ser executado de novo sem apagar dados: ele só cria o que falta.
3. (Opcional) Crie dados de demonstração — empresa, funcionários, técnicos e chamados:

       python -m database.popular_exemplo

   Acessos criados (senha `123456` para todos):
   - Empresa: CNPJ `11.222.333/0001-81`
   - Técnicos: `ANA`, `BRUNO`, `CARLA`
   - Funcionários: `FERNANDA`, `GUSTAVO`, `HELENA`, `IGOR`, `JULIA`

Por padrão o sistema conecta em `localhost:3306`, usuário `root`, sem senha, banco `deskly`
(o padrão do XAMPP). Se o seu MySQL for diferente, defina as variáveis de ambiente
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` e `DB_NAME` antes de rodar.


### Para rodar o projeto:
No terminal, entre na pasta chamados_ti e executa python main.py
Irá te dar um link localhost para poder acessar (ex: http://127.0.0.1:8080)


### Estrutura do projeto
    main.py                  -> ponto de entrada (python main.py)
    src/
      app.py                 -> cria o Flask e registra as rotas de routes.py
      db.py                  -> conexão com o MySQL (consultar, executar, transacao)
      auth.py                -> controle de acesso (login_obrigatorio, portal_obrigatorio, menu)
      utils.py               -> funções auxiliares (datas, CNPJ, textos)
      routes/routes.py       -> lista de rotas: (URL, Controller.as_view("endpoint"))
      controllers/           -> uma classe MethodView por tela, separadas por área:
        acesso.py            -> início, login/cadastro da empresa, login do funcionário, sair
        dashboard.py         -> dashboard da empresa
        equipes.py           -> setores e equipes técnicas
        funcionarios.py      -> CRUD de funcionários
        chamados.py          -> abrir chamado e "Meus chamados" (funcionário padrão)
        tecnico.py           -> fila do técnico e modal de atendimento
      templates/public/      -> páginas (nomes em snake_case, ex.: cadastro_empresa.html)
      templates/partials/    -> pedaços reaproveitados (menu)
      static/css/            -> estilos (nomes em snake_case)
    database/                -> script do banco e dados de exemplo

Para criar uma tela nova:
1. Crie a classe no controller da área (métodos `get`/`post`; para exigir login use
   `decorators = [login_obrigatorio]` ou `decorators = [portal_obrigatorio("padrao")]`).
2. Registre em `src/routes/routes.py`: `("/minha-url", MinhaTela.as_view("minha_tela"))`.
   O nome do `as_view` é o que vai no `url_for("minha_tela")` dos templates.


### Telas
- `/` — início: escolha entre entrar como funcionário ou como empresa
- Empresa: cadastro (`/cadastro/empresa`), login, dashboard, setores e equipes, funcionários
- Funcionário padrão (login em `/login/funcionario`): abrir chamado e "Meus chamados"
- Técnico (mesmo login): fila de chamados pendentes e modal de atendimento
