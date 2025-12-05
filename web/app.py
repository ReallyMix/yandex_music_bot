import os
import secrets
from flask import Flask, request, redirect, render_template_string
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(16))

BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "23cabbbdc6cd418abb4b39c32c41195d")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Временное хранилище для связи user_id с state
pending_auth = {}

@app.route("/")
def index():
    return """
    <html>
    <head><title>Yandex Music Bot Auth</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>🎵 Yandex Music Bot</h1>
        <p>Сервер авторизации работает!</p>
        <p>Используйте Telegram бота для входа.</p>
    </body>
    </html>
    """

@app.route("/auth/<int:user_id>")
def auth(user_id):
    """Начало авторизации - редирект на Яндекс OAuth"""
    state = secrets.token_urlsafe(16)
    pending_auth[state] = user_id
    
    redirect_uri = f"{BASE_URL}/callback"
    auth_url = (
        "https://oauth.yandex.ru/authorize"
        f"?response_type=token"
        f"&client_id={YANDEX_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        "&force_confirm=yes"
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """Callback страница после авторизации"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Авторизация...</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 400px;
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
                font-size: 24px;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .success {
                color: #28a745;
                font-size: 48px;
                display: none;
            }
            .success h2 {
                font-size: 24px;
                margin-top: 20px;
            }
            .error {
                color: #dc3545;
                display: none;
            }
            .error h2 {
                font-size: 20px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div id="loading">
                <h1>🎵 Обработка авторизации...</h1>
                <div class="spinner"></div>
            </div>
            <div id="success" class="success">
                ✅
                <h2>Готово!</h2>
                <p>Возвращайся в бота</p>
            </div>
            <div id="error" class="error">
                <h2>❌ Ошибка</h2>
                <p id="errorMsg"></p>
            </div>
        </div>

        <script>
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            const state = params.get('state');
            
            if (token && state) {
                fetch('/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token, state: state })
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    if (data.success) {
                        document.getElementById('success').style.display = 'block';
                        setTimeout(() => { window.close(); }, 2000);
                    } else {
                        document.getElementById('error').style.display = 'block';
                        document.getElementById('errorMsg').textContent = data.error || 'Неизвестная ошибка';
                    }
                })
                .catch(err => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('errorMsg').textContent = 'Ошибка связи с сервером';
                });
            } else {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('errorMsg').textContent = 'Токен не получен от Яндекса';
            }
        </script>
    </body>
    </html>
    """)

@app.route("/process", methods=["POST"])
def process():
    """Обработка токена и отправка в Telegram"""
    data = request.json
    token = data.get("token")
    state = data.get("state")
    
    if not token or not state:
        return {"success": False, "error": "Неверные данные"}
    
    user_id = pending_auth.pop(state, None)
    
    if not user_id:
        return {"success": False, "error": "Сессия истекла"}
    
    try:
        # Проверяем токен
        from yandex_music import Client
        client = Client(token).init()
        account = client.account_status()
        
        # Отправляем сообщение в Telegram
        message_text = (
            f"✅ <b>Авторизация успешна!</b>\n\n"
            f"Пользователь: <b>{account.account.display_name or account.account.login}</b>\n"
            f"Аккаунт: {account.account.login}\n"
            f"Подписка: {'Яндекс Плюс ⭐' if account.plus else 'Без подписки'}\n\n"
            f"Используй команды через кнопки меню."
        )
        
        telegram_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(telegram_api_url, json={
            "chat_id": user_id,
            "text": message_text,
            "parse_mode": "HTML"
        })
        
        if response.status_code == 200:
            # TODO: Сохранить токен в БД
            # from src.database.repository import get_repository
            # repo = get_repository()
            # repo.save_user(user_id, token, account.account.login)
            
            return {"success": True}
        else:
            return {"success": False, "error": "Не удалось отправить сообщение в Telegram"}
            
    except Exception as e:
        return {"success": False, "error": f"Ошибка: {str(e)}"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Flask сервер запущен на порту {port}")
    print(f"🔗 BASE_URL: {BASE_URL}")
    app.run(host="0.0.0.0", port=port, debug=True)
