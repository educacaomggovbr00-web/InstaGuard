# Implementação e validação — InstaGuard

Base analisada integralmente: `e06213b8b354a1a46cd7130123a8e901f3535460`, branch
`feat/initial-case-manager`. A `main` continha apenas o README inicial.

## Problemas encontrados e alterações

- Evidências eram apenas links e descrições. Novo módulo `evidence.py` preserva
  arquivos legitimamente fornecidos, limita cada arquivo a 25 MiB, calcula SHA-256,
  guarda tamanho, data da observação com fuso, data de registro UTC e operador.
- Bancos antigos são migrados sem apagar casos ou links; dados de procedência ausentes
  continuam desconhecidos. A migração usa uma transação de escrita serializada.
- Relatórios Markdown/JSON verificam as cópias locais e distinguem `verified_bytes`,
  `mismatch`, `unavailable` e `unverified`. Alegações e conteúdo continuam não
  verificados, mesmo quando o hash corresponde. JSON inclui linha do tempo.
- O investigador aponta fonte ausente, perfil correspondente, perfil divergente,
  endereço que não é perfil e fonte externa, sem afirmar autenticidade.
- O painel valida Host e Origin para reduzir exposição a DNS rebinding e requisições
  de outras origens; mantém CSRF, escape HTML, CSP e cache desativado. Agora oferece JSON.
- URLs com credenciais, caracteres de controle, barras invertidas ou portas inválidas
  são recusadas. Rotas reservadas do Instagram não viram nomes de perfil.
- Banco novo nasce com modo 0600; links simbólicos de banco e arquivos são recusados.
  Pacotes manuais nascem em diretório novo 0700 e arquivos 0600, sem sobrescrita.
- Auditoria somente leitura confere colunas essenciais, categorias, estados, URLs,
  integridade SQLite, referências, permissões do banco e hashes de cópias locais.
  Seu resultado não imprime nomes, alegações ou conteúdo das evidências.
- Dois arquivos removidos de `.github/workflows/` (`Insta.yml` e
  `instagram_mass_report.yaml`) eram configurações duplicadas de denúncias em massa,
  sem `on`/`jobs` e com estrutura YAML inválida. Não implementavam um serviço funcional.
  Permanecem recuperáveis no histórico Git. Os workflows de revisão manual e testes
  foram preservados; testes usam permissões de leitura e Python 3.10/3.12/3.13.

## Validação local executada

```bash
python -m unittest discover -s tests -v
python scripts/smoke_evidence.py
python scripts/simulate_load.py --count 10000
python -m compileall -q instaguard.py evidence.py investigator.py report.py dashboard.py security_audit.py submission.py scripts tests
```

50 testes passam em Python 3.12: 33 existentes e 17 novos. Cobertura nova inclui
migração legada repetida, preservação de cópia após exclusão da fonte, alteração e
ausência de arquivo, permissões, limpeza de cópias incompletas, fuso/data futura,
fontes divergentes, escape de HTML, auditoria de estrutura e valores inválidos,
CSRF/Host/Origin, limite HTTP e download JSON.

O executor local proíbe sockets. Os três testes HTTP usam o parser HTTP e o handler
reais com fluxos em memória nesse ambiente. No GitHub Actions, onde sockets locais
são permitidos, os mesmos testes iniciam um servidor em `127.0.0.1` numa porta efêmera.
A matriz no CI valida as outras versões Python; não foi executado Android/Termux real.

O smoke test executa a CLI em subprocessos com banco temporário e arquivo fictício,
produz Markdown e JSON e confirma auditoria `pass`. A simulação processa 10.000
eventos exclusivamente na memória, com `real_reports_sent: 0`.

## Limitações

Nenhuma informação de `@melancoolics` foi coletada ou verificada. Não há evidência
fornecida pelo solicitante que comprove uso de imagem, violação ou identidade.
Nenhuma denúncia foi enviada. O projeto organiza material legitimamente fornecido
para revisão humana; não consulta o Instagram nem infere quem controla uma conta.

Hashes comprovam correspondência de bytes ao registro local, não autenticidade,
autoria ou cadeia de custódia imutável. Quem pode modificar banco e arquivos pode
substituir ambos. Não há criptografia nem assinatura externa. Backups devem manter
o banco e `evidence-files/` juntos; JSON não embute os arquivos. Arquivos locais são
anexados pela CLI, sem upload no painel. A auditoria não é uma certificação completa
de segurança. Não foram usados scanners ou serviços externos de análise.

Resultados do GitHub Actions devem ser conferidos na execução vinculada ao commit;
o resultado local acima não substitui o estado remoto.
