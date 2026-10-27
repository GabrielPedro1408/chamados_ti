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


### Telas
- `/` — início: escolha entre entrar como funcionário ou como empresa
- Empresa: cadastro (`/cadastro/empresa`), login, dashboard, setores e equipes, funcionários
- Funcionário padrão (login em `/login/funcionario`): abrir chamado e "Meus chamados"
- Técnico (mesmo login): fila de chamados pendentes e modal de atendimento
