-- Revision 7: единый каталог семейств
-- Создать компанию-носитель каталога (идемпотентно).
-- Значение company_id должно совпадать с env SHARED_CATALOG_COMPANY_ID (default: CATALOG).

INSERT INTO atptlp_info.companies (company_id, name, is_active)
VALUES ('CATALOG', 'Общий каталог семейств', true)
ON CONFLICT (company_id) DO NOTHING;

-- После применения миграции выполнить консолидацию данных вручную:
--
-- UPDATE "ATPTLP_familymanager".families f
-- SET project_id = c.id
-- FROM atptlp_info.companies c
-- WHERE c.company_id = 'CATALOG';
--
-- Это переводит все существующие записи families в единый каталог.
-- Запускать ОДИН РАЗ на production после развёртывания rev 7.
