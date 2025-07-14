-- init.sql (refactored)

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Index levels table
CREATE TABLE IF NOT EXISTS indexlevels (
  date DATE PRIMARY KEY,
  level REAL,
  divisor REAL
);

-- Trigger: ensure date >= base_date
CREATE TRIGGER IF NOT EXISTS indexlevels_base_date_check
BEFORE INSERT ON indexlevels
BEGIN
  SELECT
    CASE
      WHEN NEW.date < (SELECT value FROM settings WHERE key = 'base_date')
      THEN RAISE (ABORT, 'Date must be >= base_date')
    END;
END;

-- Market data table
CREATE TABLE IF NOT EXISTS marketdata (
  date DATE NOT NULL,
  stock TEXT NOT NULL,
  price REAL,
  shares_outstanding REAL,
  PRIMARY KEY (date, stock)
);

-- Members table (NO price or shares_outstanding stored)
CREATE TABLE IF NOT EXISTS members (
  date DATE NOT NULL,
  stock TEXT NOT NULL,
  notional_num_shares REAL,
  PRIMARY KEY (date, stock),
  FOREIGN KEY (date) REFERENCES indexlevels(date) ON DELETE CASCADE,
  FOREIGN KEY (date, stock) REFERENCES marketdata(date, stock) ON DELETE CASCADE
);

-- Changes table
CREATE TABLE IF NOT EXISTS changes (
  date DATE NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('ADD', 'REMOVE', 'REBALANCE')),
  stock TEXT NOT NULL,
  PRIMARY KEY (date, stock),
  FOREIGN KEY (date, stock) REFERENCES marketdata(date, stock) ON DELETE CASCADE
);

-- Set base date and base value
INSERT OR REPLACE INTO settings (key, value) VALUES ('base_date', '2025-06-02');
INSERT OR REPLACE INTO settings (key, value) VALUES ('base_value', '1000');
