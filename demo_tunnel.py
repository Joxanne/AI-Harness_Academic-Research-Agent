"""
Live Demo 通道 — 使用 pyngrok 將本機 Chainlit 暴露為公開 URL

使用方式：
  pip install pyngrok
  python demo_tunnel.py
"""

import subprocess
import sys
import time
import os


def main():
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print("安裝 pyngrok...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
        from pyngrok import ngrok, conf

    # 啟動 Chainlit（背景）
    print("啟動 Chainlit 伺服器 (port 8000)...")
    server = subprocess.Popen(
        [sys.executable, "-m", "chainlit", "run", "src/app.py",
         "--headless", "--port", "8000"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    # 等待伺服器就緒
    time.sleep(4)

    # 建立 ngrok 通道
    print("建立公開通道...")
    tunnel = ngrok.connect(8000, "http")
    public_url = tunnel.public_url

    print("\n" + "=" * 60)
    print(f"  Live Demo URL: {public_url}")
    print("=" * 60)
    print("分享上方網址即可讓他人存取 Demo")
    print("按 Ctrl+C 關閉\n")

    try:
        server.wait()
    except KeyboardInterrupt:
        print("\n關閉中...")
        ngrok.kill()
        server.terminate()


if __name__ == "__main__":
    main()
