#!/usr/bin/env python3
"""Auditoria defensiva local do banco SQLite do InstaGuard.

Sem acesso ao Instagram, sem tráfego de rede e sem divulgação dos casos.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

from instaguard import DEFAULT_DB


def audit_database(database_path):
    """Verifica integridade, estrutura e proteção local, sem modificar o banco."""
    path = Path(database_path).expanduser()
    findings = []

    def add(check, status, detail):
        findings.append({"check": check, "status": status, "detail": detail})

    if path.is_symlink():
        add("database_path", "fail", "Banco por link simbólico: caminho não auditado.")
    elif not path.is_file():
        add("database_path", "fail", "Banco SQLite não encontrado como arquivo regular.")
    else:
        add("database_path", "pass", "Arquivo regular localizado.")

        # Não registrar o conteúdo dos casos no relatório.
        if os.name == "posix":
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                add("file_permissions", "fail",
                    f"Permissões {mode:04o}: grupo ou outros têm acesso ao arquivo.")
            else:
                add("file_permissions", "pass",
                    f"Permissões {mode:04o}: acesso restrito ao proprietário.")

            if path.parent == DEFAULT_DB.parent:
                parent_mode = stat.S_IMODE(path.parent.stat().st_mode)
                if parent_mode & 0o077:
                    add("default_directory_permissions", "fail",
                        "Diretório padrão permite acesso a grupo ou outros.")
                else:
                    add("default_directory_permissions", "pass",
                        "Diretório padrão protegido.")
        else:
            add("file_permissions", "warning",
                "Permissões POSIX não disponíveis neste sistema.")

        try:
            # Abertura somente para leitura: não cria nem atualiza o banco.
            uri = path.resolve().as_uri() + "?mode=ro"
            with sqlite3.connect(uri, uri=True) as db:
                db.execute("PRAGMA query_only = ON")
                check = db.execute("PRAGMA quick_check").fetchone()
                if check is not None and check[0] == "ok":
                    add("sqlite_integrity", "pass", "SQLite quick_check retornou ok.")
                else:
                    add("sqlite_integrity", "fail", "SQLite detectou inconsistências.")

                fk_problems = db.execute("PRAGMA foreign_key_check").fetchone()
                if fk_problems is None:
                    add("foreign_keys", "pass", "Nenhuma referência órfã encontrada.")
                else:
                    add("foreign_keys", "fail", "Há referências órfãs no banco.")

                tables = {
                    row[0] for row in db.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                if {"cases", "evidence"}.issubset(tables):
                    add("schema", "pass", "Tabelas essenciais presentes.")
                else:
                    add("schema", "fail", "Uma ou mais tabelas essenciais estão ausentes.")
        except (sqlite3.Error, OSError, ValueError) as exc:
            add("sqlite_read", "fail",
                f"Não foi possível verificar o banco ({type(exc).__name__}).")

    statuses = [item["status"] for item in findings]
    return {
        "tool": "InstaGuard security audit",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "local_sqlite_only",
        "external_requests": 0,
        "records_or_private_data_included": False,
        "result": "fail" if "fail" in statuses else (
            "warning" if "warning" in statuses else "pass"
        ),
        "findings": findings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Auditoria local de integridade e permissões do InstaGuard, sem rede."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Banco SQLite local")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = audit_database(args.db)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Auditoria InstaGuard: {result['result'].upper()}")
        for entry in result["findings"]:
            print(f"  [{entry['status'].upper()}] {entry['check']}: {entry['detail']}")
    return 1 if result["result"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
