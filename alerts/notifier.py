"""
通知送信モジュール

LINE Notify を使ってオッズ変動アラートをユーザーに通知する。
"""

import logging

import requests

from config import Config

logger = logging.getLogger(__name__)

LINE_NOTIFY_API = "https://notify-api.line.me/api/notify"


def send_line_notify(message):
    """
    LINE Notify でメッセージを送信する。

    Args:
        message: 送信するメッセージ文字列

    Returns:
        bool: 送信成功ならTrue
    """
    token = Config.LINE_NOTIFY_TOKEN
    if not token:
        logger.warning("LINE Notify トークンが設定されていません")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}

    try:
        resp = requests.post(LINE_NOTIFY_API, headers=headers, data=data, timeout=10)

        if resp.status_code == 200:
            logger.info("LINE通知を送信しました")
            return True
        else:
            logger.error(
                "LINE通知の送信に失敗: status=%d, body=%s",
                resp.status_code,
                resp.text,
            )
            return False

    except requests.RequestException as e:
        logger.error("LINE通知の送信中にエラーが発生: %s", e)
        return False


def send_alert_notifications(alert_logs):
    """
    アラートログのリストをまとめて通知する。

    Args:
        alert_logs: list[AlertLog] 通知対象のアラートログ

    Returns:
        int: 通知成功数
    """
    if not alert_logs:
        return 0

    success_count = 0

    for alert in alert_logs:
        if alert.is_notified:
            continue

        notify_method = "both"
        if alert.alert_rule:
            notify_method = alert.alert_rule.notify_method

        sent = False
        if notify_method in ("line", "both"):
            sent = send_line_notify(alert.message)

        # Webは常にログに記録されるので、LINE送信の成否に関わらず通知済みとする
        if notify_method == "web" or sent:
            alert.is_notified = True
            success_count += 1

    return success_count
