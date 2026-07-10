ALTER TABLE integration_secrets RENAME COLUMN key_name TO label;
ALTER TABLE integration_secrets RENAME COLUMN platform TO provider;
