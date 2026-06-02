-- Revision 12: таблица прав пользователей FamilyMang
-- Примеры permission: 'delete_families', 'manage_users'

CREATE TABLE IF NOT EXISTS atptlp_info.family_user_permissions (
    windows_user TEXT NOT NULL,
    permission   TEXT NOT NULL,
    PRIMARY KEY (windows_user, permission)
);

CREATE INDEX IF NOT EXISTS ix_family_user_permissions_user
    ON atptlp_info.family_user_permissions (windows_user);

-- Пример: выдать право удаления пользователю
-- INSERT INTO atptlp_info.family_user_permissions (windows_user, permission)
-- VALUES ('ivanov', 'delete_families');
