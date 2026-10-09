#!/usr/bin/env python3
"""Gera relatórios locais a partir de casos salvos no InstaGuard.

Sem conexão com Instagram, busca de pessoas, automação de denúncias ou
inferência da identidade de quem opera um perfil.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import sqlite3

from evidence import verify_evidence

from instaguard import DEFAULT_DB, connect, get_case, timestamp
from investigator import assess


def safe_text(value):
    """Escapa conteúdo informado pelo usuário para evitar Markdown enganoso."""
    value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"([\\\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value).replace("\n", "  \n")


def inline_code(value):
    """Texto seguro em marcação inline sem alterar endereços URL."""
    return str(value).replace("`", "").replace("\r", " ").replace("\n", " ")


def make_report(case, display_name="", bio="", source_url=""):
    info = assess(
        case["username"],
        display_name=display_name,
        bio=bio,
        source_url=source_url,
    )
    mark = safe_text
    code = inline_code
    lines = [
        "# InstaGuard — relatório de revisão de perfil",
        "",
        f"**Caso:** #{case['id']}",
        f"**Gerado em (UTC):** {timestamp()}",
        "**Método:** informações fornecidas manualmente; sem consulta ao Instagram.",
        "",
        "## Perfil informado",
        "",
        f"- Usuário: `@{mark(info['username'])}`",
        f"- Link do perfil: `{code(info['profile_url'])}`",
        f"- Nome de exibição informado (não verificado): {mark(display_name) if display_name else 'Não informado'}",
        "- **Identidade de quem criou ou administra o perfil: não determinada.**",
        f"- Categoria cadastrada: {mark(case['category'])}",
        f"- Andamento do caso: {mark(case['status'])}",
        f"- Fonte informada: `{code(source_url)}`" if source_url else "- Fonte informada: nenhuma",
        "",
        "## Alegação registrada pelo operador",
        "",
        mark(case["reason"]),
        "",
        "## Biografia pública informada manualmente",
        "",
        mark(bio) if bio else "Não informada.",
        "",
        "## Indicadores para revisão humana",
        "",
    ]
    indicators = info["review_indicators"]
    if indicators:
        for indicator in indicators:
            lines.append(
                f"- {mark(indicator['indicator'])}: trecho `{code(indicator['excerpt'])}`"
            )
    else:
        lines.append("Nenhum indicador textual encontrado nos dados fornecidos.")
    lines.extend(["", "## Evidências cadastradas", ""])
    if case["evidence"]:
        for index, evidence in enumerate(case["evidence"], 1):
            lines.append(
                f"{index}. `{code(evidence['url'])}` — {mark(evidence['description'])}"
            )
    else:
        lines.append("Nenhuma evidência cadastrada.")
    lines.extend([
        "", "## Verificação e procedência", "",
        "Fatos confirmados abaixo dizem respeito somente aos arquivos locais; hashes não comprovam autoria ou veracidade.",
        f"Consistência da fonte: {mark(info['provenance']['source_consistency'])}",
    ])
    structured = make_json_report(case, display_name, bio, source_url)
    for heading, key in (("Fatos confirmados", "confirmed_facts"),
                         ("Informações não verificadas", "unverified_information"),
                         ("Resultados inconclusivos", "inconclusive_results")):
        lines.extend(["", "### " + heading, ""])
        lines.extend("- " + mark(json.dumps(item, ensure_ascii=False)) for item in structured[key])
        if not structured[key]:
            lines.append("Nenhum.")
    lines.extend([
        "",
        "## Conclusão",
        "",
        "Inconclusivo: o cadastro e os indicadores textuais, isoladamente, não",
        "comprovam que o perfil seja falso, que violou regras ou quem o criou.",
        "O conteúdo informado precisa de conferência humana com acesso legítimo.",
        "Este documento não realiza denúncia nem solicita banimento de contas.",
        "",
    ])
    return "\n".join(lines)


def make_json_report(case, display_name="", bio="", source_url=""):
    """Structured offline review, with explicit uncertainty and source attribution."""
    info = assess(
        case["username"], display_name=display_name, bio=bio, source_url=source_url
    )
    checks = [verify_evidence(item) for item in case["evidence"]]
    confirmed = [check for check in checks if check["status"] == "verified_bytes"]
    inconclusive = [check for check in checks if check["status"] in ("mismatch", "unavailable")]
    inconclusive.append({"subject": "profile_authorship_and_violation", "status": "not_established"})
    return {
        "schema_version": 2,
        "generated_at_utc": timestamp(),
        "mode": "offline_manual_review",
        "case": {
            "id": case["id"],
            "username": case["username"],
            "category": case["category"],
            "status": case["status"],
            "reason_claimed_by_operator": case["reason"],
        },
        "public_fields_supplied_manually": {
            "display_name": display_name or None,
            "bio": bio or None,
            "source_url": source_url or None,
            "independently_verified": False,
        },
        "review_indicators": info["review_indicators"],
        "evidence_supplied_by_operator": case["evidence"],
        "provenance": info["provenance"],
        "integrity_checks": checks,
        "confirmed_facts": confirmed,
        "unverified_information": [
            {"subject": "operator_reason", "value": case["reason"]},
            {"subject": "public_fields", "display_name": display_name, "bio": bio},
            *[{"subject": "evidence_content", "evidence_id": item.get("id"),
               "url": item["url"], "description": item["description"]} for item in case["evidence"]],
        ],
        "inconclusive_results": inconclusive,
        "timeline": sorted([
            {"event": "evidence_registered", "evidence_id": item.get("id"), "at_utc": item["created_at"]}
            for item in case["evidence"] if item.get("created_at")
        ] + [
            {"event": "observation_claimed_by_operator", "evidence_id": item.get("id"), "at_utc": item["observed_at"]}
            for item in case["evidence"] if item.get("observed_at")
        ], key=lambda item: item["at_utc"]),
        "identity_of_profile_creator": {
            "status": "unknown",
            "note": "Nome de exibição não identifica quem criou ou controla uma conta."
        },
        "conclusion": "inconclusive",
        "limitations": [
            "Nenhuma verificação de Instagram ou serviço externo foi realizada.",
            "Informações fornecidas manualmente não comprovam fraude ou autoria.",
            "Nenhuma denúncia ou restrição de conta é executada.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Gera relatório Markdown de um caso salvo, sem acesso à internet."
    )
    p.add_argument("case_id", type=int, help="ID do caso, visto em 'instaguard.py list'")
    p.add_argument("--db", default=str(DEFAULT_DB), help="Caminho do banco SQLite")
    p.add_argument("--display-name", default="", help="Nome público fornecido manualmente")
    p.add_argument("--bio", default="", help="Biografia pública fornecida manualmente")
    p.add_argument("--source", default="", help="URL HTTPS de origem das informações")
    p.add_argument("--format", choices=("md", "json"), default="md", help="Formato do relatório")
    p.add_argument("--output", help="Salvar em arquivo novo; sem --output, imprime na tela")
    args = p.parse_args(argv)

    try:
        db = connect(args.db)
        try:
            case = get_case(db, args.case_id)
        finally:
            db.close()
        if args.format == "json":
            report = json.dumps(
                make_json_report(case, args.display_name, args.bio, args.source),
                ensure_ascii=False, indent=2
            ) + "\n"
        else:
            report = make_report(case, args.display_name, args.bio, args.source)
        if args.output:
            destination = Path(args.output).expanduser()
            if destination.resolve() == Path(args.db).expanduser().resolve():
                raise ValueError("Relatório não pode sobrescrever o banco SQLite.")
            # A escrita nasce com permissões privadas e nunca substitui arquivo existente.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            with os.fdopen(
                os.open(destination, flags, 0o600), "w", encoding="utf-8"
            ) as output:
                output.write(report)
            print(f"Relatório salvo em: {destination}")
        else:
            print(report)
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

