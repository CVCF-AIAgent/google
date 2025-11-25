import os
import datetime

from flask import Flask, request, jsonify, render_template_string

# Google API 関連
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

app = Flask(__name__)

# カレンダー読み取り専用スコープ
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# ---- ここから認証系のヘルパー ----

def prepare_credential_files_from_env():
    """
    Render 用：
    環境変数 GOOGLE_CREDENTIALS_JSON / GOOGLE_TOKEN_JSON があれば
    credentials.json / token.json としてファイルを書き出す。
    （ローカルではなくてもOKなので、今は「あるなら使う」くらいのノリ）
    """
    creds_env = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_env and not os.path.exists("credentials.json"):
        with open("credentials.json", "w", encoding="utf-8") as f:
            f.write(creds_env)

    token_env = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_env and not os.path.exists("token.json"):
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(token_env)


def get_creds():
    """
    OAuth 認証情報(token.json)を取得。
    ・token.json があればそれを使う
    ・なければ credentials.json を使ってブラウザで認証
    ・必要なら refresh_token で自動更新
    """
    prepare_credential_files_from_env()

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 有効な認証情報がない / 期限切れなどの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 期限切れだが refresh_token がある → 自動更新
            creds.refresh(Request())
        else:
            # 初回認証：ブラウザを開いて Google ログイン＆許可
            if not os.path.exists("credentials.json"):
                raise RuntimeError(
                    "credentials.json が見つかりません。GCP からダウンロードして "
                    "このファイルと同じフォルダに置いてください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # 更新or取得した認証情報を token.json に保存
        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds

# ---- ここまで認証系 ----


# HTML テンプレ（前と同じ）
INDEX_HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>カレンダー連携テスト（ログ付き）</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 16px;
      background: #f7f7f7;
    }
    h1 {
      font-size: 1.4rem;
      margin-bottom: 0.5rem;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      padding: 16px 20px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
      margin-bottom: 16px;
    }
    button {
      padding: 8px 16px;
      font-size: 1rem;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      background: #2563eb;
      color: #fff;
    }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    #log {
      font-family: "Consolas", "SFMono-Regular", Menlo, Monaco, monospace;
      white-space: pre-wrap;
      background: #0b1020;
      color: #e5e7eb;
      padding: 12px 14px;
      border-radius: 8px;
      max-height: 300px;
      overflow-y: auto;
      font-size: 0.9rem;
    }
    .log-line-time {
      color: #9ca3af;
    }
  </style>
</head>
<body>
  <h1>カレンダー → スプレッドシート連携テスト</h1>
  <p>今は実験として、「実行」ボタンを押したときに Google カレンダーから予定を取得し、その結果をログに表示します。</p>

  <div class="card">
    <button id="run-btn">実行する</button>
    <span id="status" style="margin-left: 8px; font-size: 0.9rem;"></span>
  </div>

  <div class="card">
    <div style="margin-bottom: 4px; font-weight: 600;">ログ</div>
    <div id="log">(まだ実行していません)</div>
  </div>

  <script>
    const runBtn = document.getElementById('run-btn');
    const statusEl = document.getElementById('status');
    const logEl = document.getElementById('log');

    function appendLogLines(lines) {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('ja-JP', { hour12: false });
      lines.forEach(line => {
        const spanTime = document.createElement('span');
        spanTime.className = 'log-line-time';
        spanTime.textContent = '[' + timeStr + '] ';

        const spanMsg = document.createElement('span');
        spanMsg.textContent = line;

        const br = document.createElement('br');

        logEl.appendChild(spanTime);
        logEl.appendChild(spanMsg);
        logEl.appendChild(br);
      });
      logEl.scrollTop = logEl.scrollHeight;
    }

    runBtn.addEventListener('click', async () => {
      runBtn.disabled = true;
      statusEl.textContent = '実行中...';

      if (logEl.textContent.trim() === '(まだ実行していません)') {
        logEl.textContent = '';
      }

      try {
        const res = await fetch('/run', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ trigger: 'manual' })
        });

        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }

        const data = await res.json();
        if (data && Array.isArray(data.logs)) {
          appendLogLines(data.logs);
        } else {
          appendLogLines(['[エラー] 予期しないレスポンス形式です']);
        }
        statusEl.textContent = '完了';
      } catch (err) {
        console.error(err);
        appendLogLines(['[エラー] リクエストに失敗しました: ' + err.message]);
        statusEl.textContent = 'エラー';
      } finally {
        runBtn.disabled = false;
        setTimeout(() => {
          statusEl.textContent = '';
        }, 2000);
      }
    });
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)


@app.route("/run", methods=["POST"])
def run_job():
    """
    ボタン押下で呼ばれるエンドポイント。
    ここで Google カレンダーから「今日〜明日」の予定を取得してログとして返す。
    """
    logs = []
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"ジョブ開始: {now_str}")

    try:
        # 認証
        logs.append("Google カレンダー認証を開始します...")
        creds = get_creds()
        logs.append("Google カレンダー認証 OK ✅")

        service = build("calendar", "v3", credentials=creds)
        logs.append("Calendar API クライアント生成 OK")

        # 期間：今日 0:00 〜 明日 23:59
        today_start = datetime.datetime(now.year, now.month, now.day, 0, 0)
        tomorrow_end = today_start + datetime.timedelta(days=2, seconds=-1)

        time_min = today_start.isoformat() + "Z"
        time_max = tomorrow_end.isoformat() + "Z"

        logs.append(f"期間: {time_min} ～ {time_max} の予定を取得します...")

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        if not events:
            logs.append("今日〜明日の予定はありません。")
        else:
            logs.append(f"今日〜明日の予定件数: {len(events)} 件")
            for e in events:
                start_raw = e["start"].get("dateTime", e["start"].get("date"))
                summary = e.get("summary", "（タイトルなし）")
                logs.append(f"- {start_raw} | {summary}")

        logs.append("ジョブ完了 ✅")

    except Exception as e:
        logs.append(f"[エラー] {repr(e)}")

    return jsonify({"status": "ok", "logs": logs})


if __name__ == "__main__":
    # ローカル実行用
    app.run(host="0.0.0.0", port=5000, debug=True)
