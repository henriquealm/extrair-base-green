# VTEX Customer Segmentation — Green by Missako

Extrai toda a base de clientes via API VTEX (Master Data + OMS) e gera uma planilha segmentada por gênero de produto comprado.

## Estrutura

```
├── main.py          # Orquestrador principal
├── classifier.py    # Lógica de classificação por categoria
├── exporter.py      # Geração do .xlsx formatado
├── requirements.txt
├── .env.example     # Template de credenciais
└── output/          # Gerado automaticamente
```

## Setup no GitHub Codespaces

### 1. Criar o arquivo `.env`
```bash
cp .env.example .env
```
Edite o `.env` com suas credenciais reais:
- `VTEX_ACCOUNT`: nome da conta (ex: `greenbyMissako`)
- `VTEX_APP_KEY` e `VTEX_APP_TOKEN`: gerados em **Configurações da Conta → Gerenciamento de Conta → Chaves e Tokens**

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Executar
```bash
python main.py
```

O arquivo `output/segmentacao_missako.xlsx` será gerado com as seguintes abas:

| Aba | Conteúdo |
|-----|----------|
| 📊 Resumo | Totais e percentuais por segmento |
| 🔵 Somente Meninos | Clientes que compraram só produtos masculinos |
| 🩷 Somente Meninas | Clientes que compraram só produtos femininos |
| 💜 Meninos e Meninas | Clientes que compraram para ambos |
| ⚪ Categorias Neutras | Compraram categorias sem gênero definido |
| ❌ Sem Compra | Cadastros sem nenhum pedido registrado |
| 📦 Todos com Compra | União de todos os compradores |

## Como a classificação funciona

O script combina **duas fontes**:

1. **Master Data CL** — campo `categoryPurchasedTag` (quando preenchido)
2. **OMS** — pedidos reais do cliente (para quem tem tag `null`)

As categorias são classificadas em `classifier.py`. Ajuste as listas `BOY_CATEGORIES`, `GIRL_CATEGORIES` e `NEUTRAL_CATEGORIES` conforme a árvore de categorias real da loja.

## Permissões necessárias na App Key

| Recurso | Permissão |
|---------|-----------|
| Master Data | `Read only` |
| OMS | `Read only` |

## Observações

- O endpoint `/scroll` do Master Data não tem limite de registros
- O script respeita o rate limit da VTEX com `time.sleep` entre as chamadas
- Credenciais nunca são commitadas (`.env` está no `.gitignore`)
