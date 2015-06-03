#!/bin/bash

function print_usage(){
    cat <<END
NAME 
    zanata-profile-switcher.sh switch zanata running profile

SYNOPSIS
    zanata-profile-switcher.sh <profile>

DESCRIPTION
    This program will stop JBoss, copy files of each profile
END
}

if [ $# -eq -0 ];then
    print_usage
    exit 0
fi

PROFILE=$1

: ${STANDALONE_XML:=/etc/jbossas/standalone/standalone.xml}
: ${ZANATA_DS_XML:=/var/lib/jbossas/standalone/deployments/zanata-ds.xml}

PROFILE_MANAGED_FILES=( ${STANDALONE_XML} ${ZANATA_DS_XML})

for file in "${PROFILE_MANAGED_FILES[@]}"; do
    parentDir=$(dirname $file)
    filename=$(basename $file)
    newFile=${parentDir}/${filename}.${PROFILE} 
    if sudo test -r ${newFile} ;then
        sudo cp -v  ${file} ${file}.bak
	sudo cp -v ${newFile} ${file}
    else
	echo "${newFile} not found, skip" >/dev/stderr
    fi
done
