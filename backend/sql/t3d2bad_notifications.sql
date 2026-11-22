-- Task T3D2BAD: Hệ thống thông báo trong web
-- Bảng notifications: lưu các thông báo tương tác (like, comment, follow) và trạng thái đơn hàng

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient_id BIGINT UNSIGNED NOT NULL,
    actor_id BIGINT UNSIGNED NULL,
    type VARCHAR(50) NOT NULL,
    content VARCHAR(500) NOT NULL,
    video_id BIGINT UNSIGNED NULL,
    order_id BIGINT UNSIGNED NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_notifications_recipient_id (recipient_id),
    INDEX ix_notifications_actor_id (actor_id),
    INDEX ix_notifications_type (type),
    INDEX ix_notifications_video_id (video_id),
    INDEX ix_notifications_order_id (order_id),
    INDEX ix_notifications_is_read (is_read),
    INDEX ix_notifications_created_at (created_at),
    CONSTRAINT fk_notifications_recipient FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_notifications_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
