# 副業回収ダッシュボード

副業で使った自己投資額を、収入・経費・利益と比較しながら回収状況を可視化する Streamlit アプリです。  
`Google Sheets` の `Input` シートを読み込み、回収率や未回収額、月別推移を表示します。

## 主な機能

- Google Sheets から `Input` シートを読み込み
- 日付・金額データの型変換（欠損や記号付き金額にも対応）
- 以下の KPI をサマリーカードで表示
  - 総収入
  - 総経費
  - 事業利益（収入 - 経費）
  - 自己投資額（自己投資フラグ TRUE）
  - 回収率（収入 ÷ 自己投資額 × 100）
- 回収状況（未回収額 / 回収ステータス）を表示
- 月別の収入・経費・利益をグラフ表示
- 入力データ一覧を表示
- 回収率・利益状況に応じた自動コメント表示
- スマホでも見やすい余白・文字サイズ調整

## データ仕様（Input シート）

以下の列を想定しています（この順番が推奨）:

1. 日付
2. 区分（収入 / 経費）
3. 収益カテゴリ
4. 勘定科目
5. 固定変動区分
6. 自己投資フラグ（TRUE / FALSE）
7. 金額
8. 内容

## セットアップ

```bash
pip install -r requirements.txt
```

## Google Sheets 認証設定

次のいずれかでサービスアカウント認証情報を設定してください。

1. `./.streamlit/secrets.toml` に設定（推奨）
2. 環境変数 `GCP_SERVICE_ACCOUNT_JSON` に JSON 文字列で設定
3. プロジェクト直下に `credentials.json` を配置

`secrets.toml` 例:

```toml
spreadsheet_id = "YOUR_SPREADSHEET_ID"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

## 起動方法

```bash
streamlit run app.py
```

起動後、画面上部の `GoogleスプレッドシートID` に対象の ID を入力すると集計が表示されます。  
`secrets.toml` に `spreadsheet_id` を設定済みの場合は自動入力されます。

## 補足

- Google Sheets 側で、サービスアカウントの `client_email` を共有ユーザーとして追加してください。
- 金額は `1,000` や `¥1000` のような形式でも自動で数値化します。
- 日付が解釈できない行は除外されます。
