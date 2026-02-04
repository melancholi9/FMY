"""
オッズ変動検知エンジン

オッズの変動を分析し、アラート条件に合致した場合にアラートを生成する。
"""

import logging
from datetime import datetime

from models.database import db, OddsSnapshot, AlertRule, AlertLog, RaceEntry, Race

logger = logging.getLogger(__name__)


class OddsChangeDetector:
    """オッズ変動を検知してアラートを生成するエンジン"""

    def check_all_entries(self):
        """
        全ての監視対象エントリーについてオッズ変動をチェックし、
        アラート条件に合致した場合にアラートログを生成する。

        Returns:
            list[AlertLog]: 新たに生成されたアラートのリスト
        """
        alerts = []

        # 有効なアラートルールを取得
        rules = AlertRule.query.filter_by(is_enabled=True).all()
        if not rules:
            logger.debug("有効なアラートルールがありません")
            return alerts

        # アクティブなレースのエントリーを取得
        active_races = Race.query.filter_by(is_active=True).all()

        for race in active_races:
            entries = RaceEntry.query.filter_by(race_id=race.id).all()
            for entry in entries:
                entry_alerts = self._check_entry(entry, rules)
                alerts.extend(entry_alerts)

        if alerts:
            db.session.add_all(alerts)
            db.session.commit()
            logger.info("%d件のアラートを検知しました", len(alerts))

        return alerts

    def _check_entry(self, entry, rules):
        """
        特定のエントリーについてオッズ変動をチェックする。

        Args:
            entry: RaceEntry
            rules: list[AlertRule] 有効なアラートルール

        Returns:
            list[AlertLog]: 検知されたアラートのリスト
        """
        alerts = []

        # 最新2つのスナップショットを取得
        recent_snapshots = (
            OddsSnapshot.query.filter_by(entry_id=entry.id, odds_type="win")
            .order_by(OddsSnapshot.fetched_at.desc())
            .limit(10)
            .all()
        )

        if len(recent_snapshots) < 2:
            return alerts

        current = recent_snapshots[0]
        previous = recent_snapshots[1]

        for rule in rules:
            # ルールのターゲットフィルタ
            if rule.target_race_id and rule.target_race_id != entry.race_id:
                continue
            if rule.target_entry_id and rule.target_entry_id != entry.id:
                continue

            # 変動率チェック
            percent_alert = self._check_percent_change(
                entry, current, previous, rule
            )
            if percent_alert:
                alerts.append(percent_alert)

            # 変動量チェック
            absolute_alert = self._check_absolute_change(
                entry, current, previous, rule
            )
            if absolute_alert:
                alerts.append(absolute_alert)

            # 連続下落チェック
            consecutive_alert = self._check_consecutive_drop(
                entry, recent_snapshots, rule
            )
            if consecutive_alert:
                alerts.append(consecutive_alert)

        return alerts

    def _check_percent_change(self, entry, current, previous, rule):
        """変動率に基づくアラートチェック"""
        if previous.odds_value == 0:
            return None

        change_percent = (
            (current.odds_value - previous.odds_value) / previous.odds_value * 100
        )

        # 方向フィルタ
        if rule.direction == "down" and change_percent >= 0:
            return None
        if rule.direction == "up" and change_percent <= 0:
            return None

        if abs(change_percent) >= rule.change_threshold_percent:
            direction = "下落" if change_percent < 0 else "上昇"
            race = db.session.get(Race, entry.race_id)
            race_info = f"{race.venue}{race.race_number}R" if race else ""

            message = (
                f"【オッズ{direction}アラート】\n"
                f"{race_info} {entry.horse_number}番 {entry.horse_name}\n"
                f"オッズ: {previous.odds_value:.1f} → {current.odds_value:.1f} "
                f"({change_percent:+.1f}%)"
            )

            return AlertLog(
                alert_rule_id=rule.id,
                entry_id=entry.id,
                alert_type="percent_change",
                previous_odds=previous.odds_value,
                current_odds=current.odds_value,
                change_percent=change_percent,
                change_absolute=current.odds_value - previous.odds_value,
                message=message,
            )
        return None

    def _check_absolute_change(self, entry, current, previous, rule):
        """変動量(絶対値)に基づくアラートチェック"""
        change_absolute = current.odds_value - previous.odds_value

        # 方向フィルタ
        if rule.direction == "down" and change_absolute >= 0:
            return None
        if rule.direction == "up" and change_absolute <= 0:
            return None

        if abs(change_absolute) >= rule.change_threshold_absolute:
            direction = "下落" if change_absolute < 0 else "上昇"
            race = db.session.get(Race, entry.race_id)
            race_info = f"{race.venue}{race.race_number}R" if race else ""

            message = (
                f"【オッズ急変アラート】\n"
                f"{race_info} {entry.horse_number}番 {entry.horse_name}\n"
                f"オッズ: {previous.odds_value:.1f} → {current.odds_value:.1f} "
                f"({change_absolute:+.1f}pt)"
            )

            return AlertLog(
                alert_rule_id=rule.id,
                entry_id=entry.id,
                alert_type="absolute_change",
                previous_odds=previous.odds_value,
                current_odds=current.odds_value,
                change_percent=(change_absolute / previous.odds_value * 100)
                if previous.odds_value
                else 0,
                change_absolute=change_absolute,
                message=message,
            )
        return None

    def _check_consecutive_drop(self, entry, snapshots, rule):
        """連続下落に基づくアラートチェック"""
        required_drops = rule.consecutive_drop_count
        if len(snapshots) < required_drops + 1:
            return None

        # 最新N+1個のスナップショットで連続下落しているかチェック
        consecutive = 0
        for i in range(len(snapshots) - 1):
            if i >= required_drops:
                break
            if snapshots[i].odds_value < snapshots[i + 1].odds_value:
                consecutive += 1
            else:
                break

        if consecutive >= required_drops:
            first_odds = snapshots[required_drops].odds_value
            current_odds = snapshots[0].odds_value
            total_change = current_odds - first_odds
            race = db.session.get(Race, entry.race_id)
            race_info = f"{race.venue}{race.race_number}R" if race else ""

            message = (
                f"【連続下落アラート】\n"
                f"{race_info} {entry.horse_number}番 {entry.horse_name}\n"
                f"{required_drops}回連続でオッズが下落しています\n"
                f"オッズ推移: {first_odds:.1f} → {current_odds:.1f} "
                f"({total_change:+.1f}pt)"
            )

            return AlertLog(
                alert_rule_id=rule.id,
                entry_id=entry.id,
                alert_type="consecutive_drop",
                previous_odds=first_odds,
                current_odds=current_odds,
                change_percent=(total_change / first_odds * 100)
                if first_odds
                else 0,
                change_absolute=total_change,
                message=message,
            )
        return None
