"""
定期実行ジョブ

APSchedulerで定期的にオッズデータを取得し、変動検知を実行する。
"""

import logging
from datetime import datetime

from models.database import db, Race, RaceEntry, OddsSnapshot
from scraper.odds_scraper import JRAOddsScraper, DemoOddsScraper
from alerts.detector import OddsChangeDetector
from alerts.notifier import send_alert_notifications
from config import Config

logger = logging.getLogger(__name__)


def scrape_and_check(app, demo_mode=False):
    """
    オッズデータを取得し、変動チェック・通知を行うメインジョブ。

    Args:
        app: Flaskアプリインスタンス
        demo_mode: Trueならデモデータを使用
    """
    with app.app_context():
        try:
            logger.info("=== オッズ取得ジョブを開始 ===")

            scraper = DemoOddsScraper() if demo_mode else JRAOddsScraper()

            # アクティブなレースを取得
            active_races = Race.query.filter_by(is_active=True).all()

            if not active_races:
                logger.info("監視中のレースがありません")
                # デモモードの場合は自動でレースを登録
                if demo_mode:
                    _register_demo_races(scraper)
                    active_races = Race.query.filter_by(is_active=True).all()

                if not active_races:
                    return

            # 各レースのオッズを取得
            for race in active_races:
                _fetch_and_store_odds(scraper, race)

            # オッズ変動をチェック
            detector = OddsChangeDetector()
            alerts = detector.check_all_entries()

            # アラート通知を送信
            if alerts:
                notified = send_alert_notifications(alerts)
                db.session.commit()
                logger.info("%d件のアラートを通知しました", notified)

            logger.info("=== オッズ取得ジョブを完了 ===")

        except Exception as e:
            logger.exception("オッズ取得ジョブでエラーが発生: %s", e)
            db.session.rollback()


def _register_demo_races(scraper):
    """デモ用レースを登録する"""
    races_data = scraper.fetch_race_list()

    for data in races_data:
        existing = Race.query.filter_by(race_id=data["race_id"]).first()
        if existing:
            continue

        race = Race(
            race_id=data["race_id"],
            race_name=data["race_name"],
            race_date=datetime.strptime(data["race_date"], "%Y%m%d").date(),
            venue=data["venue"],
            race_number=data["race_number"],
            post_time=data.get("post_time", ""),
            race_type=data.get("race_type", ""),
            distance=data.get("distance"),
            is_active=True,
        )
        db.session.add(race)
        db.session.flush()

        # 出走馬も登録
        odds_list = scraper.fetch_win_odds(data["race_id"])
        for odds_data in odds_list:
            entry = RaceEntry(
                race_id=race.id,
                horse_number=odds_data["horse_number"],
                horse_name=odds_data["horse_name"],
                popularity=odds_data.get("popularity"),
            )
            db.session.add(entry)

    db.session.commit()
    logger.info("デモ用レースを登録しました")


def _fetch_and_store_odds(scraper, race):
    """特定レースのオッズを取得し、DBに保存する"""
    odds_list = scraper.fetch_win_odds(race.race_id)
    now = datetime.utcnow()

    for odds_data in odds_list:
        # 該当馬のエントリーを取得
        entry = RaceEntry.query.filter_by(
            race_id=race.id,
            horse_number=odds_data["horse_number"],
        ).first()

        if not entry:
            # エントリーが存在しなければ作成
            entry = RaceEntry(
                race_id=race.id,
                horse_number=odds_data["horse_number"],
                horse_name=odds_data["horse_name"],
                popularity=odds_data.get("popularity"),
            )
            db.session.add(entry)
            db.session.flush()

        # 人気順を更新
        if odds_data.get("popularity"):
            entry.popularity = odds_data["popularity"]

        # オッズスナップショットを保存
        snapshot = OddsSnapshot(
            entry_id=entry.id,
            odds_type="win",
            odds_value=odds_data["odds"],
            fetched_at=now,
        )
        db.session.add(snapshot)

    db.session.commit()
    logger.debug("race_id=%s のオッズを保存しました", race.race_id)
