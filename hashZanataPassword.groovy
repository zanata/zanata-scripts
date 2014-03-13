#!/bin/env groovy

@GrabResolver(name='jboss-public-repository-group', root='https://repository.jboss.org/nexus/content/groups/public/')
@Grapes(
@Grab(group='org.jboss.seam', module='jboss-seam', version='2.3.1.Final')
)
import org.jboss.seam.security.management.PasswordHash

if (args.length != 2) {
	println "Usage: ${this.class.name} <username> <password>"
	return 1
}

def username = args[0]
def password = args[1]
def salt = username

def hash = new PasswordHash().generateSaltedHash(password, salt, 'MD5')

println "UPDATE HAccount SET passwordHash = '${hash}' WHERE username='${username}';"
println "INSERT IGNORE INTO HAccountMembership (accountId, memberOf)\n"+
	"  VALUES ((select id from HAccount where username='sflaniga'), "+
		"(select id from HAccountRole where name='admin'));"
