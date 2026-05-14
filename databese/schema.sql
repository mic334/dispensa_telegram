-- database/schema.sql
-- Schema database per dispensa_telegram
-- Compatibile con MariaDB / MySQL

CREATE DATABASE IF NOT EXISTS dispensa
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE dispensa;

-- -----------------------------------------------------
-- Tabella principale dei prodotti in dispensa
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 3) NULL,
    initial_quantity DECIMAL(10, 3) NULL,
    unit VARCHAR(50) NULL,
    location VARCHAR(100) NULL,

    expiry_date DATE NULL,
    notes TEXT NULL,
    price DECIMAL(10, 2) NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_items_name (name),
    INDEX idx_items_location (location),
    INDEX idx_items_expiry_date (expiry_date),
    INDEX idx_items_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Log dei prodotti buttati / sprecati
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS waste_log (
    id INT AUTO_INCREMENT PRIMARY KEY,

    item_id INT NULL,
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 3) NULL,
    unit VARCHAR(50) NULL,
    estimated_value DECIMAL(10, 2) NULL,
    notes TEXT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_waste_log_item
        FOREIGN KEY (item_id)
        REFERENCES items(id)
        ON DELETE SET NULL,

    INDEX idx_waste_log_item_id (item_id),
    INDEX idx_waste_log_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Scontrini letti dal bot tramite immagine
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS receipts (
    id INT AUTO_INCREMENT PRIMARY KEY,

    chat_id BIGINT NOT NULL,
    label VARCHAR(100) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,

    status ENUM('draft', 'confirmed', 'cancelled') NOT NULL DEFAULT 'draft',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,

    INDEX idx_receipts_chat_id (chat_id),
    INDEX idx_receipts_status (status),
    INDEX idx_receipts_chat_status (chat_id, status),
    INDEX idx_receipts_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Righe/prodotti estratti da ogni scontrino
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS receipt_lines (
    id INT AUTO_INCREMENT PRIMARY KEY,

    receipt_id INT NOT NULL,

    raw_name VARCHAR(255) NULL,
    name VARCHAR(255) NOT NULL,

    quantity DECIMAL(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(50) NOT NULL DEFAULT 'pezzo',

    line_price DECIMAL(10, 2) NULL,
    unit_price DECIMAL(10, 4) NULL,

    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    added_to_pantry BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_receipt_lines_receipt
        FOREIGN KEY (receipt_id)
        REFERENCES receipts(id)
        ON DELETE CASCADE,

    INDEX idx_receipt_lines_receipt_id (receipt_id),
    INDEX idx_receipt_lines_name (name),
    INDEX idx_receipt_lines_added_to_pantry (added_to_pantry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
