# Como Configurar Navidrome (Subsonic API)

Para pegar o link do Subsonic no seu **Navidrome**, você não precisa procurar uma URL escondida na interface web. O Navidrome expõe a API compatível com o Subsonic nativamente em uma rota padrão.

O formato base da URL do Subsonic que você deve colocar no seu arquivo `.env` (na variável `NAVIDROME_URL`) é exatamente o **endereço IP (ou domínio) e a porta** que você usa para acessar o seu Navidrome pelo navegador.

### 1. Estrutura da URL

O endpoint padrão para qualquer aplicativo ou script que se conecta à API Subsonic do Navidrome é:

```text
http://IP_DO_SEU_SERVIDOR:4533

```

_(Se você configurou um domínio com SSL/HTTPS, use `https://seu-dominio.com`)_.

---

### 2. Como validar se a sua URL está certa

Você pode testar se o endpoint do Subsonic está ativo e respondendo diretamente pelo seu navegador.

1. Copie e cole a seguinte URL no seu navegador (substituindo com os seus dados de acesso):

```text
http://IP_DO_SEU_SERVIDOR:4533/rest/ping.view?u=SEU_USUARIO&p=SUA_SENHA&v=1.16.1&c=teste&f=json

```

2. Se o link estiver correto e o Navidrome estiver alcançável, o navegador vai baixar ou exibir um arquivo JSON parecido com este:

```json
{
  "subsonic-response": {
    "status": "ok",
    "version": "1.16.1"
  }
}
```

---

### 3. Preenchendo no `.env` da SamBot

Sabendo disso, no arquivo `.env` do seu bot, você só precisa passar a **URL base** (sem o `/rest/...`), pois o seu `SearchManager` já está programado para completar o resto do caminho sozinho:

```env
# Configuração do Modo de Busca: HIBRIDO | LOCAL | ONLINE
MUSIC_SOURCE_MODE=HIBRIDO

# Credenciais da API do Navidrome (Subsonic API)
NAVIDROME_URL=http://192.168.1.100:4533
NAVIDROME_USER=seu_usuario_aqui
NAVIDROME_PASSWORD=sua_senha_aqui

```

> ⚠️ **Nota Importante:** Certifique-se de que o usuário utilizado no `.env` tenha a opção **"Allow Subsonic access"** (Permitir acesso Subsonic) marcada nas configurações de usuário dentro do painel administrativo do Navidrome, caso contrário as requisições do bot receberão um erro de autenticação.
