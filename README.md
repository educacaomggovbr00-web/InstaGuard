# InstaGuard 🛡️

Ferramenta em Python para cadastrar perfis suspeitos, organizar evidências, gerar relatórios locais e acompanhar casos de possíveis violações no Instagram, sem automação de denúncias.

📖 **[Instalação no Termux, comandos e cuidados de privacidade](docs/README-v0.1.md)**

A versão 0.1 está em desenvolvimento. Código e testes disponíveis nesta branch.

## Evidências preservadas e relatórios verificáveis

Registre uma captura ou documento que você obteve legitimamente. O programa copia os
bytes para `evidence-files/`, ao lado do banco, com permissões privadas e calcula SHA-256:

```bash
python instaguard.py evidence 1 --url "https://www.instagram.com/perfil.exemplo/" --description "Captura fornecida por mim" --file ./captura.png --observed-at "2026-10-09T10:00:00Z" --collector "operador"
python report.py 1 --format md --output caso-1.md
python report.py 1 --format json --output caso-1.json
python security_audit.py --format json
```

Os relatórios separam fatos confirmados sobre os bytes locais, informações não
verificadas e resultados inconclusivos. Alteração ou ausência de uma cópia é detectada
na geração do relatório. SHA-256 não comprova autoria, identidade ou veracidade da
imagem. O investigador também indica fontes ausentes, divergentes ou de outro site.
No painel há downloads em Markdown e JSON; arquivos locais são anexados pela CLI.

Limite por arquivo: 25 MiB. A data deve ter fuso horário e não pode ser futura.
Evidências antigas por URL continuam disponíveis após migração automática do banco.
Faça backup conjunto do banco e de `evidence-files/`; exportar JSON não inclui os
arquivos binários. Os dados não são criptografados.

Veja o [relatório de implementação e validação](docs/VALIDATION.md).

## Teste artificial de carga (10.000 eventos)

O GitHub Actions executa uma simulação local com 10.000 eventos fictícios, **sem enviar denúncias reais**. Para executar no Termux:

```bash
python scripts/simulate_load.py --count 10000
```

O JSON de saída mostra `processed_locally: 10000`, `real_reports_sent: 0` e `passed: true` quando a simulação termina com sucesso. O teste não mede capacidade de envio ao Instagram: apenas exercita a criação e a contagem de eventos artificiais em memória.

## Painel web local (Android/Termux ou PC)

Agora o InstaGuard tem uma interface escura, responsiva e sem dependências extras de Python.

```bash
python dashboard.py
```

Abra **http://127.0.0.1:8765/** no navegador **do mesmo dispositivo**. Você pode cadastrar casos, adicionar evidências por URL, acompanhar status manualmente, baixar um relatório Markdown e executar o teste de 10.000 eventos **fictícios**. Use `Ctrl+C` para encerrar.

O servidor só escuta em `127.0.0.1`; ele não expõe uma interface pública, não consulta Instagram e não envia denúncias. Os dados ficam em `~/.instaguard/cases.db`. Não use o painel com dados de pessoas obtidos de forma indevida.

## Preparação de denúncia manual

Abra um caso no painel e escolha **Preparar denúncia manual**. O programa cria um rascunho a partir do motivo e das evidências previamente fornecidos por você. Revise todas as afirmações antes de copiar o texto para um canal oficial. O botão **Abrir Central de Ajuda do Instagram** leva à página oficial de ajuda; isso não garante um formulário específico nem envia nada automaticamente.

Nenhum disparo de denúncias em massa, uso de contas automáticas ou envio para perfis é implementado.

## Cadastro por link completo

No painel, o campo **Link completo ou @usuário do Instagram** aceita, por exemplo, `https://www.instagram.com/perfil/` ou `@perfil`. O InstaGuard reconhece apenas URLs HTTPS de perfil no domínio Instagram e rejeita links de posts ou sites externos. O perfil pode ser aberto no Instagram para avaliação humana.

**Online não significa envio automatizado:** o cadastro e a preparação ocorrem no dispositivo, e a denúncia oficial deve ser feita manualmente no Instagram. Este projeto não está hospedado em um servidor público.

