# FMY - 競馬オッズ変動アラート

競馬のオッズ変動をリアルタイムで監視し、設定した閾値を超える変動があった場合にアラートを通知するWebアプリケーション。

## 機能

- **オッズ自動取得**: JRA公式サイトからオッズデータを定期取得（デモモード対応）
- **変動検知**: 3種類の検知ロジック
  - **変動率アラート**: オッズが前回から一定%以上変動した場合
  - **変動量アラート**: オッズが一定ポイント以上変動した場合
  - **連続下落アラート**: オッズが連続して下がり続けている場合
- **LINE通知**: LINE Notify でスマートフォンにプッシュ通知
- **Webダッシュボード**: オッズ推移チャート、アラート履歴をブラウザで確認
- **カスタマイズ可能なルール**: 閾値、監視方向、対象レース/馬を自由に設定

## 技術スタック

- Python 3 / Flask
- SQLAlchemy + SQLite
- APScheduler（定期実行）
- BeautifulSoup4（スクレイピング）
- Chart.js（グラフ描画）
- LINE Notify API（通知）

## セットアップ

### 1. 依存パッケージのインストール

```bash
python -m venv venv
source venv/bin/activate  # Windowsは venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` ファイルを編集して設定値を入力:

```
SECRET_KEY=your-secret-key
LINE_NOTIFY_TOKEN=your-line-notify-token
SCRAPE_INTERVAL=60
DEFAULT_CHANGE_THRESHOLD_PERCENT=20.0
DEFAULT_CHANGE_THRESHOLD_ABSOLUTE=5.0
```

### 3. アプリの起動

```bash
# デモモード（模擬データで動作確認）
DEMO_MODE=1 python app.py

# 本番モード（JRAサイトから実データ取得）
DEMO_MODE=0 python app.py
```

ブラウザで http://localhost:5000 にアクセス。

## 使い方

### ダッシュボード

- 監視中のレース一覧と最新アラートが表示される
- レースをクリックすると、オッズ推移チャートと詳細を確認可能

### アラート設定

- `/settings` ページで、アラートルールの作成・編集・削除が可能
- 主な設定項目:
  - **変動率閾値**: 何%以上のオッズ変動でアラートを出すか
  - **変動量閾値**: 何ポイント以上の変動でアラートを出すか
  - **監視方向**: 下落のみ / 上昇のみ / 両方
  - **連続下落回数**: 何回連続で下がったらアラートを出すか
  - **通知方法**: LINE / Web / 両方

### LINE Notify 設定

1. [LINE Notify](https://notify-bot.line.me/) にLINEアカウントでログイン
2. マイページでアクセストークンを発行
3. `.env` の `LINE_NOTIFY_TOKEN` にトークンを設定
4. アプリを再起動

## テスト

```bash
python -m pytest tests/ -v
```

## プロジェクト構成

```
FMY/
├── app.py                  # Flaskアプリ・APIエンドポイント
├── config.py               # 設定管理
├── requirements.txt        # 依存パッケージ
├── .env.example            # 環境変数テンプレート
├── models/
│   ├── __init__.py
│   └── database.py         # DBモデル (Race, RaceEntry, OddsSnapshot, AlertRule, AlertLog)
├── scraper/
│   ├── __init__.py
│   └── odds_scraper.py     # JRAスクレイパー + デモスクレイパー
├── alerts/
│   ├── __init__.py
│   ├── detector.py         # オッズ変動検知エンジン
│   └── notifier.py         # LINE Notify通知
├── scheduler/
│   ├── __init__.py
│   └── jobs.py             # 定期実行ジョブ
├── templates/
│   ├── base.html
│   ├── index.html          # ダッシュボード
│   ├── race_detail.html    # レース詳細（オッズ推移チャート）
│   └── settings.html       # アラート設定
├── static/
│   ├── css/style.css
│   └── js/main.js
└── tests/
    └── test_detector.py    # ユニットテスト
```
