CREATE DATABASE IF NOT EXISTS ecostock_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ecostock_db;

CREATE TABLE IF NOT EXISTS usuarios (
    id                 INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    login              VARCHAR(80)  NOT NULL UNIQUE,
    senha_hash         VARCHAR(255) NOT NULL,
    nivel_acesso       ENUM('Liberacao','Operador','Administrador') NOT NULL DEFAULT 'Operador',
    ativo              TINYINT(1)   NOT NULL DEFAULT 1,
    email              VARCHAR(120) DEFAULT NULL,
    can_view_audit     TINYINT(1) NOT NULL DEFAULT 0,
    can_edit_stock     TINYINT(1) NOT NULL DEFAULT 0,
    can_delete_items   TINYINT(1) NOT NULL DEFAULT 0,
    can_add_product    TINYINT(1) NOT NULL DEFAULT 0,
    criado_em          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_login       DATETIME DEFAULT NULL,
    INDEX idx_nivel (nivel_acesso),
    INDEX idx_ativo (ativo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS produtos (
    id                   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome                 VARCHAR(120) NOT NULL,
    categoria            VARCHAR(60)  NOT NULL DEFAULT 'Geral',
    unidade              VARCHAR(20)  NOT NULL DEFAULT 'UN',
    estoque_min          DECIMAL(10,2) NOT NULL DEFAULT 1.00,
    preco_referencia     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ativo                TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nome (nome),
    INDEX idx_categoria (categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lotes (
    id                 INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_produto         INT UNSIGNED NOT NULL,
    codigo_lote        VARCHAR(60)  NOT NULL UNIQUE,
    quantidade_atual   DECIMAL(10,2) NOT NULL DEFAULT 0,
    quantidade_inicial DECIMAL(10,2) NOT NULL DEFAULT 0,
    custo_unitario     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    preco_venda_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    fornecedor         VARCHAR(120) DEFAULT NULL,
    data_validade      DATE         NOT NULL,
    data_entrada       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario_entry   INT UNSIGNED DEFAULT NULL,
    FOREIGN KEY (id_produto) REFERENCES produtos(id) ON DELETE RESTRICT,
    FOREIGN KEY (id_usuario_entry) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_validade (data_validade),
    INDEX idx_produto (id_produto),
    INDEX idx_quantidade (quantidade_atual)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_produto          INT UNSIGNED NOT NULL,
    id_lote             INT UNSIGNED DEFAULT NULL,
    id_usuario          INT UNSIGNED DEFAULT NULL,
    tipo_movimento      ENUM('ENTRADA','SAIDA','AJUSTE_POSITIVO','AJUSTE_NEGATIVO','DESCARTE_VENCIDO','AVARIA','EXCLUSAO') NOT NULL,
    quantidade          DECIMAL(10,2) NOT NULL,
    quantidade_anterior DECIMAL(10,2) DEFAULT NULL,
    quantidade_posterior DECIMAL(10,2) DEFAULT NULL,
    motivo              VARCHAR(80) DEFAULT NULL,
    valor_unitario      DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    valor_total         DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    observacao          VARCHAR(255) DEFAULT NULL,
    criado_em           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_produto) REFERENCES produtos(id) ON DELETE RESTRICT,
    FOREIGN KEY (id_lote) REFERENCES lotes(id) ON DELETE SET NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_mov_tipo (tipo_movimento),
    INDEX idx_mov_prod (id_produto),
    INDEX idx_mov_lote (id_lote),
    INDEX idx_mov_data (criado_em)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auditoria (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario    INT UNSIGNED DEFAULT NULL,
    login_usuario VARCHAR(80) DEFAULT 'sistema',
    tipo_acao     VARCHAR(50) NOT NULL,
    descricao     TEXT NOT NULL,
    ip_origem     VARCHAR(45) NOT NULL DEFAULT '0.0.0.0',
    user_agent    VARCHAR(255) DEFAULT NULL,
    resultado     ENUM('Sucesso','Falha','Bloqueado') NOT NULL DEFAULT 'Sucesso',
    dados_antes   JSON DEFAULT NULL,
    dados_depois  JSON DEFAULT NULL,
    data_hora     DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    INDEX idx_tipo (tipo_acao),
    INDEX idx_usuario (id_usuario),
    INDEX idx_data_hora (data_hora),
    INDEX idx_resultado (resultado)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notificacoes_enviadas (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_lote    INT UNSIGNED NOT NULL,
    tipo       ENUM('AVISO_30','AVISO_15','CRITICO_7','VENCIDO') NOT NULL,
    enviado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_lote_tipo (id_lote, tipo),
    FOREIGN KEY (id_lote) REFERENCES lotes(id) ON DELETE CASCADE
) ENGINE=InnoDB;

INSERT IGNORE INTO usuarios
    (login, senha_hash, nivel_acesso, ativo, can_view_audit, can_edit_stock, can_delete_items, can_add_product)
VALUES
    ('admin',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhcanFp8.xCPZly8I5R9Eq',
     'Administrador', 1, 1, 1, 1, 1);
