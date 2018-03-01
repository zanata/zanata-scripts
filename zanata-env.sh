## Define environment variables
## This script is meant to be sourced.

###
### EXIT_STATUS
###     Success:
###         EXIT_OK (0)
declare -i EXIT_OK=0

###
###     Fatal that should stop immediately:
###         EXIT_FATAL_UNSPECIFIED (1)
###             Unspecified fatal error,
###             usually indicate a bug in our scripts.
declare -i EXIT_FATAL_UNSPECIFIED=1

###         EXIT_FATAL_INVALID_OPTIONS (3)
###             Wrong options were given.
declare -i EXIT_FATAL_INVALID_OPTIONS=3

###         EXIT_FATAL_MISSING_DEPENDENCY (4)
###             Cannot find dependencY.
declare -i EXIT_FATAL_MISSING_DEPENDENCY=4

###         EXIT_FATAL_UNKNOWN_MODULE (5)
###             Invalid or unknown module or repository name.
declare -i EXIT_FATAL_UNKNOWN_MODULE=5

###         EXIT_FATAL_FAIL (6)
###             Script detected that a fatal error occurred.
declare -i EXIT_FATAL_FAIL=6

###         EXIT_FATAL_INVALID_ARGUMENTS (7)
###             Invalid arguments.
declare -i EXIT_FATAL_INVALID_ARGUMENTS=7

###         EXIT_FATAL_GIT_FAILED (8)
###             Git related failed
declare -i EXIT_FATAL_GIT_FAILED=8

###
###     Error that need to stop before next stage:
###         EXIT_ERROR_FAIL (20)
###             Script detected that an error occurred.
declare -i EXIT_ERROR_FAIL=20

###         EXIT_ERROR_UNKNOWN_VERSION (21)
###             The specified version is unknown.
declare -i EXIT_ERROR_UNKNOWN_VERSION=21


###
###     Return value, not errors:
###         EXIT_RETURN_FALSE (40)
###             Indicate the program did not have error, nor failed,
###             just not doing what you might hope it to do.
###             For example, zanata-release-notes-prepend returns EXIT_RETURN_FALSE
###             when the version-name exists, but no issues.
declare -i EXIT_RETURN_FALSE=40

###
### ENVIRONMENT
###     M2_REPOSITORY_DIR
###         Repository for maven
###         Default: ${HOME}/.m2/repository
: ${M2_REPOSITORY_DIR:=~/.m2/repository}
export M2_REPOSITORY_DIR

###
###     TMP_ROOT
###         Root of temporary directories and files, and expected to be clean
###         Default: /tmp/zanata
: ${TMP_ROOT:=/tmp/zanata}
export TMP_ROOT

###
###     REPO_LOCAL_DIR
###         Temporary maven repo
###         This should NOT be your normal work maven repo
###         Default: /tmp/maven-central-release-repo
: ${REPO_LOCAL_DIR:=${TMP_ROOT}/maven-central-release-repo}
export REPO_LOCAL_DIR

###
###     WORK_ROOT
###         Root of working directories, whose content is expected to be changed by scripts.
###         So normally this should NOT be your development directory.
###         You can also clean it by removing it, it should rebuild when running any scripts that use it.
###         Default: ${HOME}/zanata-work-root
: ${WORK_ROOT:=~/zanata-work-root}
export WORK_ROOT

###
###     ZANATA_GIT_URL_PREFIX
###         Prefix of Zanata Git URL
###         Default: git@github.com:zanata
: ${ZANATA_GIT_URL_PREFIX:=git@github.com:zanata}
export ZANATA_GIT_URL_PREFIX

MAVEN_COMMON_OPTIONS="-e -T 1"

MAVEN_RELEASE_OPTIONS="-Dallow.deploy.skip=false -Dcheckstyle.skip=true -Denforcer.skip=true -Dfindbugs.skip=true -Dgpg.executable=gpg2 -Dgpg.useagent=true -Doptimise -DskipArqTests=true -DskipFuncTests=true -DskipTests=true -DupdateReleaseInfo=true"

###
###     MAVEN_NEXUS_STAGING_PLUGIN
###          Maven plugin for nexus staging
MAVEN_NEXUS_STAGING_PLUGIN="org.sonatype.plugins:nexus-staging-maven-plugin"

###     MAVEN_NEXUS_STAGING_OPTIONS
###          The maven options for nexus plugin
MAVEN_NEXUS_STAGING_OPTIONS="-DnexusUrl=https://oss.sonatype.org/ -DserverId=sonatype-staging"

## zanata-platform
PLATFORM_MAVEN_VERSION_PROJECT="build-tools,parent"
PLATFORM_MAVEN_NEXUS_RELEASE_PROJECTS="!server/zanata-test-war,!server/functional-test"
PLATFORM_MAVEN_RELEASE_PROFILES="release"
PLATFORM_STAGING_REPOSITORY="orgzanata"
PLATFORM_RELEASE_NOTES_FILE="docs/release-notes.md"

## jgettext
JGETTEXT_STAGING_REPOSITORY="orgfedorahostedtennera"
JGETTEXT_MAVEN_RELEASE_PROFILES="release"

## openprops
OPENPROPS_STAGING_REPOSITORY="orgfedorahostedopenprops"
OPENPROPS_MAVEN_RELEASE_PROFILES="release"

