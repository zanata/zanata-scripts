#!/bin/env groovy

@GrabResolver(name='jboss-public-repository-group', root='https://repository.jboss.org/nexus/content/groups/public/')
@Grapes(
@Grab(group='org.jboss.seam', module='jboss-seam', version='2.3.1.Final')
)
import org.jboss.seam.security.management.PasswordHash

if (args.length != 2) {
	println "Usage: ${this.class.name}.groovy <username> <password>"
	return 1
}

def username = args[0]
def password = args[1]
def salt = username

def hash = new PasswordHash().generateSaltedHash(password, salt, 'MD5')

println "To set the password for '$username', please execute the following SQL against Zanata's mysql database:\n"
println "UPDATE HAccount SET passwordHash = '${hash}' WHERE username='${username}';"
