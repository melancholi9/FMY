# FMY — Claude Code 自動起動セットアップ (claude-auto-launch)

ターミナルで `claude` と打たなくても、**Git リポジトリに入るだけで Claude Code が自動で立ち上がる**ようにするシェル設定です。

一度インストールすれば、**既存のリポジトリ・これから作る新しいリポジトリの両方**で共通に動作します（リポジトリごとの設定は不要です）。

> ※ この設定はあなたのローカルマシン（macOS / Linux / WSL）のシェルに対して行うものです。

## 自動起動するタイミング

- リポジトリのディレクトリに `cd` したとき
- リポジトリ内でターミナルを開いたとき（VS Code の統合ターミナルを含む）
- `git init` で新しいリポジトリを作った直後
- `git clone` したリポジトリに `cd` で入ったとき

## インストール（1回だけ）

```bash
git clone https://github.com/melancholi9/FMY.git
bash FMY/install.sh
```

その後、**新しいターミナルを開く**か、以下で反映します:

```bash
source ~/.zshrc    # zsh の場合
source ~/.bashrc   # bash の場合
```

前提: [Claude Code CLI](https://code.claude.com/docs) がインストール済みであること。未インストールの場合:

```bash
npm install -g @anthropic-ai/claude-code
# または
curl -fsSL https://claude.ai/install.sh | bash
```

## 仕組み

- `install.sh` が `claude-auto-launch.sh` を `~/.config/claude-auto-launch/` にコピーし、`~/.bashrc` / `~/.zshrc` にマーカー付きの読み込み設定を追記します（何度実行しても重複しません）。
- シェルはプロンプトを表示するたびに「現在地が Git リポジトリの中かどうか」を確認し、リポジトリであれば `claude` を起動します。
- 暴走・多重起動しないための安全装置:
  - **同じシェルでは同じリポジトリにつき1回だけ**起動します。`claude` を `exit` した後に勝手に再起動することはありません。
  - Claude Code 内部のシェル（`CLAUDECODE` 環境変数がある環境）では起動しません。
  - スクリプト実行などの非対話シェルでは何もしません。

## 無効化・除外

| やりたいこと | 方法 |
|---|---|
| 今のシェルだけ止める | `export CLAUDE_AUTO_LAUNCH=0` |
| すべてのシェルで止める（恒久） | `claude-auto-launch off`（`on` で再開、`status` で確認） |
| 特定のリポジトリだけ除外する | そのリポジトリ直下で `touch .claude-auto-off` |

`.claude-auto-off` をコミットしたくない場合は `.gitignore` か `.git/info/exclude` に追加してください。

## オプション: VS Code でフォルダを開いた瞬間に起動

シェルフックだけでも VS Code のターミナルを開けば自動起動しますが、「フォルダを開いたら即座にターミナルパネルで Claude Code を立ち上げたい」場合は、対象リポジトリに [`templates/vscode-tasks.json`](templates/vscode-tasks.json) をコピーします:

```bash
mkdir -p .vscode && cp FMY/templates/vscode-tasks.json .vscode/tasks.json
```

初回に VS Code が「タスクの自動実行を許可しますか?」と確認してくるので「許可」を選択してください（コマンドパレット → `Tasks: Manage Automatic Tasks` からも変更できます）。

## アンインストール

```bash
bash FMY/install.sh --uninstall
```

## 対応環境

- シェル: **bash / zsh**（fish は未対応）
- OS: macOS / Linux / WSL

## トラブルシューティング

- **起動しない** → `claude-auto-launch status` で有効か確認。`command -v claude` で CLI が入っているか確認。新しいターミナルで試す。
- **macOS + bash で起動しない** → macOS のターミナルはログインシェルとして `~/.bash_profile` を読むため、`~/.bash_profile` に `[ -f ~/.bashrc ] && . ~/.bashrc` を追加してください（zsh では不要）。
- **powerlevel10k の instant prompt と警告が出る** → 起動メッセージがプロンプト描画前に出るためです。動作には影響ありません。
- **一時的に素のシェルが欲しい** → `claude` を `exit` すればそのままシェルに戻ります（同じシェルでは再起動しません）。
