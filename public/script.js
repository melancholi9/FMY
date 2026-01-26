document.addEventListener('DOMContentLoaded', () => {
  const searchForm = document.getElementById('searchForm');
  const janCodeInput = document.getElementById('janCode');
  const searchBtn = document.getElementById('searchBtn');
  const btnText = searchBtn.querySelector('.btn-text');
  const btnLoading = searchBtn.querySelector('.btn-loading');
  const resultsSection = document.getElementById('results');
  const resultCount = document.getElementById('resultCount');
  const demoNotice = document.getElementById('demoNotice');
  const resultsList = document.getElementById('resultsList');
  const errorSection = document.getElementById('error');
  const errorMessage = document.getElementById('errorMessage');
  const apiStatus = document.getElementById('apiStatus');

  // API状態をチェック
  checkApiStatus();

  // 数字のみ入力可能にする
  janCodeInput.addEventListener('input', (e) => {
    e.target.value = e.target.value.replace(/[^0-9]/g, '');
  });

  // 検索フォーム送信
  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const janCode = janCodeInput.value.trim();

    if (!janCode) {
      showError('JANコードを入力してください');
      return;
    }

    if (!/^(\d{8}|\d{13})$/.test(janCode)) {
      showError('JANコードは8桁または13桁の数字で入力してください');
      return;
    }

    await searchProducts(janCode);
  });

  // 商品検索
  async function searchProducts(janCode) {
    setLoading(true);
    hideError();
    hideResults();

    try {
      const response = await fetch(`/api/search?jan=${encodeURIComponent(janCode)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '検索中にエラーが発生しました');
      }

      displayResults(data);
    } catch (error) {
      showError(error.message);
    } finally {
      setLoading(false);
    }
  }

  // 検索結果を表示
  function displayResults(data) {
    resultsSection.style.display = 'block';
    resultCount.textContent = `${data.count}件の商品が見つかりました`;

    // デモモード表示
    if (data.isDemo) {
      demoNotice.style.display = 'block';
    } else {
      demoNotice.style.display = 'none';
    }

    // 結果リストをクリア
    resultsList.innerHTML = '';

    if (data.results.length === 0) {
      resultsList.innerHTML = '<p class="no-results">商品が見つかりませんでした</p>';
      return;
    }

    // 各商品を表示
    data.results.forEach(item => {
      const itemElement = createResultItem(item);
      resultsList.appendChild(itemElement);
    });
  }

  // 商品アイテム要素を作成
  function createResultItem(item) {
    const div = document.createElement('div');
    div.className = `result-item${item.isCheapest ? ' cheapest' : ''}`;

    // ソースに応じたクラス
    let sourceClass = '';
    if (item.source.includes('楽天')) sourceClass = 'rakuten';
    else if (item.source.includes('Yahoo')) sourceClass = 'yahoo';
    else if (item.source.includes('Amazon')) sourceClass = 'amazon';

    // 在庫状況のクラス
    const availabilityClass = item.availability === '在庫なし' ? 'out-of-stock' : '';

    div.innerHTML = `
      <img src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(item.name)}" class="item-image" onerror="this.src='https://via.placeholder.com/100?text=No+Image'">
      <div class="item-info">
        <span class="item-source ${sourceClass}">${escapeHtml(item.source)}</span>
        <p class="item-name">${escapeHtml(item.name)}</p>
        <p class="item-shop">${escapeHtml(item.shopName)}</p>
        <p class="item-availability ${availabilityClass}">${escapeHtml(item.availability)}</p>
      </div>
      <div class="item-price-section">
        <span class="item-price">&yen;${item.price.toLocaleString()}</span>
        <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="item-link">商品ページへ</a>
      </div>
    `;

    return div;
  }

  // API状態をチェック
  async function checkApiStatus() {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();

      const statuses = [];
      if (data.hasRakutenApi) statuses.push('楽天API: 有効');
      if (data.hasYahooApi) statuses.push('Yahoo!API: 有効');

      if (statuses.length === 0) {
        apiStatus.textContent = 'デモモードで動作中（APIキー未設定）';
      } else {
        apiStatus.textContent = statuses.join(' | ');
      }
    } catch (error) {
      apiStatus.textContent = 'API状態を確認できません';
    }
  }

  // ローディング状態を設定
  function setLoading(isLoading) {
    searchBtn.disabled = isLoading;
    btnText.style.display = isLoading ? 'none' : 'inline';
    btnLoading.style.display = isLoading ? 'inline' : 'none';
  }

  // エラーを表示
  function showError(message) {
    errorSection.style.display = 'block';
    errorMessage.textContent = message;
    resultsSection.style.display = 'none';
  }

  // エラーを非表示
  function hideError() {
    errorSection.style.display = 'none';
  }

  // 結果を非表示
  function hideResults() {
    resultsSection.style.display = 'none';
  }

  // HTMLエスケープ
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
