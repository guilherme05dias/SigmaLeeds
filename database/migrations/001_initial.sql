-- Campanhas
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  message_template TEXT NOT NULL,
  attachment_path TEXT,
  account_id INTEGER,
  status TEXT DEFAULT 'draft',
  total_contacts INTEGER DEFAULT 0,
  sent INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0,
  invalid INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  finished_at TIMESTAMP
);

-- Contatos de cada campanha
CREATE TABLE IF NOT EXISTS campaign_contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  name TEXT,
  phone TEXT NOT NULL,
  company TEXT,
  extra_fields TEXT,  -- JSON com colunas extras da planilha
  status TEXT DEFAULT 'PENDENTE',
  sent_at TIMESTAMP,
  error_message TEXT,
  observation TEXT
);

-- Contas WhatsApp
CREATE TABLE IF NOT EXISTS whatsapp_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT NOT NULL,
  phone TEXT,
  profile_path TEXT NOT NULL,
  status TEXT DEFAULT 'disconnected',
  last_connected TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Templates de mensagem
CREATE TABLE IF NOT EXISTS templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  variables TEXT,  -- JSON: lista de variáveis detectadas ex: ["nome","empresa"]
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blacklist de contatos (opt-out)
CREATE TABLE IF NOT EXISTS blacklist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phone TEXT NOT NULL UNIQUE,
  reason TEXT,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configurações do sistema
CREATE TABLE IF NOT EXISTS system_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
