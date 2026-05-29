-- E-commerce schema example for ER diagram generation

CREATE TABLE IF NOT EXISTS `users` (
    `id`           BIGINT       NOT NULL AUTO_INCREMENT,
    `email`        VARCHAR(200) NOT NULL,
    `name`         VARCHAR(100) NOT NULL,
    `phone`        VARCHAR(20),
    `status`       VARCHAR(50)  NOT NULL DEFAULT 'ACTIVE',
    `credit_limit` DECIMAL(19,2),
    `created_at`   DATETIME     NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY uq_users_email (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `products` (
    `id`          BIGINT        NOT NULL AUTO_INCREMENT,
    `sku`         VARCHAR(100)  NOT NULL,
    `name`        VARCHAR(255)  NOT NULL,
    `description` TEXT,
    `price`       DECIMAL(19,2) NOT NULL,
    `stock_qty`   INT           NOT NULL DEFAULT 0,
    `category`    VARCHAR(50),
    PRIMARY KEY (`id`),
    UNIQUE KEY uq_products_sku (`sku`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `orders` (
    `id`          BIGINT        NOT NULL AUTO_INCREMENT,
    `user_id`     BIGINT        NOT NULL,
    `status`      VARCHAR(50)   NOT NULL DEFAULT 'PENDING',
    `total`       DECIMAL(19,2) NOT NULL,
    `placed_at`   DATETIME      NOT NULL,
    `shipped_at`  DATETIME,
    PRIMARY KEY (`id`),
    CONSTRAINT fk_orders_user FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `order_items` (
    `id`         BIGINT        NOT NULL AUTO_INCREMENT,
    `order_id`   BIGINT        NOT NULL,
    `product_id` BIGINT        NOT NULL,
    `quantity`   INT           NOT NULL,
    `unit_price` DECIMAL(19,2) NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT fk_items_order   FOREIGN KEY (`order_id`)   REFERENCES `orders`   (`id`),
    CONSTRAINT fk_items_product FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
