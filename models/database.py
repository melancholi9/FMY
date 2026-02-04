from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Race(db.Model):
    """レース情報"""

    __tablename__ = "races"

    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    race_name = db.Column(db.String(100), nullable=False)
    race_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(20), nullable=False)  # 競馬場名
    race_number = db.Column(db.Integer, nullable=False)  # 第N レース
    post_time = db.Column(db.String(10))  # 発走時刻
    race_type = db.Column(db.String(20))  # 芝/ダート/障害
    distance = db.Column(db.Integer)  # 距離(m)
    is_active = db.Column(db.Boolean, default=True)  # 監視中かどうか
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship("RaceEntry", backref="race", lazy="dynamic")

    def __repr__(self):
        return f"<Race {self.race_id}: {self.race_name}>"


class RaceEntry(db.Model):
    """出走馬情報"""

    __tablename__ = "race_entries"

    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey("races.id"), nullable=False)
    horse_number = db.Column(db.Integer, nullable=False)  # 馬番
    horse_name = db.Column(db.String(50), nullable=False)
    jockey = db.Column(db.String(50))  # 騎手名
    trainer = db.Column(db.String(50))  # 調教師名
    popularity = db.Column(db.Integer)  # 人気順

    odds_snapshots = db.relationship(
        "OddsSnapshot", backref="entry", lazy="dynamic", order_by="OddsSnapshot.fetched_at"
    )

    __table_args__ = (
        db.UniqueConstraint("race_id", "horse_number", name="uq_race_horse"),
    )

    def __repr__(self):
        return f"<RaceEntry {self.horse_number}: {self.horse_name}>"


class OddsSnapshot(db.Model):
    """オッズのスナップショット(定期取得した時点のオッズ)"""

    __tablename__ = "odds_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("race_entries.id"), nullable=False)
    odds_type = db.Column(db.String(10), nullable=False, default="win")  # win/place
    odds_value = db.Column(db.Float, nullable=False)
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (db.Index("ix_entry_type_fetched", "entry_id", "odds_type", "fetched_at"),)

    def __repr__(self):
        return f"<OddsSnapshot entry={self.entry_id} odds={self.odds_value} at {self.fetched_at}>"


class AlertRule(db.Model):
    """アラートルール設定"""

    __tablename__ = "alert_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)

    # 対象レース (NULLなら全レース対象)
    target_race_id = db.Column(db.Integer, db.ForeignKey("races.id"), nullable=True)

    # 対象馬 (NULLなら全馬対象)
    target_entry_id = db.Column(db.Integer, db.ForeignKey("race_entries.id"), nullable=True)

    # 変動率閾値 (%) - この%以上変動したらアラート
    change_threshold_percent = db.Column(db.Float, default=20.0)

    # 変動量閾値 (絶対値) - このポイント以上変動したらアラート
    change_threshold_absolute = db.Column(db.Float, default=5.0)

    # 方向: both(両方), down(下落のみ), up(上昇のみ)
    direction = db.Column(db.String(10), default="both")

    # 連続下落検知回数
    consecutive_drop_count = db.Column(db.Integer, default=3)

    # 通知方法: line, web, both
    notify_method = db.Column(db.String(10), default="both")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    target_race = db.relationship("Race", foreign_keys=[target_race_id])
    target_entry = db.relationship("RaceEntry", foreign_keys=[target_entry_id])

    def __repr__(self):
        return f"<AlertRule {self.id}: {self.name}>"


class AlertLog(db.Model):
    """アラート発生ログ"""

    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True)
    alert_rule_id = db.Column(db.Integer, db.ForeignKey("alert_rules.id"), nullable=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("race_entries.id"), nullable=False)

    alert_type = db.Column(db.String(30), nullable=False)
    # "percent_change", "absolute_change", "consecutive_drop"

    previous_odds = db.Column(db.Float, nullable=False)
    current_odds = db.Column(db.Float, nullable=False)
    change_percent = db.Column(db.Float)
    change_absolute = db.Column(db.Float)
    message = db.Column(db.Text, nullable=False)
    is_notified = db.Column(db.Boolean, default=False)  # 通知済みか
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    alert_rule = db.relationship("AlertRule", backref="logs")
    entry = db.relationship("RaceEntry", backref="alert_logs")

    def __repr__(self):
        return f"<AlertLog {self.id}: {self.alert_type}>"
