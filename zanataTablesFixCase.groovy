#!/bin/env groovy
/*
 * zanata-table-fix-case.groovy
 *
 * Unix filter script to convert lower case Zanata table names back to their original (title) case in an SQL backup
 *
 * Usage: zcat zanata_backup.sql.gz | zanata-tables-fix-case.groovy | gzip -c > zanata_backup.casefixed.sql.gz
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
HProject_LocaleMember
HProject_Member
HProjectIteration
HProjectIteration_Locale
HProjectIteration_LocaleAlias
HProjectIteration_Validation
HProject_AllowedRole
HProject_Locale
HProject_LocaleAlias
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
IterationGroup_Locale
LanguageRequest
TransMemory
TransMemoryUnit
TransMemoryUnitVariant
TransMemory_Metadata
WebHook
"""

def tables = tableNames.split('\n').collect { it.trim() }

def lowerNames = new HashSet()

// map from back-quoted lower case name to back-quoted original case name
def quotedNames = [:]

// populate lowerNames, quotedNames
tables.each {
    table ->
    // skip any empty lines
    if (table) {
        def lowerTable = table.toLowerCase()
        lowerNames.add(lowerTable)
        quotedNames.put("`"+lowerTable+"`", "`"+table+"`")
    }
}

def foundTables = new HashSet()
// process stdin, replacing lower-case table names with original case
System.in.eachLine() { line ->
    def tableRegex = /(DROP|CREATE) TABLE (IF EXISTS )?`([^`]+)`/
    def tableMatcher = line =~ tableRegex
    tableMatcher.each {
        def table = it[3]
        if (!foundTables.contains(table)) {
            if (!table.toLowerCase().equals(table)) {
                System.err.println "WARNING: table is already mixed case: " + table
                System.err.println "Are you sure you need to run this script?"
            } else if (!lowerNames.contains(table)) {
                System.err.println "ERROR: Unexpected table: " + table
                System.err.println "Please update this script."
                System.exit 1
            }
            foundTables.add(table)
        }
    }
    if (line.startsWith('CREATE DATABASE ') || line.startsWith('USE `')) {
        // comment out, so that we can use any database name
        println "-- $line"
    } else {
        quotedNames.each { lower, orig -> line = line.replace(lower, orig) }
        println "$line"
    }
}
null
