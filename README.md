# FMY - 価格比較検索サイト

JANコード（バーコード番号）を入力するだけで、複数のECサイトから最安値の商品を検索できるWebアプリケーションです。

## 機能

- JANコード（8桁/13桁）での商品検索
- 楽天市場・Yahoo!ショッピングからの価格取得
- 価格の安い順で自動ソート
- 最安値商品のハイライト表示
- レスポンシブデザイン対応

## セットアップ

### 1. 依存パッケージのインストール

```bash
npm install
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成し、APIキーを設定します。

```bash
cp .env.example .env
```

`.env`ファイルを編集してAPIキーを設定：

```
RAKUTEN_APP_ID=あなたの楽天APIキー
YAHOO_APP_ID=あなたのYahoo!APIキー
```

### 3. サーバーの起動

```bash
npm start
```

ブラウザで http://localhost:3000 にアクセスしてください。

## APIキーの取得方法

### 楽天API
1. [楽天ウェブサービス](https://webservice.rakuten.co.jp/)にアクセス
2. 楽天会員でログイン
3. 「アプリID発行」からアプリケーションを登録
4. 発行されたアプリIDを`.env`に設定

### Yahoo!ショッピングAPI
1. [Yahoo!デベロッパーネットワーク](https://developer.yahoo.co.jp/)にアクセス
2. Yahoo! JAPAN IDでログイン
3. 「アプリケーションの管理」から新規アプリを作成
4. 発行されたClient IDを`.env`に設定

## デモモード

APIキーを設定していない場合、デモモードで動作します。
デモモードではサンプルデータが表示されます。

## プロジェクト構成

```
FMY/
├── server.js          # バックエンドサーバー
├── package.json       # プロジェクト設定
├── .env.example       # 環境変数のサンプル
├── .gitignore         # Git除外設定
└── public/
    ├── index.html     # メインページ
    ├── style.css      # スタイルシート
    └── script.js      # フロントエンドJS
```

## 技術スタック

- **バックエンド**: Node.js, Express
- **フロントエンド**: HTML5, CSS3, JavaScript (Vanilla)
- **API**: 楽天市場API, Yahoo!ショッピングAPI

## ライセンス

MIT
