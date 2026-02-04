/**
 * FMY - 競馬オッズ変動アラート メインJS
 */

(function () {
    'use strict';

    // 未読アラート数をポーリングで取得
    function pollUnreadAlerts() {
        fetch('/api/alerts/unread_count')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var badge = document.getElementById('alert-badge');
                if (!badge) return;

                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            })
            .catch(function () { /* ignore */ });
    }

    // 15秒ごとにポーリング
    setInterval(pollUnreadAlerts, 15000);
    pollUnreadAlerts();
})();
