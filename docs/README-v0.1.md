# InstaGuard 🛡️

Ferramenta **local** de organização de investigações e denúncias legítimas de possíveis violações no Instagram. Projeto pessoal, em Python 3, compatível com Termux (Android) e Linux.

> **Importante:** o InstaGuard **não** acessa o Instagram, não visualiza conteúdo privado, não automatiza denúncias, não tenta bloquear perfis e não garante remoções. O usuário avalia as evidências e decide se há motivo para usar os canais oficiais do Instagram. Uma conta privada pode ser cadastrada pelo nome de usuário, mas o aplicativo não revela seus conteúdos.

## Instalação no Termux

```bash
pkg update
pkg install python git
git clone https://github.com/educacaomggovbr00-web/InstaGuard.git
cd InstaGuard
python instaguard.py --help
```

**Observação:** este repositório é privado. Para `git clone`, você precisa estar autenticado no GitHub com acesso ao repositório. A versão inicial pode estar na branch `feat/initial-case-manager` até que seja integrada à `main`. Nesse caso, use `git switch feat/initial-case-manager` após clonar.

Não há dependências externas de Python.

## Comandos

```bash
# Criar um caso a partir de observações suas
python instaguard.py add @perfil.exemplo --category impersonation --reason "Possível uso indevido de identidade"

# Registrar um endereço HTTPS que você tem permissão para consultar
python instaguard.py evidence 1 --url "https://www.instagram.com/perfil.exemplo/" --description "URL do perfil para verificação humana"

# Consultar casos e evidências
python instaguard.py list
python instaguard.py show 1
python instaguard.py stats

# Atualizar o andamento manualmente
python instaguard.py status 1 reviewing
python instaguard.py status 1 reported
python instaguard.py status 1 closed

# Exportar o material localmente
python instaguard.py export --output relatorio.json
```

Categorias: `impersonation`, `scam`, `spam`, `other`. Estados: `new`, `reviewing`, `reported`, `closed`. Marcar como `reported` **não envia** nenhuma denúncia; apenas registra um andamento informado pelo usuário.

Para mais comandos: `python instaguard.py --help`.

## Dados e privacidade

- Os casos e evidências ficam **no dispositivo**, no banco SQLite `~/.instaguard/cases.db`; não são enviados a servidores.
- O projeto tenta restringir as permissões do banco e do diretório em sistemas compatíveis. Não há criptografia: proteja o aparelho e seus backups.
- Um relatório JSON exportado pode conter dados pessoais. Compartilhe somente quando necessário e com autorização.
- Registre apenas informações que você obteve legitimamente. Não publique acusações sem verificá-las.
- Para denunciar violações reais, use os recursos oficiais do Instagram e forneça evidências precisas, evitando denúncias duplicadas ou coordenadas.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Licença

Nenhuma licença de código aberto foi concedida. Todos os direitos reservados por padrão.

## Investigador de dados públicos (experimental)

O investigador analisa **apenas informações fornecidas manualmente**. Não busca perfis, não consulta APIs do Instagram e não identifica o verdadeiro criador de uma conta.

```bash
python investigator.py @perfil.exemplo --display-name "Nome visível" --bio "Texto público da biografia" --source "https://www.instagram.com/perfil.exemplo/"
```

A saída JSON inclui os dados registrados, links no texto e algumas expressões que merecem revisão humana (ex.: promessas financeiras). Nenhum sinal é prova de fraude e a análise não provoca denúncias ou bloqueios. Evite incluir dados pessoais que não estejam disponíveis legitimamente.

## Relatório de um caso — sem internet

Após cadastrar um caso e registrar suas evidências, o gerador cria um documento Markdown com o andamento, dados públicos digitados por você, sinais textuais para revisão e a relação das evidências:

```bash
# Ver os IDs já cadastrados
python instaguard.py list

# Mostrar relatório no terminal (substitua 1 pelo ID do seu caso)
python report.py 1

# Adicionar dados públicos visíveis informados manualmente e salvar um arquivo novo
python report.py 1 --display-name "Nome exibido" --bio "Texto público visível" --source "https://www.instagram.com/perfil.exemplo/" --output relatorio-caso-1.md

# Executar testes automatizados
python -m unittest discover -s tests -v
```

O relatório **não acessa redes sociais**, não investiga a identidade privada do proprietário, não atribui culpabilidade, não envia denúncias e não certifica a veracidade das informações inseridas. A identidade de quem criou ou administra o perfil é registrada como **não determinada**. O comando se recusa a sobrescrever um relatório existente e protege os arquivos de saída, quando o sistema suporta permissões Unix.

## Relatório estruturado JSON (teste de software)

A análise de casos pode ser exportada também como JSON, com campos que indicam explicitamente as limitações e o nível de verificação. **Não é necessário usar a internet para executar o comando.**

```bash
python report.py 1 --format json --output revisao-caso-1.json
```

O JSON traz `identity_of_profile_creator.status: unknown`, `conclusion: inconclusive` e `public_fields_supplied_manually.independently_verified: false`. Mesmo quando o operador informa um nome de exibição, isso **não comprova o nome real de quem criou a conta**. Não há invasão, contorno de privacidade, busca de identidade oculta nem envio de denúncias.

## Auditoria de segurança do próprio InstaGuard

A auditoria é **local e defensiva**: verifica o arquivo SQLite do programa, sem acessar o Instagram nem consultar perfis de terceiros.

```bash
# Confira casos cadastrados, se necessário
python instaguard.py list

# Execute uma auditoria do banco padrão (~/.instaguard/cases.db)
python security_audit.py

# Obtenha a auditoria em JSON para registrar um teste de software
python security_audit.py --format json > auditoria-instaguard.json

# Caso use um banco diferente:
python security_audit.py --db ./meus-casos.db --format json

# Testes automatizados (também executados no GitHub Actions)
python -m unittest discover -s tests -v
```

Os resultados verificam **integridade do banco SQLite**, referências órfãs, presença das tabelas essenciais e permissões de leitura por terceiros (em sistemas Unix/Termux). A auditoria é somente leitura, não imprime os casos, não altera arquivos e relata falhas sem fornecer dados pessoais. Um banco ainda não criado será informado como inexistente.

**Proteção dos arquivos:** as exportações JSON de `instaguard.py export` e os relatórios de `report.py` são criados com permissões de acesso restrito nos sistemas compatíveis e não sobrescrevem arquivos existentes. A ferramenta não certifica segurança de serviços externos, não detecta todas as vulnerabilidades e não revela identidades privadas.
