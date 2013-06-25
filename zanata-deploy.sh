#!/bin/bash -ex

# Script: zanata-deploy.sh
# Authors: sflaniga@redhat.com, camunoz@redhat.com

# This script deploys zanata.war from the local Maven repo
# to a target machine, based on a Jenkins job name
# and some configuration variables read from ~/.config/zanata-deploy.conf.

# Requirements:

# 1. env var WARNING_EMAIL must be set via zanata-deploy.conf
# 2. Jenkins vars BUILD_TAG, JOB_NAME, GIT_BRANCH set by Jenkins
# NB Jenkins will only set $GIT_BRANCH if the build config specifies a single branch
# 3. Jenkins job name should look like zanata-VER-PROFILE or zanata-build-deploy-VER-PROFILE
# 4. set m2repo or srcdir if you want to override defaults
# 5. minimal zanata-deploy.conf should look something like this:
#
# master_version=1.5
# host_1_4_jaas=jaastest.example.com
# host_1_4_internal=internaltest.example.com
# NB replace . with _ in variable names

# Each target box should be set up in a certain way.  
# See the default values for url, user, service and targetfile near the
# end of this script, or override them for each affected host, eg:
# host_1_5_special=specialcase.example.com
# url_1_5_special=https://specialcase.example.com/
# user_1_5_special=jenkins
# service_1_5_special="sudo /etc/init.d/jbossas"
# targetfile_1_5_special="/opt/jboss-as/server/default/deploy/ROOT.war"


if [ -L $0 ] ; then
    ME=$(readlink $0)
else
    ME=$0
fi
DIR=$(dirname $ME)

source $HOME/.config/zanata-deploy.conf

BUILD_TAG=${BUILD_TAG-<unknown build>}
JOB_NAME=${JOB_NAME-<unknown job>}
WARNING_EMAIL=${WARNING_EMAIL-test@example.com}
JBOSS_HOME=${JBOSS_HOME-/usr/share/jbossas/}
#JBOSS_PROFILE=${JBOSS_PROFILE-production}
ssh=${ssh-ssh}
scp=${scp-scp}
mail=${mail-mail}
m2repo=${m2repo-$HOME/.m2/repository}
BUILD_TYPES=(autotest internal kerberos fedora jaas)

# functions:

die() {
   echo "zanata-deploy: $1" >&2
   echo "zanata-deploy: $1" | $mail -s "zanata-deploy error" $WARNING_EMAIL
   exit 0
}

arrayGet() { 
    local array=$1 index=$2
    local i="${array}_${index}"
    echo "${!i}"
}

warn() {
    echo "WARNING: $1"
}


# main:

echo "BUILD_TAG: $BUILD_TAG"
echo "GIT_BRANCH: $GIT_BRANCH"

#if [[ $JOB_NAME =~ zanata-((build-)?deploy-)?(([^-][^-]*)-)?(.*) ]]; then
   #branch_name=${BASH_REMATCH[3]}
   #echo "${BASH_REMATCH[0]}"
   #echo "${BASH_REMATCH[1]}"
   #echo "${BASH_REMATCH[2]}"
   #echo "${BASH_REMATCH[3]}" # version
   #echo "${BASH_REMATCH[4]}" # type
#else
   #die "can't find type of build for job name $JOB_NAME, for $BUILD_TAG"
#fi

branch_name=$GIT_BRANCH

if [[ "$branch_name" == "" ]]; then
  die "can't determine branch name for $BUILD_TAG"
fi

if [[ "$branch_name" == "master" ]]; then
   version=$master_version
else
   version=$branch_name
fi
srcdir=${srcdir-${m2repo}/org/zanata/zanata-war/${version}-SNAPSHOT}

echo "branch: $branch_name"
echo "version: $version"
echo "srcdir: $srcdir"

# replace . with _ in version:
ver=${version//./_}

# attempt to deploy for each authentication type
for buildType in "${BUILD_TYPES[@]}"
do
   host=$(arrayGet host ${ver}_${buildType})
   
   if [[ -z $host ]]; then
     warn "no host configured for version $ver, type $buildType, and build $BUILD_TAG"

   elif [[ "$host" != "skip" ]]; then

      echo "=================================================================================="
      echo "Deploying: version $ver type $buildType"
      echo "=================================================================================="

      url=$(arrayGet url ${ver}_${buildType})
      if [[ -z $url ]]; then
         url=http://$host:8080/
      fi

      user=$(arrayGet user ${ver}_${buildType})
      if [[ -z $user ]]; then
         user=jboss
      fi

      service=$(arrayGet service ${ver}_${buildType})
      if [[ -z $service ]]; then
#         service="JBOSS_USER=RUNASIS /etc/init.d/jbossas"
	service="service jbossas"
      fi

      targetfile=$(arrayGet targetfile ${ver}_${buildType})
      if [[ -z $targetfile ]]; then
         targetfile=$JBOSS_HOME/standalone/deployments/ROOT.war
      fi

      if [[ $targetfile =~ (.*)/deployments/.* ]]; then
         logfile=${BASH_REMATCH[1]}/log/server.log
      else
         logfile=/dev/null
      fi

      post_stop=$(arrayGet post_stop ${ver}_${buildType})


      echo "host: $host"
      echo "url: $url"
      echo "user: $user"
      echo "service: $service"
      echo "targetfile: $targetfile"
      echo "post_stop: $post_stop"
      echo "logfile: $logfile"

      echo "stopping app server on $host:"
      if ! $ssh $user@$host $service stop
         then echo "$server stop failed (server not running?); ignoring error"
      fi

      if [[ -n $post_stop ]]; then
         $ssh $user@$host $post_stop
      fi

      # tmp dir will grow forever otherwise:
      $ssh $user@$host rm -fr $JBOSS_HOME/standalone/tmp/

      warfile=${srcdir}/zanata-war-*.war

      echo "copying $warfile to $host:$targetfile"
      $scp $warfile $user@$host:$targetfile
      echo "starting app server on $host"
      $ssh $user@$host $service start

   fi
done

# Check that each server is up and running
for buildType in "${BUILD_TYPES[@]}"
do

   host=$(arrayGet host ${ver}_${buildType})

   if [[ -z $host ]]; then
     warn "no host configured for version $ver, type $buildType, and build $BUILD_TAG"

   elif [[ "$host" != "skip" ]]; then
     echo "=================================================================================="
     echo "Checking host: $host"
     echo "=================================================================================="

     url=$(arrayGet url ${ver}_${buildType})
     if [[ -z $url ]]; then
        url=http://$host:8080/
     fi

     user=$(arrayGet user ${ver}_${buildType})
     if [[ -z $user ]]; then
        user=jboss
     fi

     if [[ $targetfile =~ (.*)/deployments/.* ]]; then
        logfile=${BASH_REMATCH[1]}/log/server.log
     else
        logfile=/dev/null
     fi

   
     if $DIR/is_server_up.sh $url ; then
        echo "$url has started up; log tail follows:"
        ssh $user@$host tail $logfile
     else
        echo "$url has failed to start; log tail follows:"
        ssh $user@$host tail -400 $logfile
        exit 1
     fi
   fi
done
