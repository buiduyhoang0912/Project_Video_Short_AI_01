-- T3D201D: thêm cột kiểm duyệt cho videos và products.
-- Chạy 1 lần trên DB đã có sẵn bảng (create_all KHÔNG tự sửa bảng cũ).
-- DB tạo mới từ đầu thì không cần: SQLAlchemy tự tạo đủ cột.

ALTER TABLE videos
  ADD COLUMN moderation_reason VARCHAR(500) NULL,
  ADD COLUMN moderated_by BIGINT UNSIGNED NULL,
  ADD COLUMN moderated_at DATETIME NULL,
  ADD CONSTRAINT fk_videos_moderated_by FOREIGN KEY (moderated_by) REFERENCES users(id);

ALTER TABLE products
  ADD COLUMN moderation_reason VARCHAR(500) NULL,
  ADD COLUMN moderated_by BIGINT UNSIGNED NULL,
  ADD COLUMN moderated_at DATETIME NULL,
  ADD CONSTRAINT fk_products_moderated_by FOREIGN KEY (moderated_by) REFERENCES users(id);
