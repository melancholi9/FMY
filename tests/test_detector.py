"""
オッズ変動検知エンジンのテスト
"""

import unittest
from datetime import datetime, timedelta

from app import create_app
from models.database import (
    AlertLog,
    AlertRule,
    OddsSnapshot,
    Race,
    RaceEntry,
    db,
)
from alerts.detector import OddsChangeDetector


class TestOddsChangeDetector(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # create_appが作成するデフォルトルールを削除
        AlertRule.query.delete()
        db.session.commit()

        # テスト用データの作成
        self.race = Race(
            race_id="TEST20260101",
            race_name="テストレース",
            race_date=datetime(2026, 1, 1).date(),
            venue="東京",
            race_number=1,
            is_active=True,
        )
        db.session.add(self.race)
        db.session.flush()

        self.entry = RaceEntry(
            race_id=self.race.id,
            horse_number=1,
            horse_name="テストホース",
        )
        db.session.add(self.entry)
        db.session.flush()

        self.rule = AlertRule(
            name="テストルール",
            is_enabled=True,
            change_threshold_percent=20.0,
            change_threshold_absolute=5.0,
            consecutive_drop_count=3,
            direction="both",
        )
        db.session.add(self.rule)
        db.session.commit()

        self.detector = OddsChangeDetector()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _add_snapshot(self, odds_value, minutes_ago=0):
        """テスト用のスナップショットを追加"""
        snapshot = OddsSnapshot(
            entry_id=self.entry.id,
            odds_type="win",
            odds_value=odds_value,
            fetched_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
        )
        db.session.add(snapshot)
        db.session.commit()
        return snapshot

    def test_no_alert_with_single_snapshot(self):
        """スナップショットが1つしかない場合はアラートなし"""
        self._add_snapshot(10.0)
        alerts = self.detector.check_all_entries()
        self.assertEqual(len(alerts), 0)

    def test_no_alert_with_small_change(self):
        """小さな変動ではアラートが出ない"""
        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(10.5, minutes_ago=0)
        alerts = self.detector.check_all_entries()
        self.assertEqual(len(alerts), 0)

    def test_percent_change_alert_on_drop(self):
        """20%以上の下落でアラートが出る"""
        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(7.5, minutes_ago=0)  # -25%
        alerts = self.detector.check_all_entries()

        percent_alerts = [a for a in alerts if a.alert_type == "percent_change"]
        self.assertGreater(len(percent_alerts), 0)
        self.assertLess(percent_alerts[0].change_percent, 0)

    def test_percent_change_alert_on_rise(self):
        """20%以上の上昇でもアラートが出る(direction=both)"""
        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(13.0, minutes_ago=0)  # +30%
        alerts = self.detector.check_all_entries()

        percent_alerts = [a for a in alerts if a.alert_type == "percent_change"]
        self.assertGreater(len(percent_alerts), 0)
        self.assertGreater(percent_alerts[0].change_percent, 0)

    def test_absolute_change_alert(self):
        """5pt以上の変動でアラートが出る"""
        self._add_snapshot(20.0, minutes_ago=2)
        self._add_snapshot(14.0, minutes_ago=0)  # -6pt
        alerts = self.detector.check_all_entries()

        abs_alerts = [a for a in alerts if a.alert_type == "absolute_change"]
        self.assertGreater(len(abs_alerts), 0)

    def test_consecutive_drop_alert(self):
        """3回連続下落でアラートが出る"""
        self._add_snapshot(20.0, minutes_ago=4)
        self._add_snapshot(18.0, minutes_ago=3)
        self._add_snapshot(16.0, minutes_ago=2)
        self._add_snapshot(14.0, minutes_ago=1)
        alerts = self.detector.check_all_entries()

        consec_alerts = [a for a in alerts if a.alert_type == "consecutive_drop"]
        self.assertGreater(len(consec_alerts), 0)

    def test_no_consecutive_alert_with_rise(self):
        """途中で上昇があると連続下落アラートは出ない"""
        self._add_snapshot(20.0, minutes_ago=4)
        self._add_snapshot(18.0, minutes_ago=3)
        self._add_snapshot(19.0, minutes_ago=2)  # 上昇
        self._add_snapshot(17.0, minutes_ago=1)
        alerts = self.detector.check_all_entries()

        consec_alerts = [a for a in alerts if a.alert_type == "consecutive_drop"]
        self.assertEqual(len(consec_alerts), 0)

    def test_direction_filter_down_only(self):
        """direction=downの場合、上昇ではアラートが出ない"""
        self.rule.direction = "down"
        db.session.commit()

        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(15.0, minutes_ago=0)  # +50% 上昇
        alerts = self.detector.check_all_entries()

        self.assertEqual(len(alerts), 0)

    def test_direction_filter_up_only(self):
        """direction=upの場合、下落ではアラートが出ない"""
        self.rule.direction = "up"
        db.session.commit()

        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(5.0, minutes_ago=0)  # -50% 下落
        alerts = self.detector.check_all_entries()

        self.assertEqual(len(alerts), 0)

    def test_disabled_rule_ignored(self):
        """無効化されたルールは無視される"""
        self.rule.is_enabled = False
        db.session.commit()

        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(5.0, minutes_ago=0)  # 大幅下落
        alerts = self.detector.check_all_entries()

        self.assertEqual(len(alerts), 0)

    def test_alert_message_format(self):
        """アラートメッセージに必要な情報が含まれている"""
        self._add_snapshot(10.0, minutes_ago=2)
        self._add_snapshot(7.0, minutes_ago=0)  # -30%
        alerts = self.detector.check_all_entries()

        self.assertGreater(len(alerts), 0)
        msg = alerts[0].message
        self.assertIn("テストホース", msg)
        self.assertIn("10.0", msg)
        self.assertIn("7.0", msg)


class TestDemoScraper(unittest.TestCase):
    def test_fetch_race_list(self):
        """デモスクレイパーがレース一覧を返す"""
        from scraper.odds_scraper import DemoOddsScraper

        scraper = DemoOddsScraper()
        races = scraper.fetch_race_list()
        self.assertGreater(len(races), 0)
        self.assertIn("race_id", races[0])
        self.assertIn("venue", races[0])

    def test_fetch_win_odds(self):
        """デモスクレイパーがオッズを返す"""
        from scraper.odds_scraper import DemoOddsScraper

        scraper = DemoOddsScraper()
        races = scraper.fetch_race_list()
        odds = scraper.fetch_win_odds(races[0]["race_id"])
        self.assertGreater(len(odds), 0)
        self.assertIn("horse_number", odds[0])
        self.assertIn("odds", odds[0])
        self.assertIsInstance(odds[0]["odds"], float)

    def test_odds_vary_between_calls(self):
        """デモスクレイパーのオッズが呼び出しごとに変動する"""
        from scraper.odds_scraper import DemoOddsScraper

        scraper = DemoOddsScraper()
        races = scraper.fetch_race_list()
        race_id = races[0]["race_id"]

        odds1 = {o["horse_number"]: o["odds"] for o in scraper.fetch_win_odds(race_id)}
        # 複数回呼んでいずれかの回で変動があることを確認
        changed = False
        for _ in range(10):
            odds2 = {o["horse_number"]: o["odds"] for o in scraper.fetch_win_odds(race_id)}
            if odds1 != odds2:
                changed = True
                break
        self.assertTrue(changed, "10回呼んでもオッズが変わらなかった")


if __name__ == "__main__":
    unittest.main()
