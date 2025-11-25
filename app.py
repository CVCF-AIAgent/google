from flask import Flask, request, jsonify, render_template_string
import datetime

app = Flask(__name__)

# シンプルなHTMLをPython側でそのまま返す（テンプレートファイル分けなくてOK仕様）
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
  <p>まずは実験として、「実行」ボタンを押したときにバックエンドのPython処理が走り、そのログをここに表示します。</p>

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

      // 初回の「まだ実行していません」を消す
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
    # HTML をそのまま返すだけ
    return render_template_string(INDEX_HTML)


@app.route("/run", methods=["POST"])
def run_job():
    """
    将来的にここに:
      - Googleカレンダー取得
      - スプレッドシート更新
    を書いていく。
    今はダミーでログだけ返す。
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # ここに実際の処理を書いて、その途中経過をlogsに足していくイメージ
    logs = [
        f"ジョブ開始: {now_str}",
        "ステップ1: GoogleカレンダーAPIの認証チェック（ダミー）",
        "ステップ2: 今日〜明日のイベントを取得（ダミー）",
        "ステップ3: スプレッドシート更新（ダミー）",
        "ジョブ完了 ✅",
    ]

    return jsonify({"status": "ok", "logs": logs})


if __name__ == "__main__":
    # ローカル実行時用（RenderではProcfileでgunicornを使う）
    app.run(host="0.0.0.0", port=5000, debug=True)
