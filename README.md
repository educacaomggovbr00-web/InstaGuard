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
