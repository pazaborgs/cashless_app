# Cashless App

Sistema de pagamento cashless desenvolvido para otimizar a gestão financeira dos eventos escolares. Cada participante recebe uma ficha física com QR Code que funciona como carteira digital. Créditos são carregados no caixa central e descontados nas barracas.

**Vantagens:**

- Elimina a necessidade de troco nas barracas
- Reduz filas e acelera o atendimento
- Log de auditoria 100% rastreável em tempo real
- Sem instalação de app — tudo via link no navegador

## Tech Stack

| Camada         | Tecnologia                                    |
| -------------- | --------------------------------------------- |
| Interface      | Streamlit (Python)                            |
| Banco de dados | Supabase (PostgreSQL)                         |
| Autenticação   | Magic links via query params + token secreto  |
| Config         | Google Sheets (caixas, vendedores, cardápios) |

## Arquitetura do Projeto

```
cashless_app/
├── src/
│   ├── app.py               # Roteamento principal (query params → view)
│   ├── config_loader.py     # Carrega dados do Google Sheets
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── styling.py       # load_css() — carrega tema por arquivo
│   │   ├── formatting.py    # format_currency(), parse_card_input()
│   │   ├── qr.py            # scan_qr_from_camera()
│   │   └── database.py      # get_supabase() — singleton cacheado
│   ├── views/
│   │   ├── cashier.py       # Módulo caixa (recarga)
│   │   ├── vendor.py        # Módulo vendedor (venda com carrinho)
│   │   └── access_denied.py # Tela de acesso negado
│   └── styles/
│       ├── theme_dark.css   # Tema escuro (padrão atual)
│       └── theme_light.css  # Tema claro (WIP)
├── scripts/
│   ├── generate_cards.py    # Gera pares ID-Token + QR Codes em lote
│   └── test_connection.py   # Valida conexão com Supabase
└── pyproject.toml
```

## Roteamento

O `app.py` roteia pela URL sem menus de navegação:

| URL                                      | View renderizada      |
| ---------------------------------------- | --------------------- |
| `?cashier=Central&token=__tkn_central__` | Módulo caixa          |
| `?vendor=Pastel&token=__tkn_pastel__`    | Módulo vendedor       |
| Qualquer outra                           | Tela de acesso negado |

A autenticação do caixa usa `hmac.compare_digest` para proteção contra timing attacks. A autenticação do vendedor usa comparação direta (risco menor).

## Módulo Caixa

**Acesso:** equipe da tesouraria  
**Função:** receber pagamento e creditar saldo na ficha do participante

Fluxo:

1. Leitura do QR Code por câmera ou entrada manual
2. Exibição do saldo atual da ficha
3. Input do valor de recarga
4. Tela de confirmação com resumo (ficha, valor, saldo antes/depois)
5. Confirmação → insert em `transactions` + update em `cards`

O input do caixa é persistido no `session_state` para sobreviver ao rerun sem perder a ficha carregada.

## Módulo Vendedor

**Acesso:** responsável por cada barraca  
**Função:** registrar vendas debitando o saldo da ficha do cliente

Fluxo:

1. Leitura do QR Code por câmera ou entrada manual
2. Exibição do saldo atual da ficha
3. Seleção de itens no cardápio (multi-seleção com carrinho)
4. Itens com ⚠️ indicam que adicioná-los estouraria o saldo
5. Tela de confirmação com todos os itens, total e saldo após
6. Confirmação → insert em `transactions` + update em `cards`

Durante a confirmação, o cardápio e o carrinho ficam bloqueados — o vendedor só pode confirmar ou cancelar.

Histórico do dia visível em expander `📋 Transações do dia` (renderizado via `st.iframe` para evitar bug de escape de HTML no Streamlit).

## Banco de Dados

### `cards`

| Campo     | Tipo    | Descrição                      |
| --------- | ------- | ------------------------------ |
| `id_card` | VARCHAR | Chave primária (ex: `001`)     |
| `token`   | VARCHAR | Token secreto hexadecimal      |
| `balance` | NUMERIC | Saldo disponível em tempo real |

### `transactions`

| Campo            | Tipo      | Descrição                       |
| ---------------- | --------- | ------------------------------- |
| `id_transaction` | UUID      | PK gerada automaticamente       |
| `created_at`     | TIMESTAMP | Data/hora da transação          |
| `id_card`        | VARCHAR   | FK → cards                      |
| `id_seller`      | VARCHAR   | Nome da barraca ou `Caixa {id}` |
| `operation_type` | VARCHAR   | `RECARGA` ou `VENDA`            |
| `value`          | NUMERIC   | Valor movimentado               |

Modelo append-only — nenhuma transação é editada ou deletada.

## Configuração (Google Sheets)

Três abas no mesmo arquivo:

| Aba          | Colunas                                  | Uso                                 |
| ------------ | ---------------------------------------- | ----------------------------------- |
| `caixas`     | `nome`, `token`                          | Autenticação dos terminais de caixa |
| `vendedores` | `nome`, `token`                          | Autenticação das barracas           |
| `cardapios`  | `vendedor`, `item`, `preco`, `descricao` | Cardápio por barraca                |

Cache de 10 minutos via `@st.cache_data(ttl=600)`.

### URLs (fórmula no Sheets)

**Caixas:**

```
=$E$1&"?cashier="&A2&"&token="&B2
```

**Vendedores:**

```
=$E$1&"?vendor="&A2&"&token="&B2
```

Onde `E1` contém a URL base (ex: `http://localhost:8501` em dev ou a URL de produção).

## Geração de Fichas

O script `scripts/generate_cards.py` gera em lote:

- Pares `ID-Token` com tokens hexadecimais via `secrets`
- QR Codes `.png` com correção de erro `ERROR_CORRECT_H` (30% de redundância — suporta impressão a laser e danos físicos)
- CSV para carga no Supabase

## Hardware (WIP)

Os terminais dos vendedores (tablets) operam apoiados em suportes angulados impressos em 3D (FDM), projetados para otimizar o ângulo da câmera traseira e estabilizar a leitura, deixando as mãos dos operadores livres durante o atendimento.

## TODO

- [ ] Planejar construção dos cartões e material 3D.
- [ ] Subir app para o streamlit.
- [ ] Consertar bugs na view "vendor"
- [ ] Reiniciar cartões e tirar .csv (+ semelhantes) do git repo.
