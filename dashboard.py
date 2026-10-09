#!/usr/bin/env python3
"""Painel web local do InstaGuard (Python stdlib, sem serviços externos).

Acesso apenas via 127.0.0.1, com token CSRF para formulários.
Não acessa Instagram, não automatiza denúncias e não rastreia pessoas.
"""
import argparse
from collections import Counter
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import parse_qs, urlparse

from instaguard import CATEGORIES, DEFAULT_DB, STATUSES, check_url, clean_username, connect, get_case, require_case, timestamp
from report import make_report
from submission import OFFICIAL_HELP_URL, prepare_statement
from scripts.simulate_load import simulate

CSS = """
:root{font-family:Inter,system-ui,Arial,sans-serif;color:#f3f7ff;background:#0b1020}
*{box-sizing:border-box}body{margin:0;min-height:100vh}
.wrap{max-width:1080px;margin:auto;padding:28px 18px 80px}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:26px}
.brand{font-size:25px;font-weight:800;letter-spacing:-.8px}.brand span{color:#69e9d4}
.tag{background:#12293b;border:1px solid #286575;color:#84e7e0;padding:8px 12px;border-radius:50px;font-size:12px}
h1{font-size:clamp(25px,4vw,42px);margin:0 0 8px}h2{font-size:20px;margin:0 0 17px}
p,.muted{color:#a7b2c9}p{line-height:1.5}
.hero{background:linear-gradient(125deg,#192a50,#102b34);padding:28px;border:1px solid #29465e;border-radius:22px;margin-bottom:24px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:24px}
.stat,.panel{border:1px solid #28334c;background:#131b2d;border-radius:18px;padding:20px}
.stat b{display:block;font-size:30px;margin-top:9px}
.grid{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}
.panel{margin-bottom:18px}
label{display:block;color:#c4cee0;font-size:13px;font-weight:650;margin:13px 0 6px}
input,select,textarea{width:100%;border:1px solid #34435e;border-radius:10px;background:#0c1324;padding:12px;color:#fff;font:inherit}
textarea{min-height:86px;resize:vertical}button,.btn{display:inline-block;border:0;border-radius:11px;background:#57dcc3;color:#08201e;padding:11px 16px;font-weight:800;cursor:pointer;text-decoration:none;margin-top:14px}
button:hover,.btn:hover{background:#8cf5e3}.btn.secondary{color:#dce6fa;background:#293653}
.case{border:1px solid #2b3a53;background:#10192b;padding:15px;border-radius:13px;margin:10px 0}
.case a{color:#80ecd8;text-decoration:none;font-weight:700}.case small{color:#9da9c2;display:block;margin-top:6px}
.pill{font-size:11px;color:#b4c7ea;background:#283756;border-radius:20px;padding:3px 9px;margin-left:7px}
.notice{padding:12px 15px;margin:15px 0;border:1px solid #356d64;background:#102d2b;border-radius:12px;color:#b4f8e8}
.error{border-color:#a45160;background:#37202b;color:#ffbdc8}
a{color:#84e7e0}footer{color:#9aa6bd;margin-top:25px;font-size:13px}
@media(max-width:720px){.stats{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}}
"""


def e(value):
    return escape(str(value), quote=True)


def layout(title, body, message="", error=False):
    notification = (
        f'<div class="notice{" error" if error else ""}">{e(message)}</div>'
        if message else ""
    )
    return f"""<!doctype html><html lang="pt-BR"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>{e(title)} | InstaGuard</title>
<style>{CSS}</style></head><body><div class="wrap"><header>
<div class="brand">🛡 Insta<span>Guard</span></div>
<div class="tag">● SISTEMA LOCAL · SEM DENÚNCIAS AUTOMÁTICAS</div></header>
{notification}{body}
<footer>InstaGuard · Dados no dispositivo · Nenhuma conexão com Instagram é realizada pelo painel.</footer>
</div></body></html>""".encode("utf-8")


def select_options(values, current=""):
    return "".join(
        f'<option value="{e(value)}"{" selected" if value == current else ""}>{e(value)}</option>'
        for value in values
    )


def dashboard(db, token, notice=""):
    rows = [dict(row) for row in db.execute(
        "SELECT id,username,category,status,reason,created_at FROM cases ORDER BY id DESC LIMIT 50"
    )]
    counts = Counter(dict(db.execute(
        "SELECT status, COUNT(*) FROM cases GROUP BY status"
    ).fetchall()))
    total = sum(counts.values())
    selectable = [dict(row) for row in db.execute(
        "SELECT id,username FROM cases ORDER BY id DESC"
    )]
    selection = "".join(
        f'<option value="{item["id"]}">@{e(item["username"])} (caso #{item["id"]})</option>'
        for item in selectable
    )
    picker = (
        '<section class="panel"><h2>Selecionar perfil para revisão</h2>'
        '<p>Escolha um caso cadastrado e prepare uma denúncia individual fundamentada. '
        'Nenhum envio é automático.</p>'
        '<form method="get" action="/prepare">'
        '<label for="selected_case">Perfil cadastrado</label>'
        '<select id="selected_case" name="case_id" required>'
        + selection +
        '</select><button type="submit">Preparar denúncia manual</button></form></section>'
    ) if selectable else (
        '<section class="panel"><h2>Selecionar perfil para revisão</h2>'
        '<p>Cadastre um caso com fatos observados antes de selecionar um perfil.</p></section>'
    )
    cards = "".join(
        f'<div class="case"><a href="/case/{item["id"]}">#{item["id"]} · @{e(item["username"])}</a>'
        f'<span class="pill">{e(item["status"])}</span><small>{e(item["category"])} · {e(item["reason"][:130])}</small></div>'
        for item in rows
    ) or '<p>Nenhum caso cadastrado. Comece pelo formulário ao lado.</p>'
    body = f"""<section class="hero"><h1>Central de revisão e evidências</h1>
<p>Organize observações, documente links e exporte relatórios. Tudo fica salvo localmente.</p></section>
<section class="stats">
<div class="stat"><span class="muted">Total de casos</span><b>{total}</b></div>
<div class="stat"><span class="muted">Novos</span><b>{counts["new"]}</b></div>
<div class="stat"><span class="muted">Em revisão</span><b>{counts["reviewing"]}</b></div>
<div class="stat"><span class="muted">Encerrados</span><b>{counts["closed"]}</b></div>
</section><div class="grid"><div>
<section class="panel"><h2>Casos recentes</h2>{cards}</section></div>
<div>{picker}<section class="panel"><h2>+ Novo caso</h2>
<form method="post" action="/cases"><input type="hidden" name="csrf" value="{token}">
<label>Link completo ou @usuário do Instagram</label><input name="username" placeholder="https://www.instagram.com/perfil/" maxlength="255" required>
<label>Categoria</label><select name="category">{select_options(CATEGORIES)}</select>
<label>Motivo observado</label><textarea name="reason" maxlength="2000" required placeholder="Descreva fatos verificáveis, sem acusações não confirmadas"></textarea>
<button type="submit">Cadastrar caso</button></form></section>
<section class="panel"><h2>Laboratório de testes</h2>
<p>Processa 10.000 eventos fictícios na memória, sem atingir contas ou servidores externos.</p>
<form method="post" action="/test"><input type="hidden" name="csrf" value="{token}">
<button type="submit">Executar 10.000 eventos locais</button></form></section>
</div></div>"""
    return layout("Painel", body, notice)


def case_page(db, case_id, token, notice=""):
    case = get_case(db, case_id)
    evidence = "".join(
        f'<div class="case"><a href="{e(ev["url"])}" target="_blank" rel="noopener noreferrer">Abrir evidência ↗</a>'
        f'<small>{e(ev["description"])} · {e(ev["created_at"])}</small></div>'
        for ev in case["evidence"]
    ) or "<p>Nenhuma evidência registrada.</p>"
    body = f"""<p><a href="/">← Voltar ao painel</a></p>
<section class="hero"><h1>@{e(case["username"])}</h1>
<p>Caso #{case["id"]} · {e(case["category"])} · {e(case["status"])}</p>
<a href="https://www.instagram.com/{e(case["username"])}/" target="_blank" rel="noopener noreferrer">Abrir perfil no Instagram ↗</a>
<p>{e(case["reason"])}</p>
<a class="btn secondary" href="/case/{case_id}/report">Baixar relatório Markdown</a>
<a class="btn" href="/case/{case_id}/prepare">Preparar denúncia manual</a></section>
<div class="grid"><div><section class="panel"><h2>Evidências</h2>{evidence}</section></div>
<div><section class="panel"><h2>Adicionar evidência</h2>
<form action="/case/{case_id}/evidence" method="post">
<input type="hidden" name="csrf" value="{token}">
<label>URL HTTPS</label><input name="url" type="url" required placeholder="https://...">
<label>Descrição</label><textarea name="description" maxlength="2000" required></textarea>
<button type="submit">Salvar evidência</button></form></section>
<section class="panel"><h2>Andamento manual</h2>
<form action="/case/{case_id}/status" method="post">
<input type="hidden" name="csrf" value="{token}">
<label>Status do caso</label><select name="status">{select_options(STATUSES,case["status"])}</select>
<button type="submit">Atualizar</button></form>
<p>Marcar “reported” só registra informação inserida por você; não envia denúncia.</p>
</section></div></div>"""
    return layout(f"Caso #{case_id}", body, notice)


def prepare_page(db, case_id):
    case = get_case(db, case_id)
    draft = prepare_statement(case)
    body = f"""<p><a href="/case/{case_id}">← Voltar ao caso</a></p>
<section class="hero"><h1>Preparar solicitação de revisão</h1>
<p>Confira cada alegação e evidência antes de usar este texto. Nenhuma denúncia foi enviada.</p>
<a class="btn secondary" href="{OFFICIAL_HELP_URL}" target="_blank" rel="noopener noreferrer">Abrir Central de Ajuda do Instagram ↗</a></section>
<section class="panel"><h2>Texto preparado</h2>
<label for="draft">Selecione e copie para o canal oficial, caso as informações sejam verdadeiras.</label>
<textarea id="draft" readonly rows="16" style="min-height:320px">{e(draft)}</textarea>
<p>O canal oficial poderá solicitar informações adicionais. Este painel não acessa contas ou serviços externos.</p>
</section>"""
    return layout(f"Preparar caso #{case_id}", body)


def create_handler(db_path, token):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, content_type="text/html; charset=utf-8", filename=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                db = connect(db_path)
                try:
                    if path == "/":
                        self.respond(200, dashboard(db, token))
                        return
                    if path == "/prepare":
                        candidate = parse_qs(urlparse(self.path).query).get("case_id", [""])[0]
                        if not candidate.isascii() or not candidate.isdecimal():
                            raise ValueError("Selecione um caso válido.")
                        self.respond(200, prepare_page(db, int(candidate)))
                        return
                    parts = path.strip("/").split("/")
                    if len(parts) >= 2 and parts[0] == "case" and parts[1].isdigit():
                        cid = int(parts[1])
                        if len(parts) == 2:
                            self.respond(200, case_page(db, cid, token))
                            return
                        if len(parts) == 3 and parts[2] == "prepare":
                            self.respond(200, prepare_page(db, cid))
                            return
                        if len(parts) == 3 and parts[2] == "report":
                            markdown = make_report(get_case(db, cid)).encode("utf-8")
                            self.respond(200, markdown, "text/markdown; charset=utf-8", f"instaguard-caso-{cid}.md")
                            return
                finally:
                    db.close()
                self.respond(404, layout("Não encontrado", "<h1>Página não encontrada</h1>"))
            except ValueError as exc:
                self.respond(404, layout("Caso não encontrado", f"<h1>{e(exc)}</h1>", error=True))

        def do_POST(self):
            size = self.headers.get("Content-Length", "")
            if not size.isdigit() or int(size) > 16_384:
                self.respond(413, layout("Erro", "<h1>Formulário inválido ou muito grande.</h1>"))
                return
            values = parse_qs(self.rfile.read(int(size)).decode("utf-8", errors="replace"))
            def field(name):
                return values.get(name, [""])[0].strip()
            if not secrets.compare_digest(field("csrf"), token):
                self.respond(403, layout("Acesso negado", "<h1>Token inválido.</h1>"))
                return
            path = urlparse(self.path).path
            db = None
            try:
                if path == "/test":
                    result = simulate(10_000)
                    body = "<p><a href='/'>← Voltar</a></p><section class='hero'><h1>Teste concluído</h1><p>10.000 eventos fictícios locais · 0 denúncias reais.</p><pre>" + e(json.dumps(result, indent=2, ensure_ascii=False)) + "</pre></section>"
                    self.respond(200, layout("Teste local", body))
                    return
                db = connect(db_path)
                if path == "/cases":
                    username = clean_username(field("username"))
                    category = field("category")
                    reason = field("reason")
                    if category not in CATEGORIES or not reason or len(reason) > 2000:
                        raise ValueError("Categoria ou motivo inválido.")
                    now = timestamp()
                    db.execute(
                        "INSERT INTO cases(username,category,reason,status,created_at,updated_at) VALUES(?,?,?,'new',?,?)",
                        (username, category, reason, now, now)
                    )
                    db.commit()
                    self.respond(200, dashboard(db, token, "Caso salvo com sucesso."))
                    return
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[0] == "case" and parts[1].isdigit():
                    cid = int(parts[1])
                    require_case(db, cid)
                    if parts[2] == "evidence":
                        url = check_url(field("url"))
                        description = field("description")
                        if not description or len(description) > 2000:
                            raise ValueError("Descrição inválida.")
                        now = timestamp()
                        db.execute(
                            "INSERT INTO evidence(case_id,url,description,created_at) VALUES(?,?,?,?)",
                            (cid, url, description, now)
                        )
                        db.execute("UPDATE cases SET updated_at=? WHERE id=?", (now, cid))
                    elif parts[2] == "status":
                        status = field("status")
                        if status not in STATUSES:
                            raise ValueError("Status inválido.")
                        db.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, timestamp(), cid))
                    else:
                        self.respond(404, layout("Não encontrado", "<h1>Ação não encontrada</h1>"))
                        return
                    db.commit()
                    self.respond(200, case_page(db, cid, token, "Alterações salvas."))
                    return
                self.respond(404, layout("Não encontrado", "<h1>Ação não encontrada</h1>"))
            except ValueError as exc:
                self.respond(400, layout("Erro", "<h1>Não foi possível salvar</h1>", str(exc), True))
            finally:
                if db is not None:
                    db.close()

        def log_message(self, fmt, *args):
            return

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description="InstaGuard dashboard local, sem automação de denúncias.")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        p.error("Porta precisa estar entre 1024 e 65535.")
    secret = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), create_handler(args.db, secret))
    print(f"InstaGuard aberto em http://127.0.0.1:{args.port}/")
    print("Somente no próprio dispositivo. Pressione Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
