"""Prepara uma declaração factual para avaliação humana.

Nenhuma comunicação com o Instagram ou envio automático acontece aqui.
"""
from instaguard import check_url

OFFICIAL_HELP_URL = "https://help.instagram.com/"


def prepare_statement(case):
    """Gera rascunho neutro usando apenas informações já cadastradas."""
    username = case["username"]
    reason = case["reason"].strip()
    if not reason:
        raise ValueError("Descreva os fatos observados antes de preparar uma denúncia.")
    evidence = case.get("evidence", [])
    lines = [
        "SOLICITAÇÃO DE REVISÃO — RASCUNHO PARA ENVIO MANUAL",
        "",
        f"Perfil observado: https://www.instagram.com/{username}/",
        f"Categoria informada: {case['category']}",
        "",
        "Fatos informados pelo solicitante:",
        reason,
        "",
        "Fontes e evidências informadas:",
    ]
    if evidence:
        for idx, item in enumerate(evidence, 1):
            url = check_url(item["url"])
            lines.append(f"{idx}. {url} — {item['description'].strip()}")
    else:
        lines.append("Nenhuma evidência foi cadastrada.")
    lines.extend([
        "",
        "Peço uma revisão humana, se esses fatos forem relevantes às regras da plataforma.",
        "Não posso afirmar que exista violação ou que o perfil seja falso sem confirmação.",
        "",
        "Este texto é apenas um rascunho. Revise a precisão dos fatos antes de usá-lo.",
        "O InstaGuard não enviou nenhuma denúncia.",
    ])
    return "\n".join(lines)
