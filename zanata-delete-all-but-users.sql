-- This SQL script tries to delete pretty much everything except users
-- and their locale memberships

-- Things it deletes:
-- projects, project groups and everything inside them
-- webhooks, glossaries, translation memories
-- activity information
-- some host-specific server configuration

-- The script also deletes any disabled locales (and
-- membership/coordinator information).

-- NB: the following tables are deliberately not purged:
-- HAccount* HCredentials HLocale* HPerson* HRoleAssignmentRule

-- Warning: this has only been tested against one database. Some delete
-- statements are probably in the wrong order, and will violate
-- constraints if the tables contain any data.
-- The script may also leave orphan records in some cases.

-- Zanata DB version: 3.7.1

delete from Activity;
delete from HTextFlowTargetContentHistory;
delete from HPoTargetHeader;
delete from HTextFlowTargetHistory;
delete from HTextFlowTargetReviewComment;
delete from HTextFlowTarget;
delete from HTextFlowContentHistory;
delete from HTextFlowHistory;
delete from HTextFlow;
delete from HPotEntryData;
delete from TransMemoryUnitVariant;
delete from TransMemoryUnit;
delete from TransMemory_Metadata;
delete from TransMemory;
delete from WebHook;
delete from HTermComment;
delete from HDocument_RawDocument;
delete from HRawDocument;
delete from HDocumentUploadPart;
delete from HDocumentUpload;
delete from HDocumentHistory;
delete from HDocument;
delete from HPoHeader;
delete from HSimpleComment;
delete from HProjectIteration_Locale;
delete from HProjectIteration_Validation;
delete from HProjectIteration;
delete from HProject_AllowedRole;
delete from HProject_Locale;
delete from HProject_Maintainer;
delete from HProject_Validation;
delete from HProject;
delete from HCopyTransOptions;
delete from HTermComment;
delete from HGlossaryTerm;
delete from HGlossaryEntry;
delete from IterationGroup_Locale;
delete from HIterationGroup_Maintainer;
delete from HIterationGroup_ProjectIteration;
delete from HIterationGroup;

delete from HApplicationConfiguration
  where config_key in ('host.url', 'log.email.active', 'piwik.url', 'piwik.idSite');

delete from HLocale_Member
where supportedLanguageId in (select id from HLocale where active=false);

delete from HLocale
where active=false;

