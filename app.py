"""
FMY - 競馬オッズ変動アラートアプリ

メインアプリケーションエントリーポイント。
"""

import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request

from config import Config
from models.database import (
    AlertLog,
    AlertRule,
    OddsSnapshot,
    Race,
    RaceEntry,
    db,
)
from scheduler.jobs import scrape_and_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _ensure_default_alert_rule()

    return app


def _ensure_default_alert_rule():
    """デフォルトのアラートルールが存在しなければ作成する"""
    if AlertRule.query.count() == 0:
        default_rule = AlertRule(
            name="デフォルトルール",
            is_enabled=True,
            change_threshold_percent=Config.DEFAULT_CHANGE_THRESHOLD_PERCENT,
            change_threshold_absolute=Config.DEFAULT_CHANGE_THRESHOLD_ABSOLUTE,
            consecutive_drop_count=Config.CONSECUTIVE_DROP_COUNT,
            direction="both",
            notify_method="both",
        )
        db.session.add(default_rule)
        db.session.commit()
        logger.info("デフォルトアラートルールを作成しました")


app = create_app()


# =============================================================================
# ページルーティング
# =============================================================================


@app.route("/")
def index():
    """ダッシュボード - レース一覧とアラート一覧"""
    races = Race.query.filter_by(is_active=True).order_by(Race.race_number).all()
    recent_alerts = (
        AlertLog.query.order_by(AlertLog.created_at.desc()).limit(20).all()
    )
    return render_template("index.html", races=races, alerts=recent_alerts)


@app.route("/race/<int:race_id>")
def race_detail(race_id):
    """レース詳細 - オッズ推移グラフ"""
    race = Race.query.get_or_404(race_id)
    entries = (
        RaceEntry.query.filter_by(race_id=race.id)
        .order_by(RaceEntry.horse_number)
        .all()
    )

    # 各馬のオッズ履歴を準備
    entries_data = []
    for entry in entries:
        snapshots = (
            OddsSnapshot.query.filter_by(entry_id=entry.id, odds_type="win")
            .order_by(OddsSnapshot.fetched_at)
            .all()
        )
        entries_data.append(
            {
                "entry": entry,
                "snapshots": snapshots,
                "current_odds": snapshots[-1].odds_value if snapshots else None,
            }
        )

    # アラート履歴
    entry_ids = [e.id for e in entries]
    alerts = (
        AlertLog.query.filter(AlertLog.entry_id.in_(entry_ids))
        .order_by(AlertLog.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "race_detail.html",
        race=race,
        entries_data=entries_data,
        alerts=alerts,
    )


@app.route("/settings")
def settings():
    """アラート設定ページ"""
    rules = AlertRule.query.order_by(AlertRule.id).all()
    races = Race.query.order_by(Race.race_date.desc(), Race.race_number).all()
    return render_template("settings.html", rules=rules, races=races)


# =============================================================================
# API エンドポイント
# =============================================================================


@app.route("/api/races")
def api_races():
    """レース一覧API"""
    races = Race.query.filter_by(is_active=True).order_by(Race.race_number).all()
    return jsonify(
        [
            {
                "id": r.id,
                "race_id": r.race_id,
                "race_name": r.race_name,
                "venue": r.venue,
                "race_number": r.race_number,
                "post_time": r.post_time,
            }
            for r in races
        ]
    )


@app.route("/api/race/<int:race_id>/odds")
def api_race_odds(race_id):
    """レースのオッズ情報API(チャート用データ含む)"""
    race = Race.query.get_or_404(race_id)
    entries = RaceEntry.query.filter_by(race_id=race.id).order_by(
        RaceEntry.horse_number
    )

    result = []
    for entry in entries:
        snapshots = (
            OddsSnapshot.query.filter_by(entry_id=entry.id, odds_type="win")
            .order_by(OddsSnapshot.fetched_at)
            .all()
        )
        result.append(
            {
                "horse_number": entry.horse_number,
                "horse_name": entry.horse_name,
                "jockey": entry.jockey,
                "popularity": entry.popularity,
                "current_odds": snapshots[-1].odds_value if snapshots else None,
                "odds_history": [
                    {
                        "time": s.fetched_at.strftime("%H:%M:%S"),
                        "odds": s.odds_value,
                    }
                    for s in snapshots
                ],
            }
        )

    return jsonify(result)


@app.route("/api/alerts")
def api_alerts():
    """アラート一覧API"""
    limit = request.args.get("limit", 50, type=int)
    alerts = (
        AlertLog.query.order_by(AlertLog.created_at.desc()).limit(limit).all()
    )
    return jsonify(
        [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "message": a.message,
                "previous_odds": a.previous_odds,
                "current_odds": a.current_odds,
                "change_percent": a.change_percent,
                "change_absolute": a.change_absolute,
                "is_notified": a.is_notified,
                "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for a in alerts
        ]
    )


@app.route("/api/alerts/unread_count")
def api_alerts_unread_count():
    """未読アラート数API (ポーリング用)"""
    count = AlertLog.query.filter_by(is_notified=False).count()
    return jsonify({"count": count})


@app.route("/api/rules", methods=["GET"])
def api_get_rules():
    """アラートルール一覧取得API"""
    rules = AlertRule.query.order_by(AlertRule.id).all()
    return jsonify(
        [
            {
                "id": r.id,
                "name": r.name,
                "is_enabled": r.is_enabled,
                "change_threshold_percent": r.change_threshold_percent,
                "change_threshold_absolute": r.change_threshold_absolute,
                "direction": r.direction,
                "consecutive_drop_count": r.consecutive_drop_count,
                "notify_method": r.notify_method,
                "target_race_id": r.target_race_id,
                "target_entry_id": r.target_entry_id,
            }
            for r in rules
        ]
    )


@app.route("/api/rules", methods=["POST"])
def api_create_rule():
    """アラートルール作成API"""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "ルール名は必須です"}), 400

    rule = AlertRule(
        name=data["name"],
        is_enabled=data.get("is_enabled", True),
        change_threshold_percent=data.get("change_threshold_percent", 20.0),
        change_threshold_absolute=data.get("change_threshold_absolute", 5.0),
        direction=data.get("direction", "both"),
        consecutive_drop_count=data.get("consecutive_drop_count", 3),
        notify_method=data.get("notify_method", "both"),
        target_race_id=data.get("target_race_id"),
        target_entry_id=data.get("target_entry_id"),
    )
    db.session.add(rule)
    db.session.commit()

    return jsonify({"id": rule.id, "message": "ルールを作成しました"}), 201


@app.route("/api/rules/<int:rule_id>", methods=["PUT"])
def api_update_rule(rule_id):
    """アラートルール更新API"""
    rule = AlertRule.query.get_or_404(rule_id)
    data = request.get_json()

    if "name" in data:
        rule.name = data["name"]
    if "is_enabled" in data:
        rule.is_enabled = data["is_enabled"]
    if "change_threshold_percent" in data:
        rule.change_threshold_percent = data["change_threshold_percent"]
    if "change_threshold_absolute" in data:
        rule.change_threshold_absolute = data["change_threshold_absolute"]
    if "direction" in data:
        rule.direction = data["direction"]
    if "consecutive_drop_count" in data:
        rule.consecutive_drop_count = data["consecutive_drop_count"]
    if "notify_method" in data:
        rule.notify_method = data["notify_method"]

    db.session.commit()
    return jsonify({"message": "ルールを更新しました"})


@app.route("/api/rules/<int:rule_id>", methods=["DELETE"])
def api_delete_rule(rule_id):
    """アラートルール削除API"""
    rule = AlertRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "ルールを削除しました"})


@app.route("/api/race/<int:race_id>/toggle", methods=["POST"])
def api_toggle_race(race_id):
    """レースの監視ON/OFF切替API"""
    race = Race.query.get_or_404(race_id)
    race.is_active = not race.is_active
    db.session.commit()
    return jsonify(
        {"is_active": race.is_active, "message": f"監視を{'開始' if race.is_active else '停止'}しました"}
    )


# =============================================================================
# スケジューラ起動
# =============================================================================

scheduler = None


def start_scheduler(demo_mode=False):
    global scheduler
    if scheduler is not None:
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scrape_and_check,
        "interval",
        seconds=Config.SCRAPE_INTERVAL,
        args=[app, demo_mode],
        id="scrape_and_check",
        name="オッズ取得・変動チェック",
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "スケジューラを開始しました (間隔: %d秒, デモモード: %s)",
        Config.SCRAPE_INTERVAL,
        demo_mode,
    )


if __name__ == "__main__":
    demo_mode = os.environ.get("DEMO_MODE", "1") == "1"
    start_scheduler(demo_mode=demo_mode)
    logger.info("FMY - 競馬オッズ変動アラートアプリを起動します")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
