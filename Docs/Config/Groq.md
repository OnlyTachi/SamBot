# Guia de Configuração da API do Groq

## Estratégias de Posicionamento de Modelos no Pipeline Multi-Camadas da SamBot

Este documento serve como guia técnico complementar para a integração da **Camada 1.5 (Failover de Nuvem de Alta Velocidade)** na SamBot. A infraestrutura do Groq permite inferências com latências extremamente baixas, ideal para cenários de transição transparente quando a nuvem principal sofre gargalos ou bloqueios por taxa de requisições (_Rate Limits_).

---

### 1. Como Obter a Chave de API do Groq

Para integrar a Camada 1.5 ao ecossistema da SamBot, é necessário obter as credenciais de autenticação diretamente na plataforma de desenvolvedores do Groq:

1. Acesse o console oficial para desenvolvedores em [console.groq.com](https://console.groq.com/).
2. Efetue o cadastro ou realize login utilizando sua conta existente.
3. No menu lateral esquerdo, navegue até a seção **API Keys**.
4. Clique no botão **Create API Key**.
5. Atribua um nome identificável para a sua chave (ex: `SamBot_Production`) e confirme.

> ⚠️ **Importante:** Copie o token gerado imediatamente. Por motivos de segurança, a chave não será exibida novamente após fechar a janela de criação.

---

### 2. Injeção de Variáveis no Ambiente (.env)

Abra o arquivo de configuração global `.env` localizado na raiz do projeto SamBot e adicione as seguintes definições de variáveis para expor as credenciais ao provedor interno:

```env
# Configurações da Camada 1.5 (Groq Failover)
GROQ_API_KEY=gsk_vA123B456C789dEfG...
GROQ_MODEL=llama-3.1-8b-instant

```

---

### 3. Recomendações de Uso e Posicionamento dos Modelos

Abaixo encontra-se a matriz de posicionamento sugerida para os modelos disponíveis na API do Groq, categorizada de acordo com o papel desempenhado dentro da arquitetura em camadas do bot:

| Modelo Groq                 | Papel Recomendado         | Contexto Máximo | Justificativa Técnica                                                                                                             |
| --------------------------- | ------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **llama-3.3-70b-versatile** | Principal / Auxiliar Alto | 128k tokens     | Raciocínio complexo de alta precisão. Excelente para orquestração fina de ferramentas. Substitui o Gemini Pro se necessário.      |
| **llama-3.1-8b-instant**    | Auxiliar / Reserva Ativa  | 128k tokens     | Equilíbrio ideal entre velocidade extrema e custos de processamento. Perfeito para responder rapidamente a comandos estruturados. |
| **gemma2-9b-it**            | Reserva Local / Nuvem     | 8k tokens       | Modelo focado em conversação fluida e natural, com excelentes respostas na língua portuguesa. Ótimo backup direto.                |
| **mixtral-8x7b-instruct**   | Auxiliar de Código        | 32k tokens      | Arquitetura _Mixture of Experts_ (MoE). Recomendado para tarefas específicas de desenvolvimento de software e análise lógica.     |

#### Estratégia de Arquitetura no SamBot:

Devido ao limite padrão estrito de **250 Requisições por Dia (RPD)** imposto no nível gratuito da API do Groq, o posicionamento nativo recomendado deste ecossistema é o de **Auxiliar de Failover Rápido (Camada 1.5)**.

Desta forma, ele intercepta unicamente os erros `HTTP 429` gerados pelo Gemini Cloud (Camada 1), garantindo a continuidade do serviço sem sobrecarregar as cotas diárias de uso.

---

### 4. Arquitetura de Fluxo Sugerida para Customização

Se o usuário optar por alterar a ordem padrão das camadas via código, a lógica de contingência deve seguir este comportamento lógico:

- **Groq como Principal (Camada 1):** Recomendado apenas se o volume de uso do servidor for inferior a 250 mensagens diárias e o foco for latência próxima a zero. Configurar com o modelo `llama-3.3-70b-versatile`.
- **Groq como Auxiliar/Reserva (Camada 1.5):** Configuração padrão. Atua como escudo protetor contra quedas de cota do Gemini. Configurar com o modelo `llama-3.1-8b-instant` para respostas imediatas.
