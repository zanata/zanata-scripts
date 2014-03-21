#!/usr/bin/env groovy

@Grab(group='org.jboss.pressgang.ccms', module='j2bugzilla-pressgang', version='1.4.1-SNAPSHOT')
//@Grab(group='com.j2bugzilla', module='j2bugzilla', version='2.2')
import com.j2bugzilla.base.*;
import com.j2bugzilla.rpc.*;

import groovy.swing.SwingBuilder
import groovy.transform.Field

@Field
File gitDir = new File('.')
String release = 'origin/master'

def cli = new CliBuilder(usage: 'update/close Zanata bugs based on Fixed In Version')
cli.d(longOpt: 'dir', args: 1, "Git workspace [default: $gitDir]")
cli.h(longOpt: 'help', "Print this help")
cli.n(longOpt: 'dryRun', "Dry run (no changes to bugs)")
cli.p(longOpt: 'password', args: 1, "Bugzilla password (Warning: password on command line is insecure)")
cli.r(longOpt: 'release', args: 1,
    """Git release branch/tag (or commit) to check [default: $release].
    If a branch, fixed bugs will be marked RELEASE_PENDING.
    If a tag, fixed bugs will be CLOSED(CURRENTRELEASE).""".stripMargin())
cli.u(longOpt: 'username', args: 1, "Bugzilla username")

def opts = cli.parse(args)
if (!opts) System.exit(1)
if (opts.help) {
    cli.usage()
    System.exit(0)
}

String user = opts.username ?: null
if (!user) {
    user = System.console().readLine("Please enter Bugzilla username: ")
}
println "Username: $user"
String pass = opts.password ?: null
if (!pass) {
    def p = System.console().readPassword("Please enter Bugzilla password: ")
    if (!p) throw new Exception("password required")
    pass = new String(p)
}
boolean dryRun = opts.dryRun
println "Dry run: $dryRun"
if (opts.dir) gitDir = opts.dir // else default above
println "Git dir: $gitDir"
if (opts.release) release = opts.release // else default above
println "Checking git release: $release"



def checkingReleaseTag = isTag(release)
def checkingReleaseBranch = isBranch(release)

println "Release is a tag: $checkingReleaseTag"
println "Release is a branch: $checkingReleaseBranch"

String bugzillaUrl = 'https://bugzilla.redhat.com/'

@Field
BugzillaConnector conn = new BugzillaConnector();
conn.connectTo(bugzillaUrl);
conn.executeMethod(new LogIn(user, pass));

def statuses
if (checkingReleaseBranch) {
    statuses = ['VERIFIED']
} else {
    statuses =  ['VERIFIED', 'RELEASE_PENDING']
}
println "Searching for Zanata bugs with status: $statuses\n"
List results = search(statuses)

results.each { bug ->
    def id = bug.getID()
    def summary = bug.summary
    def map = bug.parameterMap
    def fixedInVer = map.cf_fixed_in

    def matcher = (fixedInVer =~ /git-([^\(\)]*)/)
    def gitID = null
    if (matcher.matches()) {
        gitID = matcher[0][1]
    }

    println "Bug: $id"
    println "Link: https://bugzilla.redhat.com/show_bug.cgi?id=$id"
    println "Summary: $summary"
    println "Status: ${bug.status}"
    println "Fixed in Version: $fixedInVer"
    println "Git ID: $gitID"

    if (gitID) {
        if (findCommit(gitID, release)) {
            if (checkingReleaseTag) {
                String comment = "Closing bug ($gitID is ancestor of $release)."
                println comment
                bug.status = 'CLOSED'
                bug.resolution = 'CURRENTRELEASE'
                executeMethod(new UpdateBug(bug, comment))
            } else if (checkingReleaseBranch) {
                String comment = "Marking bug as RELEASE_PENDING ($gitID is ancestor of $release)."
                println comment
                bug.status = 'RELEASE_PENDING'
                executeMethod(new UpdateBug(bug, comment))
            }
        } else {
            println "Ignoring bug; git ID '$gitID' is not an ancestor of $release\n"
        }
    } else if (fixedInVer) {
        System.err.println "Warning: couldn't find git ID (git-*) for bug $id with Fixed in Version: $fixedInVer\n"
    } else {
        System.err.println "Warning: bug $id has no Fixed in Version\n"
    }
}

// finally
//conn.executeMethod(new LogOut());


// Bugzilla methods:

/*
// J2Bugzilla 2.x version:
List search(String status) {
    BugSearch search = new BugSearch(
        new BugSearch.SearchQuery(BugSearch.SearchLimiter.PRODUCT, 'Zanata'),
        new BugSearch.SearchQuery(BugSearch.SearchLimiter.STATUS, status)
    );
    conn.executeMethod(search);
    search.searchResults
}

List search(statuses) {
    List results = new ArrayList()
    statuses.each { results.addAll(search(it)) }
    results
}
*/

List search(List<String> statuses) {
    BugSearch search = new BugSearch(ECSBug.class)
    search.addQueryParam(BugSearch.PRODUCT, 'Zanata')
    search.addQueryParam(BugSearch.STATUS, statuses)
    conn.executeMethod(search)
    search.searchResults
}

void executeMethod(BugzillaMethod method) {
    if (dryRun) {
        System.err.println("dryRun: skipped execution of $method")
    } else {
        conn.executeMethod(method)
    }
}


// Git methods:

boolean findCommit(String commit, String target) {
    // Thanks to http://stackoverflow.com/a/3006203/14379
    def proc1 = ['git', 'merge-base', commit, target].execute(null, gitDir)
    def proc2 = ['git', 'rev-parse', '--verify', commit].execute(null, gitDir)
    proc1.waitFor()
    proc2.waitFor()
    if (proc1.exitValue() != 0) {
        // probably not a valid commit
        return false
        //throw new Exception('git merge-base failed: '+proc1.err.text)
    }
    if (proc2.exitValue() != 0) {
        return false
        //throw new Exception('git rev-parse failed: '+proc2.err.text)
    }
    return proc1.in.text == proc2.in.text
}

boolean isTag(String target) {
    def proc = ['git', 'show-ref', '--tags', target].execute(null, gitDir)
    proc.waitFor()
    return proc.exitValue() == 0
}

boolean isBranch(String target) {
    def proc = ['git', 'show-ref', target].execute(null, gitDir)
    proc.waitFor()
    return proc.exitValue() == 0
}

null
