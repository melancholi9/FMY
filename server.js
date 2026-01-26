require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// 楽天市場APIで商品検索
async function searchRakuten(janCode) {
  const appId = process.env.RAKUTEN_APP_ID;
  if (!appId) {
    console.log('楽天APIキーが設定されていません');
    return [];
  }

  try {
    const response = await axios.get('https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601', {
      params: {
        applicationId: appId,
        keyword: janCode,
        hits: 10,
        sort: '+itemPrice'
      }
    });

    if (response.data.Items) {
      return response.data.Items.map(item => ({
        source: '楽天市場',
        name: item.Item.itemName,
        price: item.Item.itemPrice,
        url: item.Item.itemUrl,
        imageUrl: item.Item.mediumImageUrls[0]?.imageUrl || '',
        shopName: item.Item.shopName,
        availability: item.Item.availability === 1 ? '在庫あり' : '要確認'
      }));
    }
    return [];
  } catch (error) {
    console.error('楽天API エラー:', error.message);
    return [];
  }
}

// Yahoo!ショッピングAPIで商品検索
async function searchYahoo(janCode) {
  const appId = process.env.YAHOO_APP_ID;
  if (!appId) {
    console.log('Yahoo!APIキーが設定されていません');
    return [];
  }

  try {
    const response = await axios.get('https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch', {
      params: {
        appid: appId,
        jan_code: janCode,
        results: 10,
        sort: '+price'
      }
    });

    if (response.data.hits) {
      return response.data.hits.map(item => ({
        source: 'Yahoo!ショッピング',
        name: item.name,
        price: item.price,
        url: item.url,
        imageUrl: item.image?.medium || '',
        shopName: item.seller?.name || '',
        availability: item.inStock ? '在庫あり' : '在庫なし'
      }));
    }
    return [];
  } catch (error) {
    console.error('Yahoo!API エラー:', error.message);
    return [];
  }
}

// デモ用のモックデータ（APIキーがない場合のテスト用）
function getMockData(janCode) {
  return [
    {
      source: '楽天市場',
      name: `サンプル商品 (JAN: ${janCode})`,
      price: 2980,
      url: 'https://www.rakuten.co.jp/',
      imageUrl: 'https://via.placeholder.com/150',
      shopName: 'サンプルショップA',
      availability: '在庫あり'
    },
    {
      source: 'Yahoo!ショッピング',
      name: `サンプル商品 (JAN: ${janCode})`,
      price: 2780,
      url: 'https://shopping.yahoo.co.jp/',
      imageUrl: 'https://via.placeholder.com/150',
      shopName: 'サンプルショップB',
      availability: '在庫あり'
    },
    {
      source: 'Amazon',
      name: `サンプル商品 (JAN: ${janCode})`,
      price: 3200,
      url: 'https://www.amazon.co.jp/',
      imageUrl: 'https://via.placeholder.com/150',
      shopName: 'Amazon.co.jp',
      availability: '在庫あり'
    }
  ];
}

// JANコードの形式チェック（8桁または13桁の数字）
function isValidJanCode(code) {
  return /^(\d{8}|\d{13})$/.test(code);
}

// 価格検索API
app.get('/api/search', async (req, res) => {
  const { jan } = req.query;

  if (!jan) {
    return res.status(400).json({ error: 'JANコードを入力してください' });
  }

  if (!isValidJanCode(jan)) {
    return res.status(400).json({ error: 'JANコードは8桁または13桁の数字で入力してください' });
  }

  try {
    // APIキーが設定されているかチェック
    const hasApiKeys = process.env.RAKUTEN_APP_ID || process.env.YAHOO_APP_ID;

    let results = [];

    if (hasApiKeys) {
      // 並列でAPI呼び出し
      const [rakutenResults, yahooResults] = await Promise.all([
        searchRakuten(jan),
        searchYahoo(jan)
      ]);
      results = [...rakutenResults, ...yahooResults];
    }

    // 結果がない場合はデモデータを返す
    if (results.length === 0) {
      results = getMockData(jan);
      results.isDemo = true;
    }

    // 価格でソート（安い順）
    results.sort((a, b) => a.price - b.price);

    // 最安値を特定
    if (results.length > 0) {
      const minPrice = results[0].price;
      results = results.map(item => ({
        ...item,
        isCheapest: item.price === minPrice
      }));
    }

    res.json({
      janCode: jan,
      count: results.length,
      isDemo: !hasApiKeys,
      results: results
    });
  } catch (error) {
    console.error('検索エラー:', error);
    res.status(500).json({ error: '検索中にエラーが発生しました' });
  }
});

// ヘルスチェック
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    hasRakutenApi: !!process.env.RAKUTEN_APP_ID,
    hasYahooApi: !!process.env.YAHOO_APP_ID
  });
});

// メインページ
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`サーバーが起動しました: http://localhost:${PORT}`);
  console.log('');
  console.log('API設定状況:');
  console.log(`  楽天API: ${process.env.RAKUTEN_APP_ID ? '設定済み' : '未設定（デモモード）'}`);
  console.log(`  Yahoo!API: ${process.env.YAHOO_APP_ID ? '設定済み' : '未設定（デモモード）'}`);
});
