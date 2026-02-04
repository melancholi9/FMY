import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///fmy.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # スクレイピング間隔(秒) - デフォルト60秒
    SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", 60))

    # LINE Notify トークン
    LINE_NOTIFY_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN", "")

    # オッズ変動アラートのデフォルト閾値
    # オッズが前回から何%以上変動したらアラートを出すか
    DEFAULT_CHANGE_THRESHOLD_PERCENT = float(
        os.environ.get("DEFAULT_CHANGE_THRESHOLD_PERCENT", 20.0)
    )

    # オッズが絶対値で何ポイント以上変動したらアラートを出すか
    DEFAULT_CHANGE_THRESHOLD_ABSOLUTE = float(
        os.environ.get("DEFAULT_CHANGE_THRESHOLD_ABSOLUTE", 5.0)
    )

    # 急落検知: 直近N回の取得で連続して下がっている場合
    CONSECUTIVE_DROP_COUNT = int(os.environ.get("CONSECUTIVE_DROP_COUNT", 3))

    # User-Agent
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
