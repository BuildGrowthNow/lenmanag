# Cloudflare Workers AI setup

The backend now uses Cloudflare Workers AI when `LLM_PROVIDER=cloudflare`.

## 1. Create the API token

1. Open the Cloudflare Dashboard and select **Workers AI**.
2. Select **Use REST API**.
3. Select **Create a Workers AI API Token**.
4. Copy the token immediately. Do not paste it into Git, chat, or source code.

The token must have the account permission **Workers AI - Read**. Cloudflare's REST API guide notes that a custom token may need both **Workers AI - Read** and **Workers AI - Edit**; use the dashboard's Workers AI token template when possible.

## 2. Put the credentials in the local environment

In the repository `.env`, set:

```dotenv
LLM_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=96e76c10fcf1d0d5970e17cf5c7008c8
CLOUDFLARE_API_TOKEN=paste-the-new-token-here
```

The account ID is already populated locally. The API token is intentionally blank until you create it.

## 3. Accept the vision-model license once

Screenshot QA uses the natively multimodal `@cf/zai-org/glm-5.3-flash`, which is also the final text fallback. It supports vision, reasoning, and function calling, so no separate legacy vision model is needed.

## 4. Verify connectivity

From the repository root:

```powershell
npx wrangler whoami
python -m compileall -q apps/backend/app
```

Start the backend and exercise a normal generation flow. The text model order is:

1. `@cf/deepseek-ai/deepseek-v4-pro-0813`
2. `@cf/zai-org/glm-5.3`
3. `@cf/qwen/qwen3.8-27b`
4. `@cf/deepseek-ai/deepseek-v4-flash-0731`
5. `@cf/zai-org/glm-5.3-flash`

Each model is skipped after three consecutive failures and retried later after the in-memory failure state resets.

## Production

Set the same variables in the production environment used by `docker compose -f docker-compose.prod.yml`. Do not commit `.env`; it is ignored by Git. DeepSeek V4 Pro is paid Workers AI access, so enable Workers Paid or fund the account as required by Cloudflare before production use.

References:

- [Workers AI REST API](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
- [Workers AI OpenAI-compatible endpoints](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)
- [Llama Vision model setup](https://developers.cloudflare.com/workers-ai/guides/tutorials/llama-vision-tutorial/)
