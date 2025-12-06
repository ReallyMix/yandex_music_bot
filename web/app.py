import os
import secrets
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
from yandex_music import Client

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# привязка state -> telegram_user_id
pending_auth: Dict[str, int] = {}


@app.get("/")
async def index():
    return {"status": "ok", "message": "Yandex Music Bot OAuth backend (FastAPI)"}


@app.get("/auth/{user_id}")
async def auth(user_id: int):
    """Старт авторизации: редирект на OAuth Яндекса."""
    state = secrets.token_urlsafe(16)
    pending_auth[state] = user_id

    redirect_uri = f"{BASE_URL}/callback"

    auth_url = (
        "https://oauth.yandex.ru/authorize"
        f"?response_type=token"
        f"&client_id={YANDEX_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&force_confirm=yes"
    )
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback():
    """Страница, куда прилетает redirect от Яндекса (access_token в hash)."""
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Авторизация Yandex Music Bot</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           display:flex;align-items:center;justify-content:center;
           min-height:100vh;background:#111;color:#fff; }}
    .card {{ background:#181818;padding:32px;border-radius:16px;
             box-shadow:0 10px 40px rgba(0,0,0,0.6);text-align:center;
             max-width:360px; }}
    .spinner {{ border:4px solid #333;border-top:4px solid #1DB954;
               border-radius:50%;width:40px;height:40px;
               animation:spin 1s linear infinite;margin:16px auto; }}
    @keyframes spin {{0%{{transform:rotate(0deg);}}100%{{transform:rotate(360deg);}}}}
  </style>
</head>
<body>
  <div class="card">
    <h2>Завершаем авторизацию…</h2>
    <div class="spinner"></div>
    <p>Окно можно будет закрыть через пару секунд.</p>
  </div>
  <script>
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const token = params.get('access_token');
    const state = params.get('state');

    if (token && state) {{
      fetch('{BASE_URL}/process', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ token, state }})
      }}).then(() => {{
        setTimeout(() => window.close(), 1500);
      }});
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/process")
async def process(request: Request):
    """Получаем токен от JS, валидируем, шлём сообщение пользователю."""
    data = await request.json()
    token = data.get("token")
    state = data.get("state")

    if not token or not state:
        return JSONResponse({"success": False, "error": "bad data"}, status_code=400)

    user_id = pending_auth.pop(state, None)
    if not user_id:
        return JSONResponse({"success": False, "error": "state expired"}, status_code=400)

    try:
        client = Client(token).init()
        account = client.account_status()
    except Exception as e:
        return JSONResponse({"success": False, "error": f"yandex error: {e}"}, status_code=400)

    text = (
        "✅ <b>Авторизация в Яндекс.Музыке успешна!</b>\n\n"
        f"Пользователь: <b>{account.account.display_name or account.account.login}</b>\n"
        f"Аккаунт: {account.account.login}\n"
        f"Подписка: {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
        "Сейчас токен всё ещё нужно будет вставить вручную в бота (позже можно автоматизировать)."
    )

    telegram_api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        telegram_api,
        json={"chat_id": user_id, "text": text, "parse_mode": "HTML"},
        timeout=10,
    )

    return JSONResponse({"success": True})
