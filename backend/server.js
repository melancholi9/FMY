const express = require('express');
const cors = require('cors');
const path = require('path');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// ── Customers ──────────────────────────────────────────────
app.get('/api/customers', (req, res) => {
  const { search, status } = req.query;
  let query = 'SELECT * FROM customers WHERE 1=1';
  const params = [];

  if (search) {
    query += ' AND (name LIKE ? OR company LIKE ? OR email LIKE ?)';
    const s = `%${search}%`;
    params.push(s, s, s);
  }
  if (status) {
    query += ' AND status = ?';
    params.push(status);
  }
  query += ' ORDER BY created_at DESC';

  res.json(db.prepare(query).all(...params));
});

app.get('/api/customers/:id', (req, res) => {
  const customer = db.prepare('SELECT * FROM customers WHERE id = ?').get(req.params.id);
  if (!customer) return res.status(404).json({ error: 'Not found' });

  const deals = db.prepare('SELECT * FROM deals WHERE customer_id = ? ORDER BY created_at DESC').all(req.params.id);
  const activities = db.prepare('SELECT * FROM activities WHERE customer_id = ? ORDER BY date DESC').all(req.params.id);

  res.json({ ...customer, deals, activities });
});

app.post('/api/customers', (req, res) => {
  const { name, company, email, phone, status, notes } = req.body;
  if (!name) return res.status(400).json({ error: 'Name is required' });

  const result = db.prepare(
    'INSERT INTO customers (name, company, email, phone, status, notes) VALUES (?, ?, ?, ?, ?, ?)'
  ).run(name, company || null, email || null, phone || null, status || 'active', notes || null);

  res.status(201).json(db.prepare('SELECT * FROM customers WHERE id = ?').get(result.lastInsertRowid));
});

app.put('/api/customers/:id', (req, res) => {
  const { name, company, email, phone, status, notes } = req.body;
  const existing = db.prepare('SELECT id FROM customers WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Not found' });

  db.prepare(
    'UPDATE customers SET name=?, company=?, email=?, phone=?, status=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(name, company || null, email || null, phone || null, status || 'active', notes || null, req.params.id);

  res.json(db.prepare('SELECT * FROM customers WHERE id = ?').get(req.params.id));
});

app.delete('/api/customers/:id', (req, res) => {
  const result = db.prepare('DELETE FROM customers WHERE id = ?').run(req.params.id);
  if (result.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.json({ success: true });
});

// ── Deals ──────────────────────────────────────────────────
app.get('/api/deals', (req, res) => {
  const deals = db.prepare(`
    SELECT d.*, c.name as customer_name, c.company
    FROM deals d
    LEFT JOIN customers c ON d.customer_id = c.id
    ORDER BY d.created_at DESC
  `).all();
  res.json(deals);
});

app.post('/api/deals', (req, res) => {
  const { customer_id, title, amount, stage, expected_close, notes } = req.body;
  if (!customer_id || !title) return res.status(400).json({ error: 'customer_id and title are required' });

  const result = db.prepare(
    'INSERT INTO deals (customer_id, title, amount, stage, expected_close, notes) VALUES (?, ?, ?, ?, ?, ?)'
  ).run(customer_id, title, amount || 0, stage || 'prospect', expected_close || null, notes || null);

  res.status(201).json(db.prepare('SELECT * FROM deals WHERE id = ?').get(result.lastInsertRowid));
});

app.put('/api/deals/:id', (req, res) => {
  const { title, amount, stage, expected_close, notes } = req.body;
  const existing = db.prepare('SELECT id FROM deals WHERE id = ?').get(req.params.id);
  if (!existing) return res.status(404).json({ error: 'Not found' });

  db.prepare(
    'UPDATE deals SET title=?, amount=?, stage=?, expected_close=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(title, amount || 0, stage, expected_close || null, notes || null, req.params.id);

  res.json(db.prepare('SELECT * FROM deals WHERE id = ?').get(req.params.id));
});

app.delete('/api/deals/:id', (req, res) => {
  const result = db.prepare('DELETE FROM deals WHERE id = ?').run(req.params.id);
  if (result.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.json({ success: true });
});

// ── Activities ─────────────────────────────────────────────
app.get('/api/activities', (req, res) => {
  const activities = db.prepare(`
    SELECT a.*, c.name as customer_name, d.title as deal_title
    FROM activities a
    LEFT JOIN customers c ON a.customer_id = c.id
    LEFT JOIN deals d ON a.deal_id = d.id
    ORDER BY a.date DESC
    LIMIT 50
  `).all();
  res.json(activities);
});

app.post('/api/activities', (req, res) => {
  const { customer_id, deal_id, type, title, description, date } = req.body;
  if (!type || !title) return res.status(400).json({ error: 'type and title are required' });

  const result = db.prepare(
    'INSERT INTO activities (customer_id, deal_id, type, title, description, date) VALUES (?, ?, ?, ?, ?, ?)'
  ).run(customer_id || null, deal_id || null, type, title, description || null, date || new Date().toISOString());

  res.status(201).json(db.prepare('SELECT * FROM activities WHERE id = ?').get(result.lastInsertRowid));
});

app.delete('/api/activities/:id', (req, res) => {
  const result = db.prepare('DELETE FROM activities WHERE id = ?').run(req.params.id);
  if (result.changes === 0) return res.status(404).json({ error: 'Not found' });
  res.json({ success: true });
});

// ── Dashboard Stats ────────────────────────────────────────
app.get('/api/stats', (req, res) => {
  const totalCustomers = db.prepare("SELECT COUNT(*) as count FROM customers WHERE status = 'active'").get();
  const totalDeals = db.prepare('SELECT COUNT(*) as count, SUM(amount) as total FROM deals').get();
  const stageStats = db.prepare('SELECT stage, COUNT(*) as count, SUM(amount) as total FROM deals GROUP BY stage').all();
  const recentActivities = db.prepare(`
    SELECT a.*, c.name as customer_name
    FROM activities a
    LEFT JOIN customers c ON a.customer_id = c.id
    ORDER BY a.date DESC LIMIT 5
  `).all();

  res.json({
    activeCustomers: totalCustomers.count,
    totalDeals: totalDeals.count,
    totalAmount: totalDeals.total || 0,
    stageStats,
    recentActivities
  });
});

app.listen(PORT, () => {
  console.log(`CRM server running at http://localhost:${PORT}`);
});
