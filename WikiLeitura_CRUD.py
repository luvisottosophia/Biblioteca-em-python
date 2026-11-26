import getpass # esconde a senha
import re # e-mail, telefone e contato
from datetime import date, datetime

import bcrypt # proteção de senha
import mysql.connector
from mysql.connector import Error, IntegrityError

import config

PERFIS_VALIDOS = ["Admin", "Desenvolvedor"]

# As funções que mexem no banco devolvem sempre (resultado, erro):
#   deu certo -> (resultado, None)
#   deu errado -> (None ou False, "mensagem do erro")


# =========== CONEXÃO ============

def conectar(): # Abre a conexão com o MySQL usando o config.py
    return mysql.connector.connect(
        host=str(config.host).strip(),
        port=int(getattr(config, "port", 3306)),
        user=str(config.user).strip(),
        password=config.password,
        database=str(config.database).strip(),
        charset="utf8mb4",
        connection_timeout=10,
    )


def testar_conexao():
    # Tenta conectar e, se falhar, explica o motivo: senha errada, banco inexistente, IP não liberado ou config.py incompleto
    try:
        con = conectar()
        con.close()
        return True, None
    except Error as e:
        causas = {
            1045: "Usuário ou senha incorretos (confira o config.py).",
            1049: "O nome do banco (database) não existe (confira o config.py).",
            2003: "Não conectou ao servidor. No hPanel da Hostinger, vá em "
                  "Bancos de dados > MySQL Remoto e libere o seu IP; confira também o host.",
            2005: "O host está errado (confira o config.py).",
        }
        return False, f"{causas.get(e.errno, 'Falha na conexão.')} (detalhe: {e})"
    except AttributeError as e:
        return False, f"O config.py está incompleto ou é outro arquivo: {e}"


def executar(sql, params=()):
     # Roda INSERT/UPDATE/DELETE. Confirma a alteração e devolve o id gerado e quantas linhas mudaram.
    con = conectar()
    cur = con.cursor()
    try:
        cur.execute(sql, params)
        con.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        cur.close()
        con.close()


def consultar(sql, params=()):
    # Roda um SELECT e devolve um registro (ou None).
    con = conectar()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        con.close()
# conexão nunca fica aberta por engano por conta do try/finally
# Try: se alguma linha dentro dele causar um erro, o Python para ali e procura quem trate o erro
# Finally: sem o finally, se o execute falhar, o close() nunca será chamado, e a conexão ficará aberta

# =========== ENTRADA DE DADOS ============

# repete a pergunta até o usuário digitar um número inteiro
def ler_mensagem(mensagem, minimo=None, maximo=None): # consegue definir a quantidade de minimo e máximo
    while True:
        try:
            valor = int(input(mensagem).strip())
        except ValueError: # trata o erro, caso aconteça algum erro, o código roda e o programa continua em vez de quebrar
            print("Digite apenas números inteiros.")
            continue
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            print("Valor fora do intervalo permitido.")
            continue
        return valor


def confirmar_mensagem(mensagem): # True ou False
    while True:
        r = input(mensagem + " (S/N): ").strip().lower()
        if r in ("s", "n"):
            return r == "s"
        print("Opção inválida!")


# =========== VALIDAÇÕES ============

# Cada uma devolve a mensagem de erro, ou None se estiver tudo certo.
# =========== VALIDAÇÕES BÁSICAS ===========

def validar_texto(valor, campo, tam_max=100):
    if not valor:
        return f"{campo} não pode ficar vazio."
    if len(valor) > tam_max:
        return f"{campo} deve ter no máximo {tam_max} caracteres."
    return None


def validar_email(email):
    email = (email or "").strip().lower()
    if not email:
        return "E-mail não pode ficar vazio."
    if len(email) > 80:
        return "E-mail deve ter no máximo 80 caracteres."
    if "@" not in email or "." not in email:
        return "E-mail inválido (deve conter '@' e '.')."
    return None


def validar_senha(senha):
    if not senha:
        return "A senha não pode ficar vazia."
    if len(senha) < 6:
        return "A senha deve ter pelo menos 6 caracteres."
    if len(senha) > 70:
        return "A senha é muito longa."
    return None


def validar_inteiro(valor, campo, minimo=1, maximo=None):
    # Verifica se é um número válido e está dentro dos limites
    if type(valor) != int:
        return f"{campo} deve ser um número inteiro."
    if valor < minimo:
        return f"{campo} deve ser no mínimo {minimo}."
    if maximo is not None and valor > maximo:
        return f"{campo} deve ser no máximo {maximo}."
    return None


def validar_data(valor):
    # Aceita apenas o padrão brasileiro DD/MM/AAAA (ex: 15/05/2000)
    try:
        data = datetime.strptime(str(valor).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None, "Data inválida. Use o formato DD/MM/AAAA."
        
    if data > date.today():
        return None, "A data não pode estar no futuro."
    return data, None


def validar_telefone(telefone):
    if not telefone:
        return None, "O telefone não pode ficar vazio."
    digitos = ""
    for caractere in str(telefone):
        if caractere.isdigit():
            digitos = digitos + caractere     
    if len(digitos) != 10 and len(digitos) != 11: # Verifica se tem 10 ou 11 dígitos (com DDD)
        return None, "Telefone inválido. Use DDD + número (10 ou 11 dígitos)."
    if digitos[0] == "0":
        return None, "O DDD não pode começar com 0."   
    return digitos, None


def validar_nascimento(valor):
    data, erro = validar_data(valor)
    if erro:
        return None, erro
    if data >= date.today():
        return None, "A data de nascimento deve ser anterior a hoje."
    if data.year < 1900:
        return None, "Ano de nascimento inválido."
    return data, None


def validar_contrato(num):
    num = (num or "").strip().upper()
    if not num:
        return None, "O número do contrato não pode ficar vazio."
    if num[:4] != "CTR-":
        return None, "O contrato deve começar com 'CTR-'."
    if len(num) < 8:
        return None, "O número do contrato é muito curto."
    return num, None

def gerar_hash(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# =========== ADM ============

def criar_perfil_adm(nome_adm, email_adm, senha, telefone_adm, perfil,
                     num_contrato):
    nome_adm = (nome_adm or "").strip()
    email_adm = (email_adm or "").strip().lower()
    perfil = (perfil or "").strip().capitalize() or PERFIS_VALIDOS[0]

    erro = validar_texto(nome_adm, "Nome", 50) or validar_email(email_adm) or validar_senha(senha)
    telefone_adm, erro_tel = validar_telefone(telefone_adm)
    erro = erro or erro_tel
    if not erro and perfil not in PERFIS_VALIDOS:
        erro = "Perfil inválido. Use: " + ", ".join(PERFIS_VALIDOS) + "."
    num_contrato, erro_ctr = validar_contrato(
        num_contrato, )
    erro = erro or erro_ctr
    if erro:
        return None, erro

    con_adm = conectar()
    cru_adm = con_adm.cursor()

    try:
        cru_adm.execute("SELECT IDAdmin FROM g06_Administradores WHERE EmailAdmin = %s", (email_adm,))
        if cru_adm.fetchone():
            return None, "E-mail já cadastrado."

        cru_adm.execute("SELECT IDAdmin FROM g06_Administradores WHERE NumContrato = %s", (num_contrato,))
        if cru_adm.fetchone():
            return None, "Nº de contrato já cadastrado."

        senha = gerar_hash(senha)

        cru_adm.execute(
            "INSERT INTO g06_Administradores (NomeAdmin, EmailAdmin, SenhaHash, Perfil, TelefoneAdmin, NumContrato) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nome_adm, email_adm, senha, perfil, telefone_adm, num_contrato),
        )
        con_adm.commit()
        return cru_adm.lastrowid, None
    except IntegrityError as e:
        return None, f"Dados recusados pelo banco: {e}"
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"
    finally:
        cru_adm.close()
        con_adm.close()


# =========== LEITOR ============

def criar_perfil_leitor(nome, email, senha, nascimento):
    nome = (nome or "").strip()
    email = (email or "").strip().lower()

    erro = validar_texto(nome, "Nome", 50) or validar_email(email) or validar_senha(senha)
    nascimento, erro_nasc = validar_nascimento(nascimento)
    erro = erro or erro_nasc
    if erro:
        return None, erro

    try:
        if consultar("SELECT IDLeitor FROM g06_Leitores WHERE EmailLeitor = %s", (email,)):
            return None, "E-mail já cadastrado."
        id_lei, _ = executar(
            "INSERT INTO g06_Leitores(NomeLeitor, EmailLeitor, SenhaHash, NascimentoLeitor) "
            "VALUES (%s, %s, %s, %s)",
            (nome, email, gerar_hash(senha), nascimento),
        )
        return id_lei, None
    except IntegrityError as e:
        return None, f"Dados recusados pelo banco: {e}"
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"


# =========== LIVRO ============

def criar_livros(nome, id_categoria, lancamento, num_paginas, id_admin):
    nome = (nome or "").strip()

    erro = (validar_texto(nome, "Nome do livro", 150)
            or validar_inteiro(id_categoria, "Categoria")
            or validar_inteiro(num_paginas, "Páginas", 1, 10000)
            or validar_inteiro(id_admin, "Administrador"))
    data, erro_data = validar_data(lancamento)
    erro = erro or erro_data
    if erro:
        return None, erro

    try:
        if consultar("SELECT IDLivro FROM g06_Livros WHERE LOWER(NomeLivro) = LOWER(%s)", (nome,)):
            return None, "Livro já cadastrado."
        id_livro, _ = executar(
            "INSERT INTO g06_Livros(NomeLivro, IDCategoria, LancamentoLivro, NumPagLivro, IDAdmin) "
            "VALUES (%s, %s, %s, %s, %s)",
            (nome, id_categoria, data, num_paginas, id_admin),
        )
        return id_livro, None
    except IntegrityError:
        return None, "Categoria ou administrador não existe."
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"

def remover_livro(id_livro):
    erro = validar_inteiro(id_livro, "Código do livro")
    if erro:
        return False, erro

    try:
        _, linhas = executar("DELETE FROM g06_Livros WHERE IDLivro = %s", (id_livro,))
        if linhas == 0:
            return False, "Livro não encontrado."
        return True, None
    except IntegrityError:
        return False, "Não é possível remover: o livro possui registros vinculados (ex.: empréstimo)."
    except Error as e:
        return False, f"Erro ao acessar o banco de dados: {e}"


# =========== LOGIN ============
# Retorna (usuario, None) se der certo, ou (None, "mensagem") se falhar.
# usuario é um dict com id e nome (e Perfil, se for adm).

def login(tipo, email, senha):
    if tipo == "adm":
        sql = ("SELECT IDAdmin AS id, NomeAdmin AS nome, SenhaHash, Perfil "
               "FROM g06_Administradores WHERE EmailAdmin = %s")
    elif tipo == "leitor":
        sql = ("SELECT IDLeitor AS id, NomeLeitor AS nome, SenhaHash "
               "FROM g06_Leitores WHERE EmailLeitor = %s")
    else:
        return None, "Tipo de login inválido. Use 'adm' ou 'leitor'."

    email = (email or "").strip().lower()
    if not email or not senha:
        return None, "Informe e-mail e senha."

    try:
        usuario = consultar(sql, (email,))
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"

    if not usuario:
        return None, "E-mail ou senha incorretos."
    try:
        senha = bcrypt.checkpw(senha.encode("utf-8"), usuario["SenhaHash"].encode("utf-8"))
    except ValueError:
        senha = False
    if not senha:
        return None, "E-mail ou senha incorretos."

    del usuario["SenhaHash"]
    return usuario, None


# =========== MENU PRINCIPAL ============

def existe_adm():
    try:
        return consultar("SELECT IDAdmin FROM g06_Administradores LIMIT 1") is not None
    except Error:
        return True  # se o banco falhar, não oferece criar administrador


def cadastrar_adm():
    print("\n--- Novo administrador ---")
    nome = input("Nome: ")
    email = input("E-mail: ")
    telefone = input("Telefone com DDD (ex.: 47987654321): ")
    senha = getpass.getpass("Senha: ")
    perfil = input("Perfil (" + "/".join(PERFIS_VALIDOS) + ") [Enter = " + PERFIS_VALIDOS[0] + "]: ")
    num_contrato = input("Nº do contrato (CTR-AAAA-NNNNN): ")
    id_adm, erro = criar_perfil_adm(nome, email, senha, telefone, perfil, num_contrato)
    print(erro if erro else f"Administrador criado! Código: {id_adm}")


def cadastrar_leitor():
    print("\n--- Criar conta de leitor ---")
    nome = input("Nome: ")
    email = input("E-mail: ")
    senha = getpass.getpass("Senha: ")
    nascimento = input("Data de nascimento (DD/MM/AAAA): ")
    id_lei, erro = criar_perfil_leitor(nome, email, senha, nascimento)
    print(erro if erro else f"Conta criada! Código: {id_lei}")


def cadastrar_livro(id_admin):
    print("\n--- Novo livro ---")
    nome = input("Nome do livro: ")
    id_categoria = ler_mensagem("Código da categoria: ", 1)
    lancamento = input("Lançamento (DD/MM/AAAA): ")
    paginas = ler_mensagem("Número de páginas: ", 1, 10000)
    id_livro, erro = criar_livros(nome, id_categoria, lancamento, paginas, id_admin)
    print(erro if erro else f"Livro cadastrado! Código: {id_livro}")


def excluir_livro():
    print("\n--- Remover livro ---")
    codigo = ler_mensagem("Código do livro: ", 1)
    if not confirmar_mensagem(f"Remover o livro {codigo}?"):
        print("Cancelado.")
        return
    removeu, erro = remover_livro(codigo)
    print("Livro removido!" if removeu else erro)


def fazer_login(tipo):
    email = input("E-mail: ")
    senha = getpass.getpass("Senha: ")
    usuario, erro = login(tipo, email, senha)
    if erro:
        print(erro)
    return usuario


def menu_adm(adm):
    while True:
        print(f"\n=== ADMINISTRADOR: {adm['nome']} ===")
        print("1 - Cadastrar livro")
        print("2 - Remover livro")
        print("3 - Cadastrar novo administrador")
        print("0 - Sair")
        op = ler_mensagem("Opção: ")
        if op == 1:
            cadastrar_livro(adm["id"])
        elif op == 2:
            excluir_livro()
        elif op == 3:
            cadastrar_adm()
        elif op == 0:
            return
        else:
            print("Opção inválida!")


# =========== MENU LEITOR ============

def consultar_todos(sql, params=()):
    # tupla (ou lista) contém os valores reais que vão substituir os marcadores %s da string sql
   # SELECT. Retorna uma lista de registros (dicts).
    con = conectar()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        cur.close()
        con.close()


# ---------- Livros (consulta) ----------

def listar_livros(busca=""):
   # Retorna (lista de livros, None) ou (None, mensagem de erro).
    sql = ("SELECT l.IDLivro, l.NomeLivro, c.NomeCategoria, l.LancamentoLivro, l.NumPagLivro "
           "FROM g06_Livros l "
           "JOIN g06_Categorias c ON c.IDCategoria = l.IDCategoria "
           "WHERE l.NomeLivro LIKE %s "
           "ORDER BY l.NomeLivro")
    try:
        return consultar_todos(sql, (f"%{busca.strip()}%",)), None
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"


def mostrar_livros(livros):
    if not livros:
        print("Nenhum livro encontrado.")
        return
    for l in livros:
        data = l["LancamentoLivro"].strftime("%d/%m/%Y") if l["LancamentoLivro"] else "não informado"
        print("=" * 45)
        print(f"Código:     {l['IDLivro']}")
        print(f"Nome:       {l['NomeLivro']}")
        print(f"Categoria:  {l['NomeCategoria']}")
        print(f"Lançamento: {data}")
        print(f"Páginas:    {l['NumPagLivro']}")
    print("=" * 45)


# ---------- Empréstimo (g06_Estante) ----------
# Pegar um livro emprestado = colocá-lo na estante do leitor.
# Devolver = tirá-lo da estante.

def emprestar_livro(id_leitor, id_livro):
    # Retorna (nome do livro, None) ou (None, mensagem de erro).
    erro = validar_inteiro(id_livro, "Código do livro")
    if erro:
        return None, erro

    try:
        livro = consultar("SELECT NomeLivro FROM g06_Livros WHERE IDLivro = %s", (id_livro,))
        if not livro:
            return None, "Livro não encontrado."

        if consultar("SELECT IDLivro FROM g06_Estante WHERE IDLeitor = %s AND IDLivro = %s",
                     (id_leitor, id_livro)):
            return None, "Este livro já está na sua estante."

        executar("INSERT INTO g06_Estante (IDLeitor, IDLivro) VALUES (%s, %s)",
                 (id_leitor, id_livro))
        return livro["NomeLivro"], None
    except IntegrityError as e:
        return None, f"Dados recusados pelo banco: {e}"
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"


def devolver_livro(id_leitor, id_livro):
    # Retorna (True, None) ou (False, mensagem de erro).
    erro = validar_inteiro(id_livro, "Código do livro")
    if erro:
        return False, erro

    try:
        _, linhas = executar("DELETE FROM g06_Estante WHERE IDLeitor = %s AND IDLivro = %s",
                             (id_leitor, id_livro))
        if linhas == 0:
            return False, "Este livro não está na sua estante."
        return True, None
    except Error as e:
        return False, f"Erro ao acessar o banco de dados: {e}"


def listar_estante(id_leitor):
   # Retorna (lista, None) ou (None, mensagem de erro).
    sql = ("SELECT l.IDLivro, l.NomeLivro, l.NumPagLivro, e.DataLiberacao, "
           "       e.UltimaPagina, e.DataUltimaLeitura, e.Favorito "
           "FROM g06_Estante e "
           "JOIN g06_Livros l ON l.IDLivro = e.IDLivro "
           "WHERE e.IDLeitor = %s "
           "ORDER BY l.NomeLivro")
    try:
        return consultar_todos(sql, (id_leitor,)), None
    except Error as e:
        return None, f"Erro ao acessar o banco de dados: {e}"


def mostrar_estante(itens):
    if not itens:
        print("Sua estante está vazia.")
        return
    for i in itens:
        if i["UltimaPagina"] is None:
            progresso = "não iniciado"
        else:
            progresso = f"página {i['UltimaPagina']} de {i['NumPagLivro']}"
        ultima = i["DataUltimaLeitura"].strftime("%d/%m/%Y %H:%M") if i["DataUltimaLeitura"] else "-"
        print("=" * 45)
        print(f"Código:         {i['IDLivro']}")
        print(f"Nome:           {i['NomeLivro']}")
        print(f"Liberado em:    {i['DataLiberacao'].strftime('%d/%m/%Y')}")
        print(f"Leitura:        {progresso}")
        print(f"Última leitura: {ultima}")
        print(f"Favorito:       {'Sim' if i['Favorito'] else 'Não'}")
    print("=" * 45)


# ---------- Telas do menu ----------

def ver_livros():
    livros, erro = listar_livros()
    if erro:
        print(erro)
    else:
        mostrar_livros(livros)


def buscar_livro():
    busca = input("Nome (ou parte do nome): ")
    livros, erro = listar_livros(busca)
    if erro:
        print(erro)
    else:
        mostrar_livros(livros)


def menu_emprestar(leitor):
    print("\n--- Pegar livro emprestado ---")
    codigo = ler_mensagem("Código do livro (veja na opção 1º ): ", 1)
    nome, erro = emprestar_livro(leitor["id"], codigo)
    print(erro if erro else f"'{nome}' foi adicionado à sua estante!")


def menu_estante(leitor):
    print("\n--- Minha estante ---")
    itens, erro = listar_estante(leitor["id"])
    if erro:
        print(erro)
    else:
        mostrar_estante(itens)


def menu_devolver(leitor):
    print("\n--- Devolver livro ---")
    codigo = ler_mensagem("Código do livro: ", 1)
    if not confirmar_mensagem(f"Devolver o livro {codigo}? Seu progresso de leitura nele será apagado."):
        print("Cancelado.")
        return
    devolveu, erro = devolver_livro(leitor["id"], codigo)
    print("Livro devolvido!" if devolveu else erro)


def menu_leitor(leitor):
    while True:
        print(f"\n=== LEITOR: {leitor['nome']} ===")
        print("1º - Ver todos os livros")
        print("2º - Buscar livro pelo nome")
        print("3º - Pegar livro emprestado")
        print("4º - Minha estante")
        print("5º - Devolver livro")
        print("0 - Sair")
        op = ler_mensagem("Opção: ")
        if op == 1:
            ver_livros()
        elif op == 2:
            buscar_livro()
        elif op == 3:
            menu_emprestar(leitor)
        elif op == 4:
            menu_estante(leitor)
        elif op == 5:
            menu_devolver(leitor)
        elif op == 0:
            return
        else:
            print("Opção inválida!")


def menu_principal():
    while True:
        print("\n=== BIBLIOTECA ===")
        print("1º - Entrar como administrador")
        print("2º - Entrar como leitor")
        print("3º - Criar conta de leitor")
        sem_adm = not existe_adm()
        if sem_adm:
            print("4º - Criar primeiro administrador") 
        print("0 - Sair")

        op = ler_mensagem("Opção: ")
        if op == 1:
            adm = fazer_login("adm")
            if adm:
                menu_adm(adm)
        elif op == 2:
            leitor = fazer_login("leitor")
            if leitor:
                menu_leitor(leitor)
        elif op == 3:
            cadastrar_leitor()
        elif op == 4 and sem_adm:
            cadastrar_adm()
        elif op == 0:
            print("Até logo!")
            return
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    ok, erro = testar_conexao()
    if ok:
        menu_principal()
    else:
        print("Não foi possível conectar ao banco de dados.")
        print(erro)