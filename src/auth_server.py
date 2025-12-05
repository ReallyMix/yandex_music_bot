from flask import Flask, request, render_template_string
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Временное хранилище {state: user_id}
pending_auth = {}

@app.route("/")
def index():
    return "OAuth server для Yandex Music Bot"

@app.route("/auth/<int:user_id>")
def start_auth(user_id):
    """Страница авторизации для пользователя"""
    import secrets
    state = secrets.token_urlsafe(16)
    pending_auth[state] = user_id
    
    # ЗАМЕНИ на свой публичный URL (из ngrok или хостинга)
    redirect_uri = "https://ваш_домен.ngrok.io/callback"
    
    auth_url = (
        f"https://oauth.yandex.ru/authorize"
        f"?response_type=token"
        f"&client_id=23cabbbdc6cd418abb4b39c32c41195d"
        f"&state={state}"
    )
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Авторизация Яндекс.Музыка</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{ color: #333; margin-bottom: 20px; }}
            .btn {{
                background: #FFDB4D;
                color: black;
                padding: 15px 40px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }}
            .btn:hover {{ background: #FFD700; }}
            .emoji {{ font-size: 60px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🎵</div>
            <h1>Авторизация</h1>
            <p>Для продолжения войдите в свой аккаунт Яндекс.Музыки</p>
            <a href="{auth_url}" class="btn">Войти через Яндекс</a>
        </div>
    </body>
    </html>
    """
    return html

@app.route("/callback")
def callback():
    """Страница для обработки callback от Яндекса"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Обработка...</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                text-align: center;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            #status { margin-top: 20px; font-size: 18px; }
            .success { color: #28a745; font-size: 60px; }
            .error { color: #dc3545; font-size: 60px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner" id="spinner"></div>
            <div id="status">⏳ Обработка авторизации...</div>
        </div>
        <script>
            // Извлекаем токен из URL fragment (#access_token=...)
            const hash = window.location.hash.substring(1);
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            const state = params.get('state');
            
            if (token && state) {
                // Отправляем токен на сервер
                fetch('/process_token', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({token: token, state: state})
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('spinner').style.display = 'none';
                    if (data.success) {
                        document.getElementById('status').innerHTML = 
                            '<div class="success">✅</div>' +
                            '<h2>Успешно!</h2>' +
                            '<p>Вернитесь в Telegram бота</p>';
                    } else {
                        throw new Error(data.error);
                    }
                })
                .catch(error => {
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('status').innerHTML = 
                        '<div class="error">❌</div>' +
                        '<h2>Ошибка</h2>' +
                        '<p>' + error.message + '</p>';
                });
            } else {
                document.getElementById('spinner').style.display = 'none';
                document.getElementById('status').innerHTML = 
                    '<div class="error">❌</div>' +
                    '<h2>Ошибка авторизации</h2>' +
                    '<p>Токен не получен</p>';
            }
        </script>
    </body>
    </html>
    """
    return html

@app.route("/process_token", methods=["POST"])
def process_token():
    """Обрабатывает полученный токен и отправляет в бота"""
    data = request.json
    token = data.get("token")
    state = data.get("state")
    
    user_id = pending_auth.pop(state, None)
    
    if not user_id:
        return {"success": False, "error": "Неверный state"}, 400
    
    if not token:
        return {"success": False, "error": "Токен не получен"}, 400
    
    try:
        # Проверяем токен через Yandex Music API
        from yandex_music import Client
        client = Client(token).init()
        account = client.account_status()
        
        # TODO: Сохрани токен в БД
        # from database.repository import save_user_token
        # save_user_token(user_id, token)
        
        # Отправляем сообщение пользователю в Telegram
        message_text = (
            f"✅ Авторизация успешна!\n\n"
            f"Добро пожаловать, {account.account.display_name or account.account.login}! 🎵\n\n"
            f"Теперь используй команды через кнопки меню."
        )
        
        requests.post(
            f"{BOT_API}/sendMessage",
            json={"chat_id": user_id, "text": message_text}
        )
        
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

