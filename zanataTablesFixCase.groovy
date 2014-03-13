#!/bin/env groovy
/*
 * zanata-table-fix-case.groovy
 *
 * Unix filter script to convert lower case Zanata table names back to their original (title) case in an SQL backup
 *
 * Usage: zcat zanata_backup.sql.gz | zanata-tables-fix-case.groovy | gzip -c > zanata_backup.casefixed.sql.gz
 *
 * Version 3
 * Date: 7 Nov 2013
 * Author: Sean Flanigan <sflaniga@redhat.com>
 *
 * Changelog:
 *
 * 7 Nov 2013 Sean Flanigan <sflaniga@redhat.com>
 * Bug fix: need to replace long table names first
 *
 * 5 Nov 2013 Sean Flanigan <sflaniga@redhat.com>
 * Check for unknown table names
 *
 * 4 Nov 2013 Sean Flanigan <sflaniga@redhat.com>
 * Initial version
 */

// Table list generated with this commend:
// echo "SELECT table_name FROM information_schema.tables WHERE table_schema='zanata';" | mysql --silent -u root zanata
def tableNames = """\
Activity
DATABASECHANGELOG
DATABASECHANGELOGLOCK
HAccount
HAccountActivationKey
HAccountMembership
HAccountOption
HAccountResetPasswordKey
HAccountRole
HAccountRoleGroup
HApplicationConfiguration
HCopyTransOptions
HCredentials
HDocument
HDocumentHistory
HDocumentUpload
HDocumentUploadPart
HDocument_RawDocument
HGlossaryEntry
HGlossaryTerm
HIterationGroup
HIterationGroup_Maintainer
HIterationGroup_ProjectIteration
HLocale
HLocale_Member
HPerson
HPersonEmailValidationKey
HPoHeader
HPoTargetHeader
HPotEntryData
HProject
HProjectIteration
HProjectIteration_Locale
HProjectIteration_Validation
HProject_AllowedRole
HProject_Locale
HProject_Maintainer
HProject_Validation
HRawDocument
HRoleAssignmentRule
HSimpleComment
HTermComment
HTextFlow
HTextFlowContentHistory
HTextFlowHistory
HTextFlowTarget
HTextFlowTargetContentHistory
HTextFlowTargetHistory
HTextFlowTargetReviewComment
TransMemory
TransMemoryUnit
TransMemoryUnitVariant
TransMemory_Metadata
"""

// sort tables by descending length
def tables = tableNames.split('\n').collect { it.trim() } .sort { -it.size() }

// map from lower case name to original case name
def names = [:]
// populate names map
tables.each { table -> if (table) names.put(table.toLowerCase(), table) }

// process stdin, replacing lower-case table names with original case
System.in.eachLine() { line ->
    def tableRegex = /(DROP|CREATE) TABLE (IF EXISTS )?`([^`]+)`/
    def tableMatcher = line =~ tableRegex
    tableMatcher.each {
        def table = it[3]
        if (!names[table]) {
            System.err.println "Unexpected table: " + table
            System.err.println "Please update this script."
            System.exit 1
        }
    }
    names.each { lower, orig -> line = line.replace(lower, orig) }
    println "$line"
}
null