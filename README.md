# WikiLeitura — Sistema de Biblioteca em Python & MySQL

O WikiLeitura é uma aplicação em linha de comando (CLI) desenvolvida em Python no âmbito do Projeto Integrador, destinada à gestão de acervo, utilizadores e empréstimos de uma biblioteca nacional. O sistema liga-se a uma base de dados relacional MySQL (gerida através do phpMyAdmin) recorrendo ao mysql-connector-python e ao bcrypt para autenticação e proteção de credenciais.

A estrutura separa os fluxos entre Administradores e Leitores, com validação de dados de entrada, consultas parametrizadas e operações CRUD (Create, Read, Update, Delete) sobre as tabelas do banco (g06_Administradores, g06_Leitores, g06_Livros, g06_Categorias e g06_Estante).

## Funcionalidades
Autenticação e segurança: início de sessão distinto por perfil, ocultação de palavra-passe no terminal (getpass) e armazenamento com hash bcrypt.
Gestão administrativa: registo de administradores e livros, consulta com categorias, remoção com confirmação e tratamento de integridade referencial.
Área do leitor: listagem e pesquisa de livros por nome, empréstimo (adição à estante), acompanhamento do progresso de leitura e devolução.
Validação e diagnóstico: verificação de e-mails, datas, telefones e números de contrato, além do script `teste_conexao.py` para diagnosticar a ligação ao servidor.

## Estrutura do repositório
WikiLeitura_CRUD.py — aplicação principal em linha de comando com as regras de negócio e operações CRUD.
teste_conexao.py — script auxiliar para testar a ligação ao MySQL e inspecionar a estrutura das tabelas.
config.example.py — modelo com variáveis de ligação fictícias (config.py real é ignorado pelo .gitignore).
.gitignore — lista de ficheiros e pastas ignorados no controlo de versões.

## Como executar
1. Instala as dependências necessárias:
```bash
pip install mysql-connector-python bcrypt
```
