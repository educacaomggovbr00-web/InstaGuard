#!/usr/bin/env python3
"""Investigador local de sinais públicos: não coleta dados de perfis automaticamente.

Recebe dados fornecidos voluntariamente por um operador e destaca declarações
que merecem revisão humana. Não deduz identidade, não classifica alguém como
fraudador nem envia denúncias.
"""
import argparse
import json
import re
from urllib.parse import urlparse

from instaguard import clean_username

LINK_PATTERN = re.compile(r"https?://[^\\s]+", re.IGNORECASE)
SUSPICIOUS_CLAIMS = (
    ("pedido de dinheiro", re.compile(
        r"\\b(pix|transfer[eê]ncia|dep[oó]sito|manda(r)? dinheiro)\\b",
        re.IGNORECASE)),
    ("promessa financeira", re.compile(
        r"\\b(lucro garantido|dinheiro f[aá]cil|renda garantida)\\b",
        re.IGNORECASE)),
    ("pedido de credenciais", re.compile(
        r"\\b(senha|c[oó]digo de verifica[cç][aã]o|c[oó]digo de login)\\b",
        re.IGNORECASE)),
)


def assess(username, display_name="", bio="", source_url=""):
    user = clean_username(username)
    if len(display_name) > 120 or len(bio) > 2200:
        raise ValueError("Nome ou biografia acima do limite permitido.")
    if source_url:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("A fonte precisa ser uma URL HTTPS válida, sem credenciais.")
    signals = [
        {"indicator": name, "excerpt": match.group(0)}
        for name, pattern in SUSPICIOUS_CLAIMS
        if (match := pattern.search(bio)) is not None
    ]
    links = [match.rstrip(".,;!?)") for match in LINK_PATTERN.findall(bio)]
    return {
        "username": user,
        "profile_url": f"https://www.instagram.com/{user}/",
        "display_name_reported": display_name,
        "bio_reported": bio,
        "source_url": source_url,
        "links_in_bio": links,
        "review_indicators": signals,
        "conclusion": "Revisão humana necessária. Indicadores não comprovam fraude.",
        "creator_identity": "Não determinada; nome de exibição não comprova autoria.",
        "collection_method": "Dados informados manualmente; nenhuma consulta ao Instagram.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Analise local de informacoes publicas fornecidas manualmente")
    p.add_argument("username", help="@usuario do Instagram")
    p.add_argument("--display-name", default="", help="Nome publicamente exibido")
    p.add_argument("--bio", default="", help="Biografia publica fornecida pelo operador")
    p.add_argument("--source", default="", help="URL HTTPS da fonte informada")
    args = p.parse_args(argv)
    try:
        result = assess(args.username, args.display_name, args.bio, args.source)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
