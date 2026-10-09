#!/usr/bin/env python3
"""Gera um único pacote para revisão humana; nenhuma denúncia é enviada.

Aceita dados fornecidos pelo operador; não usa redes, cookies ou credenciais.
"""
import argparse
import os
from pathlib import Path
import sys

from instaguard import CATEGORIES, check_url, clean_username
from submission import OFFICIAL_HELP_URL, prepare_statement


def build_case(profile_url, category, reason, evidence_text=""):
    username = clean_username(profile_url)
    if category not in CATEGORIES:
        raise ValueError("Categoria inválida.")
    reason = reason.strip()
    if not reason or len(reason) > 2000:
        raise ValueError("Informe fatos observados (até 2000 caracteres).")
    evidence_urls = [line.strip() for line in evidence_text.splitlines() if line.strip()]
    if len(evidence_urls) > 20:
        raise ValueError("Limite de 20 links de evidência por caso.")
    evidence = [
        {"url": check_url(url), "description": "Link fornecido pelo operador; conteúdo não verificado"}
        for url in evidence_urls
    ]
    return {"username": username, "category": category, "reason": reason, "evidence": evidence}


def main(argv=None):
    p = argparse.ArgumentParser(description="Prepara um único relato para envio humano.")
    p.add_argument("--profile-url", required=True)
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--reason", required=True)
    p.add_argument("--evidence-urls", default="", help="Links HTTPS separados por nova linha")
    p.add_argument("--output-dir", default="manual-review-package")
    args = p.parse_args(argv)
    try:
        case = build_case(args.profile_url, args.category, args.reason, args.evidence_urls)
        dest = Path(args.output_dir)
        # A new directory avoids partial overwrite of an earlier review package.
        dest.mkdir(parents=True, exist_ok=False, mode=0o700)
        file = dest / "revisao-manual.txt"
        # Não substitui arquivo anterior; evita alterações silenciosas.
        with os.fdopen(os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as out:
            out.write(prepare_statement(case) + "\n")
        with os.fdopen(os.open(dest / "LEIA-ME.txt", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as out:
            out.write(
                "Pacote de revisão manual — InstaGuard\n"
                "Nenhuma denúncia foi enviada. Nenhuma informação foi verificada.\n"
                "Revise cada alegação antes de enviar uma denúncia legítima.\n"
                "Consulte a ajuda oficial do Instagram: " + OFFICIAL_HELP_URL + "\n"
            )
        print(f"Pacote de revisão manual criado em {dest}/; 0 denúncias enviadas.")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

