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
