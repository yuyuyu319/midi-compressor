import os
import io
import time
import mido
from flask import Flask, request, send_file, make_response

app = Flask(__name__)

# --- デザイン & コンテンツ ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MIDI Compressor | ベロシティ圧縮ツール</title>
    <meta name="description" content="オーディオコンプレッサーの理論をMIDIに。指定したスレッショルドを超えるベロシティをレシオに基づいて圧縮し、音楽的なダイナミクス制御を実現します。">
    
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4758959657594096"
     crossorigin="anonymous"></script>

    <style>
        :root { --accent: #d500f9; --bg: #0f172a; --card: #1e293b; --text: #f8fafc; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; text-align: center; padding: 50px 20px; margin:0; line-height: 1.6; }
        .card { background: var(--card); padding: 40px; border-radius: 24px; max-width: 650px; margin: auto; border: 1px solid #334155; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.3); }
        h1 { color: var(--accent); font-size: 2.5rem; margin-bottom: 10px; font-weight: 800; }
        .subtitle { color: #94a3b8; margin-bottom: 30px; font-size: 1.1rem; }
        .form-group { margin: 20px 0; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto; }
        label { display: block; font-size: 0.9rem; color: #94a3b8; margin-bottom: 8px; font-weight: 600; }
        input[type="number"] { width: 100%; padding: 12px; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 8px; font-size: 1rem; box-sizing: border-box; transition: 0.3s; }
        input[type="number"]:focus { border-color: var(--accent); outline: none; }
        button { background: var(--accent); color: white; border: none; padding: 18px; border-radius: 12px; font-weight: bold; cursor: pointer; width: 100%; font-size: 1.1rem; margin-top: 20px; transition: 0.2s; }
        button:hover { transform: translateY(-2px); opacity: 0.9; }
        
        .link-box { margin-top: 25px; padding-top: 20px; border-top: 1px solid #334155; font-size: 0.8rem; color: #94a3b8; }
        .link-box a { text-decoration: none; font-weight: bold; margin: 0 4px; display: inline-block; }
        .link-box a.humanizer { color: #00e676; }
        .link-box a.normalizer { color: #00b0ff; }
        .link-box a.limiter { color: #ff9100; }
        .link-box a.expander { color: #ff5252; }

        .content-section { max-width: 700px; margin: 60px auto; text-align: left; background: rgba(30, 41, 59, 0.5); padding: 40px; border-radius: 20px; border: 1px solid #1e293b; }
        .content-section h2 { color: var(--accent); border-bottom: 2px solid #334155; padding-bottom: 10px; margin-top: 40px; }
        
        .policy-section { max-width: 600px; margin: 80px auto 0; text-align: left; padding: 30px; border-top: 1px solid #334155; color: #94a3b8; font-size: 0.85rem; }
        .policy-section h2 { color: #f8fafc; font-size: 1.1rem; border-left: 4px solid var(--accent); padding-left: 10px; margin-bottom: 15px; }
        .footer-copy { margin-top: 40px; font-size: 0.75rem; color: #475569; padding-bottom: 40px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>MIDI Compressor</h1>
        <p class="subtitle">大きい音だけを、音楽的に圧縮する。</p>
        <form action="/process" method="post" enctype="multipart/form-data">
            <div style="margin-bottom: 25px; border: 2px dashed #334155; padding: 20px; border-radius: 12px;">
                <input type="file" name="midi_file" accept=".mid,.midi" required style="color: #94a3b8;">
            </div>
            <div class="form-group">
                <label>スレッショルド (1-127)<br><small>※この値を超えた音を圧縮します</small></label>
                <input type="number" name="threshold" value="80" min="1" max="127">
            </div>
            <div class="form-group">
                <label>レシオ (比率 1.0-10.0)<br><small>※圧縮の強さを指定します</small></label>
                <input type="number" name="ratio" value="2.0" step="0.1" min="1.0" max="10.0">
            </div>
            <button type="submit">COMPRESS & DOWNLOAD</button>
        </form>
        <div class="link-box">
            関連ツール: 
            <a href="https://midi-humanizer.onrender.com/" class="humanizer">Humanizer</a> | 
            <a href="https://midi-normalizer.onrender.com/" class="normalizer">Normalizer</a> | 
            <a href="https://midi-limiter.onrender.com/" class="limiter">Limiter</a> | 
            <a href="https://midi-expander.onrender.com/" class="expander">Expander</a>
        </div>
    </div>

    <div class="content-section">
        <h2>MIDIコンプレッサーのメリット</h2>
        <p>オーディオ用のコンプレッサーと同様に、スレッショルドを超えたベロシティをレシオに基づいて圧縮します。MIDIリミッターが上限でバッサリ切るのに対し、コンプレッサーは超過分を「比率」で小さくするため、演奏の表情やニュアンスを殺さずに、ピークだけを自然に抑えることができます。</p>
        <h3>主な用途</h3>
        <p>・強すぎる打鍵を抑え、ミックスの馴染みを良くする<br>・ベロシティが高い時の音源側の音色変化（キツさ）をマイルドにする<br>・トラックのダイナミクスレンジを音楽的に狭める</p>
    </div>

    <div class="policy-section">
        <h2>プライバシーポリシー</h2>
        <p><strong>データ処理：</strong>アップロードされたMIDIファイルはサーバーに保存されず、メモリ内で即座に処理・返送されます。プライバシーは完全に守られます。</p>
        <p><strong>広告配信：</strong>当サイトではGoogle AdSense等の第三者配信事業者がCookieを利用して広告を配信する場合があります。</p>
    </div>

    <div class="footer-copy">&copy; 2026 MIDI Compressor. All rights reserved.</div>
</body>
</html>
"""

# --- MIDI処理ロジック ---
def process_logic(midi_file_stream, threshold, ratio):
    midi_file_stream.seek(0)
    input_data = io.BytesIO(midi_file_stream.read())
    try:
        mid = mido.MidiFile(file=input_data)
    except: return None
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                if msg.velocity > threshold:
                    # 圧縮計算: スレッショルド + (超過分 / レシオ)
                    msg.velocity = int(threshold + (msg.velocity - threshold) / ratio)
                msg.velocity = max(1, min(127, msg.velocity))
    output = io.BytesIO()
    mid.save(file=output)
    output.seek(0)
    return output

# --- ルーティング ---
@app.route('/')
def index():
    response = make_response(HTML_PAGE)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@app.route('/process', methods=['POST'])
def process():
    file = request.files['midi_file']
    threshold = int(request.form.get('threshold', 80))
    ratio = float(request.form.get('ratio', 2.0))
    processed_midi = process_logic(file, threshold, ratio)
    return send_file(processed_midi, as_attachment=True, download_name="compressed.mid", mimetype='audio/midi')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
