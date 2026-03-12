# FMY CRM

シンプルなCRM（顧客管理システム）です。

## 機能

- **ダッシュボード** — 顧客数・案件数・金額サマリー、ステージ別グラフ、最近の活動
- **顧客管理** — 顧客の追加・編集・削除・検索、詳細ページ（案件・活動履歴付き）
- **案件管理** — カンバンボード形式で案件をステージ別に管理
- **活動履歴** — 電話・メール・打合せ・メモなどの記録

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| Backend  | Node.js + Express |
| Database | SQLite (better-sqlite3) |
| Frontend | Vanilla HTML/CSS/JS |

## セットアップ

```bash
cd backend
npm install
npm start
```

ブラウザで http://localhost:3000 を開く。

## ディレクトリ構成

```
FMY/
├── backend/
│   ├── server.js     # API サーバー
│   ├── db.js         # DB初期化
│   └── package.json
└── frontend/
    ├── index.html
    ├── css/style.css
    └── js/app.js
```
