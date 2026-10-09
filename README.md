# InstaGuard 🛡️

Ferramenta em Python para cadastrar perfis suspeitos, organizar evidências, gerar relatórios locais e acompanhar casos de possíveis violações no Instagram, sem automação de denúncias.

📖 **[Instalação no Termux, comandos e cuidados de privacidade](docs/README-v0.1.md)**

A versão 0.1 está em desenvolvimento. Código e testes disponíveis nesta branch.

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
