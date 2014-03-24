#!/bin/env groovy

if (args.length != 1) {
	println "Usage: ${this.class.name} <username>"
	return 1
}

def username = args[0]
println "To make '$username' an admin, please execute the following SQL against Zanata's mysql database:\n"
println "INSERT IGNORE INTO HAccountMembership (accountId, memberOf)\n"+
	"  VALUES ((select id from HAccount where username='$username'), "+
		"(select id from HAccountRole where name='admin'));"
