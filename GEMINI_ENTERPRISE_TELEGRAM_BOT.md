# Gemini Enterprise (Create Agent) ကို Telegram Bot နဲ့ချိတ်ဆက်နည်း

ဒီ guide က **Gemini Enterprise > Create Agent** မှာ build လုပ်ထားတဲ့ agent ကို **Telegram Bot** ကနေ message ပို့ပြီး response ပြန်ယူနိုင်အောင် practical setup ပေးထားပါတယ်။

## 1) Architecture (အကျဉ်း)

Telegram User ➜ Telegram Bot ➜ Webhook Server ➜ Gemini Enterprise Agent ➜ Telegram Reply

> အဓိက logic က webhook server ထဲမှာရှိပါတယ်။ Telegram က message ကို webhook endpoint ကို POST လုပ်မယ်၊ server က Gemini agent ကိုခေါ်ပြီး result ကို Telegram chat ထဲ reply ပြန်ပို့မယ်။

## 2) လိုအပ်တာများ

- Google Cloud project (Gemini Enterprise / Vertex AI Agent Builder access ရရှိရမည်)
- Telegram account
- Public HTTPS URL ရတဲ့ server (Cloud Run, Render, Railway, VPS + SSL)
- Env vars သိမ်းနိုင်တဲ့ runtime

## 3) Telegram Bot ဖန်တီးခြင်း

1. Telegram ထဲ `@BotFather` ကိုရှာပါ
2. `/newbot` လိုက်လုပ်ပါ
3. Bot name + username သတ်မှတ်ပါ
4. ထွက်လာတဲ့ **BOT_TOKEN** ကိုသိမ်းထားပါ

## 4) Gemini Enterprise Agent ဆင်ခြင်မှု

Create Agent မှာ အောက်ပါအချက်တွေ clear ဖြစ်ရင် integration လွယ်ပါတယ်

- Instruction ကိုတိုတောင်း/ရှင်းလင်းအောင်ရေးပါ
- Output format ကိုခိုင်မာစေပါ (ဥပမာ: plain text only)
- Safety policy ကြောင့် blocked ဖြစ်နိုင်တဲ့ use case တွေကို anticipate လုပ်ပါ
- Session memory လို/မလို မတိုင်မီသတ်မှတ်ပါ

## 5) Python Webhook Sample

`server.py`

```python
import os
import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Gemini Enterprise side
# သင့် project setup အလိုက် endpoint / auth ပြောင်းရန်လိုသည်
GEMINI_AGENT_ENDPOINT = os.environ["GEMINI_AGENT_ENDPOINT"]
GEMINI_BEARER_TOKEN = os.environ["GEMINI_BEARER_TOKEN"]


def call_gemini_agent(user_text: str, user_id: str) -> str:
    payload = {
        "input": user_text,
        "user_id": user_id,
    }
    headers = {
        "Authorization": f"Bearer {GEMINI_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }

    r = requests.post(GEMINI_AGENT_ENDPOINT, json=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Gemini error: {r.text}")

    data = r.json()
    # Agent response schema ပေါ်မူတည်ပြီး key အမည်ပြောင်းရနိုင်
    return data.get("text", "No response from agent")


def telegram_send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )


@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    body = await req.json()

    message = body.get("message") or {}
    text = message.get("text")
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    from_user = message.get("from") or {}
    user_id = str(from_user.get("id", "unknown"))

    if not text or not chat_id:
        return {"ok": True}

    try:
        answer = call_gemini_agent(text, user_id)
    except Exception:
        answer = "တောင်းပန်ပါတယ်၊ လက်ရှိမှာ request ကို process မလုပ်နိုင်သေးပါ။"

    telegram_send_message(chat_id, answer)
    return {"ok": True}
```

## 6) Webhook သတ်မှတ်ခြင်း

Server deploy ပြီး public URL ရရင်:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<YOUR_DOMAIN>/telegram/webhook"
```

Webhook status စစ်ရန်:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

## 7) Security Best Practices

- Bot token ကို code ထဲ hardcode မလုပ်ပါနဲ့ (env var သုံးပါ)
- Telegram secret path သုံးပါ (ဥပမာ `/telegram/webhook/<secret>`)
- IP allowlist သို့မဟုတ် HMAC verification ထည့်နိုင်ရင်ထည့်ပါ
- Gemini endpoint authorization ကို short-lived token သုံးပါ
- Logging မှာ PII masking လုပ်ပါ

## 8) Troubleshooting

- **Webhook 404**: route path မတူခြင်း / deploy route mismatch
- **No reply**: app logs မှာ Telegram payload parse error စစ်ပါ
- **401/403 from Gemini**: bearer token scope/expiry စစ်ပါ
- **Timeout**: Gemini call latency မြင့်ရင် async queue သို့ background job pattern သုံးပါ

## 9) Next Step (Production)

- Redis cache ထည့်ပြီး frequent FAQ ကို cache လုပ်ပါ
- Per-user rate limit ထည့်ပါ
- `/start`, `/help`, `/reset` command handlers ထည့်ပါ
- Monitoring (error rate, p95 latency) dashboard ဆောက်ပါ

---

လိုချင်ရင် နောက်တစ်ဆင့်အနေနဲ့ **သင့် Create Agent response schema အတိုင်း** webhook sample ကို exact mapping ဖြင့် customize လုပ်ပေးနိုင်ပါတယ်။
