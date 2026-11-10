-- ClipShop AI: schema MySQL cho Address, Cart, CartItem, Order, OrderItem
-- (sinh từ SQLAlchemy models; FK tới users/shops/products do module khác định nghĩa)

CREATE TABLE addresses (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	recipient_name VARCHAR(100) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	address TEXT NOT NULL, 
	is_default BOOL NOT NULL DEFAULT '0', 
	created_at DATETIME NOT NULL DEFAULT (now()), 
	updated_at DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_addresses_user_default ON addresses (user_id, is_default);

CREATE TABLE carts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT (now()), 
	updated_at DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);


CREATE TABLE cart_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	cart_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cart_items_cart_product UNIQUE (cart_id, product_id), 
	CONSTRAINT ck_cart_items_quantity_positive CHECK (quantity > 0), 
	FOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE INDEX ix_cart_items_product_id ON cart_items (product_id);

CREATE TABLE orders (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_code VARCHAR(32) NOT NULL, 
	buyer_id INTEGER NOT NULL, 
	shop_id INTEGER NOT NULL, 
	recipient_name VARCHAR(100) NOT NULL, 
	recipient_phone VARCHAR(20) NOT NULL, 
	shipping_address TEXT NOT NULL, 
	payment_method ENUM('cod','simulated') NOT NULL, 
	total_amount NUMERIC(12, 2) NOT NULL, 
	status ENUM('pending','confirmed','shipping','completed','cancelled') NOT NULL DEFAULT 'pending', 
	created_at DATETIME NOT NULL DEFAULT (now()), 
	updated_at DATETIME NOT NULL DEFAULT (now()), 
	PRIMARY KEY (id), 
	CONSTRAINT ck_orders_total_non_negative CHECK (total_amount >= 0), 
	UNIQUE (order_code), 
	FOREIGN KEY(buyer_id) REFERENCES users (id) ON DELETE RESTRICT, 
	FOREIGN KEY(shop_id) REFERENCES shops (id) ON DELETE RESTRICT
);

CREATE INDEX ix_orders_buyer_created ON orders (buyer_id, created_at);
CREATE INDEX ix_orders_shop_status ON orders (shop_id, status);

CREATE TABLE order_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	order_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	product_name VARCHAR(255) NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_order_items_quantity_positive CHECK (quantity > 0), 
	CONSTRAINT ck_order_items_price_non_negative CHECK (unit_price >= 0), 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE RESTRICT
);

CREATE INDEX ix_order_items_order_id ON order_items (order_id);
CREATE INDEX ix_order_items_product_id ON order_items (product_id);
