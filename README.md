# 🛠️ Sistema de Chamados de TI

> Projeto prático de aplicação em Python desenvolvido para a disciplina de **Programação em Python** do curso de **Engenharia de Software** do Centro Universitário Padre Anchieta (UniAnchieta).

---

## 📌 Sobre o Projeto

O **Sistema de Chamados de TI** é uma aplicação web desenvolvida com a biblioteca **Flask** e banco de dados **MySQL**. O objetivo principal do sistema é gerenciar e otimizar o fluxo de atendimento a incidentes e requisições de TI, oferecendo interfaces distintas para usuários finais (funcionários) e equipes de suporte (técnicos).

Um dos grandes diferenciais do sistema é o recurso de **troubleshooting inteligente**, que compara automaticamente o problema relatado no novo chamado com históricos de chamados antigos para sugerir soluções prévias, agilizando o tempo de resposta e resolução.

---

## 🚀 Funcionalidades Principais

### 👤 Portal do Funcionário
* **Abertura de Chamados:** Interface simples e intuitiva para envio de requisições.
* **Acompanhamento:** Visualização em tempo real da posição na fila de atendimento e do status (*em andamento*, *pendente*, etc.).
* **Gestão de Chamados:** Opção para cancelar/apagar chamados criados.
* **Métricas Pessoais:** Indicador mensal com o total de chamados abertos pelo usuário.

### 🛠️ Portal do Técnico
* **Painel de Chamados:** Exibição centralizada de todos os chamados pendentes.
* **Métricas de Produtividade:** Contador de chamados resolvidos pelo técnico no dia.
* **Modal de Ações (Pop-up):**
  * Assumir atendimento de um chamado.
  * Alterar nível de prioridade.
  * Adicionar comentários e atualizações.
  * Registrar a solução aplicada e finalizar o chamado.
* **💡 Recomendação Inteligente de Solução:** Comparação de termos do chamado atual com a base histórica para propor soluções recomendadas e poupar tempo de *troubleshooting*.

---

## 🧰 Tecnologias Utilizadas

* **Linguagem:** [Python 3](https://www.python.org/)
* **Framework Web:** [Flask](https://flask.palletsprojects.com/)
* **Banco de Dados:** [MySQL](https://www.mysql.com/)
* **Front-end:** HTML5, CSS3, JavaScript (Interface Web Responsiva)

---

## 🏛️ Contexto Acadêmico

* **Instituição:** Centro Universitário Padre Anchieta (UniAnchieta)
* **Curso:** Engenharia de Software (2º Semestre de 2026)
* **Disciplina:** Programação em Python
* **Docente:** Prof. Dr. Roger Antunes
