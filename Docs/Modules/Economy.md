# 💰 Sistema de Economia & Mercado Financeiro Fictício

O ecossistema financeiro da SamBot (`sambot/Modules/Economy/`) oferece um jogo econômico interativo no Discord com banco central fictício, mercado simulado de ações e fundos imobiliários (FIIs), minigames de trabalho dinâmicos e sistema de dividendos.

## 🏦 1. Banco, Carteira e Transações

Os dados de saldo e ativos são persistidos pelo `DataManager` na base SQLite:

- **Carteira (`wallet`):** Saldo líquido para uso diário, minigames e pagamentos rápidos.
- **Banco (`bank`):** Saldo protegido contra assaltos e penalidades de minigames, acumulando pequenos rendimentos diários.

### Comandos de Gestão

- `+saldo` (ou `+bal`): Consulta o montante disponível em carteira e no banco.
- `+depositar <valor | all>`: Transfere moedas da carteira para a conta protegida no banco.
- `+sacar <valor | all>`: Resgata valores do banco para uso imediato na carteira.
- `+pix <@usuario> <valor>`: Realiza transferência direta de moedas entre dois membros do servidor.

## 📈 2. Mercado de Ações e FIIs Fictício

O mercado de capitais simula flutuações de preços, permitindo aos membros montar carteiras de investimento em empresas e imóveis fictícios do servidor.

### 2.1. Cotações e Ativos

- Os ativos do mercado dividem-se em **Ações** (maior volatilidade, foco em valorização) e **FIIs** (menor volatilidade, proventos periódicos maiores).
- `+mercado`: Exibe a tabela de cotações vigentes, variações percentuais recentes e preços unitários.
- `+comprar <ticker> <quantidade>`: Adquire a quantidade desejada do ativo com débito em carteira.
- `+vender <ticker> <quantidade>`: Liquida cotas do ativo, creditando o valor da venda com base na cotação atual.

### 2.2. Cálculo de Preço Médio (PM)

Cada aquisição recalcula o Preço Médio ponderado do investidor:

$$\text{PM} = \frac{\sum (\text{Quantidade Comprada} \times \text{Preço de Compra})}{\text{Quantidade Total de Cotas}}$$

O Preço Médio é exibido no comando `+investimentos` para indicar lucro ou prejuízo latente frente à cotação do momento.

### 2.3. Pagamento de Proventos e Dividendos

Durante o ciclo noturno ou em intervalos periódicos, os proprietários de cotas de FIIs recebem proventos automáticos creditados diretamente no saldo bancário, proporcionais ao número de cotas sob custódia.

## 🛠️ 3. Minigames e Rotinas de Trabalho

Os membros podem acumular moedas e experiência (XP) através de atividades periódicas com risco e cooldown:

### 3.1. `+trabalhar` (Profissões Clássicas)

Executa a jornada diária da profissão cadastrada no perfil do usuário, concedendo recompensa estável em moedas e pontos de XP global.

### 3.2. Minigame Hacker (`+hack`)

- **Premissa:** Tentar invadir o mainframe de uma corporação para desviar fundos.
- **Mecânica de Risco:** Probabilidade de sucesso ponderada pelo nível do usuário.
  - **Sucesso:** Recompensa alta em moedas.
  - **Falha:** Bloqueio do terminal com aplicação de multa financeira sobre o saldo da carteira.

### 3.3. Minigame Coleta de Lixo (`+catarlixo`)

- Atividade comunitária de baixo risco para novos usuários coletarem sucata e itens recicláveis em troca de valores imediatos e itens no inventário.
