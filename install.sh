#!/usr/bin/env bash
# install.sh — claude-auto-launch のインストーラ / アンインストーラ
#
#   インストール:     bash install.sh
#   アンインストール: bash install.sh --uninstall
#
# やること:
#   1. claude-auto-launch.sh を ~/.config/claude-auto-launch/ にコピー
#   2. ~/.bashrc / ~/.zshrc にマーカー付きの読み込み設定を追記（冪等）
set -u

MARK_BEGIN="# >>> claude-auto-launch >>>"
MARK_END="# <<< claude-auto-launch <<<"
CONF_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-auto-launch"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_LINE='[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/claude-auto-launch/claude-auto-launch.sh" ] && . "${XDG_CONFIG_HOME:-$HOME/.config}/claude-auto-launch/claude-auto-launch.sh"'

# 設定を書き込む rc ファイルの一覧（存在するもの＋ログインシェル用）
rc_candidates() {
  local files=()
  [ -f "$HOME/.bashrc" ] && files+=("$HOME/.bashrc")
  [ -f "$HOME/.zshrc" ] && files+=("$HOME/.zshrc")
  case "${SHELL:-}" in
    */bash) [[ " ${files[*]-} " == *" $HOME/.bashrc "* ]] || files+=("$HOME/.bashrc") ;;
    */zsh)  [[ " ${files[*]-} " == *" $HOME/.zshrc "* ]] || files+=("$HOME/.zshrc") ;;
  esac
  # どちらも無い場合は両方作る
  [ "${#files[@]}" -gt 0 ] || files=("$HOME/.bashrc" "$HOME/.zshrc")
  printf '%s\n' "${files[@]}"
}

do_install() {
  if [ ! -f "$SRC_DIR/claude-auto-launch.sh" ]; then
    echo "エラー: $SRC_DIR/claude-auto-launch.sh が見つかりません" >&2
    exit 1
  fi

  mkdir -p "$CONF_DIR"
  cp "$SRC_DIR/claude-auto-launch.sh" "$CONF_DIR/claude-auto-launch.sh"
  echo "コピーしました: $CONF_DIR/claude-auto-launch.sh"

  local rc
  while IFS= read -r rc; do
    [ -n "$rc" ] || continue
    touch "$rc"
    if grep -qF "$MARK_BEGIN" "$rc" 2>/dev/null; then
      echo "設定済み（スキップ）: $rc"
    else
      printf '\n%s\n%s\n%s\n' "$MARK_BEGIN" "$SOURCE_LINE" "$MARK_END" >> "$rc"
      echo "追記しました: $rc"
    fi
  done < <(rc_candidates)

  echo ""
  if command -v claude >/dev/null 2>&1; then
    echo "claude CLI: $(command -v claude) ✓"
  else
    echo "⚠ 警告: claude コマンドが見つかりません。先にインストールしてください:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo "  または:"
    echo "    curl -fsSL https://claude.ai/install.sh | bash"
  fi

  echo ""
  echo "インストール完了。新しいターミナルを開くか、以下を実行して反映してください:"
  echo "  source ~/.bashrc   （bash の場合）"
  echo "  source ~/.zshrc    （zsh の場合）"
  echo ""
  echo "以後、Git リポジトリに入ると Claude Code が自動起動します。"
  echo "無効化: claude-auto-launch off / 特定リポジトリのみ除外: touch .claude-auto-off"
}

do_uninstall() {
  local rc tmp removed=0
  for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    [ -f "$rc" ] || continue
    grep -qF "$MARK_BEGIN" "$rc" || continue
    tmp="$(mktemp)"
    awk -v b="$MARK_BEGIN" -v e="$MARK_END" '$0==b{skip=1} !skip{print} $0==e{skip=0}' "$rc" > "$tmp"
    cat "$tmp" > "$rc"
    rm -f "$tmp"
    echo "設定を削除しました: $rc"
    removed=1
  done
  if [ -d "$CONF_DIR" ]; then
    rm -rf "$CONF_DIR"
    echo "削除しました: $CONF_DIR"
    removed=1
  fi
  if [ "$removed" -eq 1 ]; then
    echo "アンインストール完了。反映には新しいターミナルを開いてください。"
  else
    echo "claude-auto-launch はインストールされていません。"
  fi
}

case "${1:-}" in
  ""|install|--install) do_install ;;
  uninstall|--uninstall) do_uninstall ;;
  *)
    echo "使い方: bash install.sh [--uninstall]" >&2
    exit 1
    ;;
esac
