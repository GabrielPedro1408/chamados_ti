"""Funções auxiliares usadas pelos controllers (datas, textos, CNPJ)."""
import re
from datetime import date, datetime


# ---------------------------------------------------------------
# Datas
# ---------------------------------------------------------------
def primeiro_dia_mes(d, deslocamento=0):
    """Primeiro dia do mês de `d`, andando `deslocamento` meses (pode ser negativo)."""
    total = d.year * 12 + d.month - 1 + deslocamento
    return date(total // 12, total % 12 + 1, 1)


def parse_data(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date() if valor else None
    except ValueError:
        return None


def formatar_duracao(horas):
    if horas is None:
        return "–"
    if horas < 1:
        return f"{round(horas * 60)} min"
    if horas < 48:
        return f"{horas:.1f} h".replace(".", ",")
    return f"{horas / 24:.1f} dias".replace(".", ",")


# ---------------------------------------------------------------
# Textos
# ---------------------------------------------------------------
def normalizar_usuario(texto):
    """Regra do banco: NomeUsuario em MAIÚSCULAS e sem espaços."""
    return re.sub(r"\s", "", texto).upper()


def so_digitos(texto):
    return re.sub(r"\D", "", texto)


# ---------------------------------------------------------------
# CNPJ
# ---------------------------------------------------------------
def formatar_cnpj(d):
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def cnpj_valido(d):
    """Confere 14 dígitos e os dois dígitos verificadores."""
    if len(d) != 14 or d == d[0] * 14:
        return False
    for tam in (12, 13):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos = ([6] + pesos) if tam == 13 else pesos
        soma = sum(int(n) * p for n, p in zip(d[:tam], pesos))
        digito = 11 - soma % 11
        digito = 0 if digito >= 10 else digito
        if int(d[tam]) != digito:
            return False
    return True
