# claude-auto-launch.sh
# Git リポジトリに入ると Claude Code (claude) を自動起動するシェルフック。
# bash / zsh 両対応。install.sh がこのファイルを
# ~/.config/claude-auto-launch/ にコピーし、~/.bashrc / ~/.zshrc から
# source されるように設定する。
#
# 自動起動するタイミング:
#   - リポジトリのディレクトリに cd したとき
#   - リポジトリ内で新しいターミナルを開いたとき（VS Code のターミナル含む）
#   - git init / git clone で作ったリポジトリに入った直後
#
# 無効化の方法:
#   claude-auto-launch off            … すべてのシェルで恒久的に無効化
#   claude-auto-launch on             … 再度有効化
#   export CLAUDE_AUTO_LAUNCH=0       … 現在のシェルだけ無効化
#   リポジトリ直下に .claude-auto-off … そのリポジトリだけ除外

_CLAUDE_AL_STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/claude-auto-launch"
_CLAUDE_AL_DISABLE_FILE="$_CLAUDE_AL_STATE_DIR/disabled"

_claude_auto_launch_try() {
  # 対話シェル以外（スクリプト実行・scp など）では何もしない
  case "$-" in *i*) ;; *) return 0 ;; esac
  # Claude Code のセッション内部では起動しない（多重起動・ループ防止）
  [ -z "${CLAUDECODE:-}" ] || return 0
  # 無効化スイッチ
  [ "${CLAUDE_AUTO_LAUNCH:-1}" != "0" ] || return 0
  [ ! -e "$_CLAUDE_AL_DISABLE_FILE" ] || return 0
  command -v claude >/dev/null 2>&1 || return 0

  local root
  root="$(command git rev-parse --show-toplevel 2>/dev/null)" || return 0
  [ -n "$root" ] || return 0
  # リポジトリ単位の除外
  [ ! -e "$root/.claude-auto-off" ] || return 0
  # 同じシェルで一度起動したリポジトリでは再起動しない
  #（claude を exit した後、勝手に立ち上がり直さないため）
  case ":${_CLAUDE_AL_LAUNCHED:-}:" in
    *":$root:"*) return 0 ;;
  esac
  _CLAUDE_AL_LAUNCHED="${_CLAUDE_AL_LAUNCHED:-}:$root"

  printf '[claude-auto-launch] %s で Claude Code を起動します（exit でシェルに戻ります / 無効化: claude-auto-launch off）\n' "${root##*/}"
  claude
}

# 有効/無効を切り替えるユーティリティコマンド
claude-auto-launch() {
  case "${1:-status}" in
    on)
      rm -f "$_CLAUDE_AL_DISABLE_FILE"
      echo "claude-auto-launch: 有効にしました"
      ;;
    off)
      mkdir -p "$_CLAUDE_AL_STATE_DIR"
      : > "$_CLAUDE_AL_DISABLE_FILE"
      echo "claude-auto-launch: 無効にしました（claude-auto-launch on で戻せます）"
      ;;
    status)
      if [ -e "$_CLAUDE_AL_DISABLE_FILE" ]; then
        echo "claude-auto-launch: 無効（claude-auto-launch on で有効化）"
      elif [ "${CLAUDE_AUTO_LAUNCH:-1}" = "0" ]; then
        echo "claude-auto-launch: このシェルでは無効（CLAUDE_AUTO_LAUNCH=0）"
      else
        echo "claude-auto-launch: 有効"
      fi
      ;;
    *)
      echo "使い方: claude-auto-launch [on|off|status]"
      return 1
      ;;
  esac
}

# プロンプト表示前フックとして登録（再 source しても重複登録されない）
if [ -n "${ZSH_VERSION:-}" ]; then
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd _claude_auto_launch_try
elif [ -n "${BASH_VERSION:-}" ]; then
  if [[ "$(declare -p PROMPT_COMMAND 2>/dev/null)" == "declare -a"* ]]; then
    # bash 5.1+ で PROMPT_COMMAND が配列の場合
    [[ " ${PROMPT_COMMAND[*]} " == *" _claude_auto_launch_try "* ]] || PROMPT_COMMAND+=(_claude_auto_launch_try)
  else
    case ";${PROMPT_COMMAND:-};" in
      *";_claude_auto_launch_try;"*) ;;
      *) PROMPT_COMMAND="_claude_auto_launch_try${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
    esac
  fi
fi
