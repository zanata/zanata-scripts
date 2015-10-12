-- This SQL deletes some host-specific values from a Zanata database.
-- Read the source comments to see what is deleted.


-- Warning: this has only had minimal testing.

-- Author: Sean Flanigan <sflaniga@redhat.com>

-- server URL
DELETE FROM HApplicationConfiguration WHERE config_key LIKE 'host.url';

-- piwik settings
DELETE FROM HApplicationConfiguration WHERE config_key LIKE 'piwik%';

-- settings for log emails
DELETE FROM HApplicationConfiguration WHERE config_key LIKE 'log.email.active';
DELETE FROM HApplicationConfiguration WHERE config_key LIKE 'log.destination.email';
