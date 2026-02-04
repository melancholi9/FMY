"""
JRAオッズスクレイパー

JRA公式サイトからオッズデータを取得する。
発売中のレースの単勝・複勝オッズを定期的にスクレイピングする。
"""

import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import Config

logger = logging.getLogger(__name__)

# JRA公式サイトのベースURL
JRA_BASE_URL = "https://www.jra.go.jp"
JRA_ODDS_URL = f"{JRA_BASE_URL}/JRADB/accessO.html"


class JRAOddsScraper:
    """JRA公式サイトからオッズを取得するスクレイパー"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": Config.USER_AGENT,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
        )

    def fetch_race_list(self, date=None):
        """
        指定日のレース一覧を取得する。

        Returns:
            list[dict]: レース情報のリスト
            [
                {
                    "race_id": "202501010101",
                    "race_name": "3歳新馬",
                    "venue": "中山",
                    "race_number": 1,
                    "post_time": "10:00",
                    ...
                }
            ]
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y%m%d")

        try:
            # JRAレースリストページにアクセス
            url = f"{JRA_BASE_URL}/keiba/calendar2.html"
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                logger.error("レース一覧の取得に失敗: status=%d", resp.status_code)
                return []

            races = self._parse_race_list(resp.text, date_str)
            logger.info("%d件のレースを取得しました (日付: %s)", len(races), date_str)
            return races

        except requests.RequestException as e:
            logger.error("レース一覧の取得中にエラーが発生: %s", e)
            return []

    def fetch_win_odds(self, race_id):
        """
        指定レースの単勝オッズを取得する。

        Args:
            race_id: レースID

        Returns:
            list[dict]: オッズ情報のリスト
            [
                {
                    "horse_number": 1,
                    "horse_name": "ドウデュース",
                    "odds": 3.5,
                    "popularity": 1,
                }
            ]
        """
        try:
            # JRAのオッズページURLを構築
            url = self._build_odds_url(race_id, "win")
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                logger.error(
                    "単勝オッズの取得に失敗: race_id=%s, status=%d",
                    race_id,
                    resp.status_code,
                )
                return []

            odds_list = self._parse_win_odds(resp.text)
            logger.info(
                "race_id=%s の単勝オッズを%d頭分取得しました",
                race_id,
                len(odds_list),
            )
            return odds_list

        except requests.RequestException as e:
            logger.error("単勝オッズの取得中にエラーが発生: race_id=%s, %s", race_id, e)
            return []

    def fetch_place_odds(self, race_id):
        """
        指定レースの複勝オッズを取得する。

        Returns:
            list[dict]: 複勝オッズ情報のリスト
            [
                {
                    "horse_number": 1,
                    "horse_name": "ドウデュース",
                    "odds_min": 1.2,
                    "odds_max": 1.8,
                }
            ]
        """
        try:
            url = self._build_odds_url(race_id, "place")
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"

            if resp.status_code != 200:
                logger.error(
                    "複勝オッズの取得に失敗: race_id=%s, status=%d",
                    race_id,
                    resp.status_code,
                )
                return []

            odds_list = self._parse_place_odds(resp.text)
            logger.info(
                "race_id=%s の複勝オッズを%d頭分取得しました",
                race_id,
                len(odds_list),
            )
            return odds_list

        except requests.RequestException as e:
            logger.error("複勝オッズの取得中にエラーが発生: race_id=%s, %s", race_id, e)
            return []

    def _build_odds_url(self, race_id, odds_type):
        """オッズページのURLを構築する"""
        # JRAのオッズページURL形式
        # 実際のURLは JRA サイトの構造に合わせて調整が必要
        if odds_type == "win":
            return f"{JRA_BASE_URL}/JRADB/accessO.html?CESSION={race_id}&ty=0"
        else:
            return f"{JRA_BASE_URL}/JRADB/accessO.html?CESSION={race_id}&ty=1"

    def _parse_race_list(self, html, date_str):
        """レース一覧HTMLをパースする"""
        soup = BeautifulSoup(html, "lxml")
        races = []

        # JRAサイトの構造に基づいてパース
        race_tables = soup.select("table.race-table tr, div.race-list li")

        for item in race_tables:
            try:
                race_info = self._extract_race_info(item, date_str)
                if race_info:
                    races.append(race_info)
            except (ValueError, AttributeError) as e:
                logger.debug("レース情報の抽出をスキップ: %s", e)
                continue

        return races

    def _extract_race_info(self, element, date_str):
        """HTML要素からレース情報を抽出する"""
        # テキストからレース情報を抽出
        text = element.get_text(strip=True)
        if not text:
            return None

        # リンクからレースIDを取得
        link = element.find("a")
        if not link or not link.get("href"):
            return None

        href = link["href"]
        race_id_match = re.search(r"CESSION=(\d+)", href)
        if not race_id_match:
            return None

        race_id = race_id_match.group(1)

        # レース番号の抽出
        race_num_match = re.search(r"(\d+)R", text)
        race_number = int(race_num_match.group(1)) if race_num_match else 0

        # 競馬場名の抽出
        venue_names = ["東京", "中山", "阪神", "京都", "中京", "小倉", "新潟", "福島", "札幌", "函館"]
        venue = ""
        for v in venue_names:
            if v in text:
                venue = v
                break

        return {
            "race_id": race_id,
            "race_name": text[:50],
            "venue": venue,
            "race_number": race_number,
            "race_date": date_str,
            "post_time": "",
        }

    def _parse_win_odds(self, html):
        """単勝オッズHTMLをパースする"""
        soup = BeautifulSoup(html, "lxml")
        odds_list = []

        # オッズテーブルの行を取得
        rows = soup.select("table tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            try:
                horse_number = int(cols[0].get_text(strip=True))
                horse_name = cols[1].get_text(strip=True)
                odds_text = cols[2].get_text(strip=True).replace(",", "")

                if not odds_text or odds_text == "---":
                    continue

                odds_value = float(odds_text)

                # 人気順(存在する場合)
                popularity = None
                if len(cols) > 3:
                    pop_text = cols[3].get_text(strip=True)
                    if pop_text.isdigit():
                        popularity = int(pop_text)

                odds_list.append(
                    {
                        "horse_number": horse_number,
                        "horse_name": horse_name,
                        "odds": odds_value,
                        "popularity": popularity,
                    }
                )
            except (ValueError, IndexError):
                continue

        return odds_list

    def _parse_place_odds(self, html):
        """複勝オッズHTMLをパースする"""
        soup = BeautifulSoup(html, "lxml")
        odds_list = []

        rows = soup.select("table tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            try:
                horse_number = int(cols[0].get_text(strip=True))
                horse_name = cols[1].get_text(strip=True)
                odds_min_text = cols[2].get_text(strip=True).replace(",", "")
                odds_max_text = cols[3].get_text(strip=True).replace(",", "")

                if not odds_min_text or odds_min_text == "---":
                    continue

                odds_list.append(
                    {
                        "horse_number": horse_number,
                        "horse_name": horse_name,
                        "odds_min": float(odds_min_text),
                        "odds_max": float(odds_max_text),
                    }
                )
            except (ValueError, IndexError):
                continue

        return odds_list


class DemoOddsScraper:
    """
    デモ用スクレイパー。
    実際のスクレイピングの代わりに、模擬データを生成する。
    テストや動作確認に使用。
    """

    def __init__(self):
        import random

        self.random = random
        self._base_odds = {}

    def fetch_race_list(self, date=None):
        """デモ用レース一覧を返す"""
        if date is None:
            date = datetime.now()

        return [
            {
                "race_id": f"DEMO{date.strftime('%Y%m%d')}01",
                "race_name": "デモレース 第1レース 3歳新馬",
                "venue": "東京",
                "race_number": 1,
                "race_date": date.strftime("%Y%m%d"),
                "post_time": "10:00",
                "race_type": "芝",
                "distance": 1600,
            },
            {
                "race_id": f"DEMO{date.strftime('%Y%m%d')}11",
                "race_name": "デモレース 第11レース GI天皇賞",
                "venue": "東京",
                "race_number": 11,
                "race_date": date.strftime("%Y%m%d"),
                "post_time": "15:40",
                "race_type": "芝",
                "distance": 2000,
            },
        ]

    def fetch_win_odds(self, race_id):
        """デモ用単勝オッズを返す(呼ぶたびに少しずつ変動する)"""
        horses = self._get_demo_horses(race_id)
        result = []

        for i, horse in enumerate(horses):
            key = f"{race_id}_{horse['number']}"
            if key not in self._base_odds:
                self._base_odds[key] = horse["base_odds"]

            # ランダムに変動させる
            current = self._base_odds[key]
            change = self.random.uniform(-0.15, 0.10) * current
            new_odds = max(1.0, round(current + change, 1))
            self._base_odds[key] = new_odds

            # 低確率で大きな変動を発生させる(アラートテスト用)
            if self.random.random() < 0.05:
                drop = self.random.uniform(0.2, 0.4) * new_odds
                new_odds = max(1.0, round(new_odds - drop, 1))
                self._base_odds[key] = new_odds
                logger.info("【デモ】大幅な変動を発生: %s オッズ %.1f", horse["name"], new_odds)

            result.append(
                {
                    "horse_number": horse["number"],
                    "horse_name": horse["name"],
                    "odds": new_odds,
                    "popularity": i + 1,
                }
            )

        # 人気順でソート
        result.sort(key=lambda x: x["odds"])
        for i, r in enumerate(result):
            r["popularity"] = i + 1

        return result

    def _get_demo_horses(self, race_id):
        """デモ用出走馬リストを返す"""
        if race_id.endswith("11"):
            return [
                {"number": 1, "name": "サンプルホース", "base_odds": 3.5},
                {"number": 2, "name": "テストランナー", "base_odds": 5.2},
                {"number": 3, "name": "デモスプリンター", "base_odds": 8.0},
                {"number": 4, "name": "モックステイヤー", "base_odds": 12.5},
                {"number": 5, "name": "トライアルキング", "base_odds": 15.0},
                {"number": 6, "name": "ダミーダッシュ", "base_odds": 25.0},
                {"number": 7, "name": "フェイクフライト", "base_odds": 40.0},
                {"number": 8, "name": "シミュレーター", "base_odds": 55.0},
            ]
        else:
            return [
                {"number": 1, "name": "ファーストトライ", "base_odds": 2.8},
                {"number": 2, "name": "セカンドチャンス", "base_odds": 4.0},
                {"number": 3, "name": "サードタイム", "base_odds": 6.5},
                {"number": 4, "name": "フォースウィン", "base_odds": 10.0},
                {"number": 5, "name": "フィフスエレメント", "base_odds": 18.0},
                {"number": 6, "name": "シックスセンス", "base_odds": 30.0},
            ]
