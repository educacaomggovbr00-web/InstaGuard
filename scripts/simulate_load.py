#!/usr/bin/env python3
"""Teste de carga 100% local de registros fictícios.

Gera eventos artificiais em memória. Não contém endpoints, autenticação,
usuários reais, chamadas HTTP ou envio de denúncias a plataformas.
"""
import argparse
from collections import Counter
import json
from time import perf_counter


def simulate(amount=10_000):
    if not isinstance(amount, int) or amount < 1 or amount > 100_000:
        raise ValueError("Escolha entre 1 e 100000 eventos fictícios.")

    started = perf_counter()
    counts = Counter()
    # Nenhuma rede e nenhum nome de perfil: eventos inteiramente sintéticos.
    for event_id in range(amount):
        fake_event = {
            "id": event_id,
            "target": f"test_account_{event_id % 50:02d}",
            "kind": "simulated_report",
            "result": "local_only",
        }
        if fake_event["result"] != "local_only":
            raise AssertionError("Evento inesperado fora do ambiente local")
        counts[fake_event["result"]] += 1

    result = {
        "mode": "offline_simulation",
        "requested": amount,
        "processed_locally": counts["local_only"],
        "real_reports_sent": 0,
        "duration_seconds": round(perf_counter() - started, 4),
        "passed": counts["local_only"] == amount,
    }
    return result


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Simula carga em memória sem contato com Instagram ou qualquer API."
    )
    p.add_argument("--count", type=int, default=10_000)
    args = p.parse_args(argv)
    try:
        result = simulate(args.count)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
