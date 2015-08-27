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

-- The deletion order was created with help from SchemaSpy 5.0.0
-- running against Zanata 3.6, but it should work for 3.7 too.

-- Warning: this has only had minimal testing.

-- Author: Sean Flanigan <sflaniga@redhat.com>

delete from TransMemoryUnitVariant;
delete from TransMemoryUnit;
delete from TransMemory_Metadata;
delete from TransMemory;
delete from IterationGroup_Locale;
delete from HTextFlowTargetReviewComment;
delete from HTextFlowTargetContentHistory;
delete from HTextFlowContentHistory;
delete from HRawDocument;
delete from HProjectIteration_Validation;
delete from HProject_Validation;
delete from HProject_AllowedRole;
delete from HIterationGroup_ProjectIteration;
delete from HIterationGroup_Maintainer;
delete from HIterationGroup;
delete from HDocumentUploadPart;
delete from HDocumentUpload;
delete from HDocument_RawDocument;
delete from Activity;
delete from HPoTargetHeader;
delete from HDocumentHistory;
delete from HTextFlowTargetHistory;
delete from HProjectIteration_Locale;
delete from HProject_Maintainer;
delete from HProject_Locale;
delete from WebHook;
delete from HTextFlowHistory;
delete from HTermComment;
delete from HProjectIteration_LocaleAlias;
delete from HProject_LocaleAlias;
delete from HTextFlowTarget;
delete from HGlossaryTerm;
delete from HTextFlow;
delete from HDocument;
delete from HProjectIteration;
delete from HPotEntryData;
delete from HPoHeader;
delete from HGlossaryEntry;
delete from HProject;
delete from HCopyTransOptions;
delete from HSimpleComment;

delete from HApplicationConfiguration
  where config_key in ('host.url', 'log.email.active', 'piwik.url', 'piwik.idSite');

delete from HLocale_Member
  where supportedLanguageId in (select id from HLocale where active=false);

delete from HLocale
  where active=false;
