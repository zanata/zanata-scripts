#!/bin/bash

set -e 
set -o pipefail

function print_usage(){
    cat <<END
    $0 -  Test the Installation Guide for Java Client
SYNOPSIS
---------
    $0 [--asciidoc]

DESCRIPTION
------------
    Following the Installation Guide and do the smoke test.

EXIT STATUS
------------
    ${EXIT_CODE_OK} if all tests passed
    ${EXIT_CODE_INVALID_ARGUMENTS} invalid or missing arguments
    ${EXIT_CODE_FAILED} at least one of test not passed

ENVIRONMENT
------------
END
    print_variables usage $0
}

function def_var(){
    if [[ -z $(eval echo \$$1) ]];then
        if [[ -z "$2" ]];then
            export $1=
        else
            export $1="$2"
        fi
    fi
}


#### Start Var
def_var author "Ding-Yi Chen"
def_var revdate 2015-05-14
def_var revnumber 3
def_var numbered
def_var toc2
def_var ext-relative adoc

### The command for package management system
def_var PACKAGE_SYSTEM_COMMAND yum

### The command to install a package in updates-testing
def_var PACKAGE_INSTALL_UPDATE_REPO_COMMAND "${PACKAGE_SYSTEM_COMMAND} -y install --enablerepo=updates-testing"

### The JBoss stanalone dir
def_var JBOSS_STANDALONE_DIR /var/lib/jbossas/standalone

### :STANDALONE_XML: {JBOSS_STANDALONE_DIR}/configuration/standalone.xml
def_var STANDALONE_XML "${JBOSS_STANDALONE_DIR}/configuration/standalone.xml"

### :DEPLOYMENTS_DIR: {JBOSS_STANDALONE_DIR}/deployments
def_var DEPLOYMENTS_DIR "${JBOSS_STANDALONE_DIR}/deployments"

### :ZANATA_DS_XML: {DEPLOYMENTS_DIR}/zanata-ds.xml
def_var ZANATA_DS_XML "${DEPLOYMENTS_DIR}/zanata-ds.xml"

### :JBOSS_HOME: /usr/share/jbossas
def_var JBOSS_HOME /usr/share/jbossas

### :MODULE_XML: {JBOSS_HOME}/modules/system/layers/base/sun/jdk/main/module.xml
def_var MODULE_XML "${JBOSS_HOME}/modules/system/layers/base/sun/jdk/main/module.xml"

### :ZANATA_HOME: /var/lib/zanata
def_var ZANATA_HOME /var/lib/zanata

### :ZANATA_DOCUMENT_STORAGE_DIRECTORY: {ZANATA_HOME}/documents
def_var ZANATA_DOCUMENT_STORAGE_DIRECTORY "${ZANATA_HOME}/documents"

### :ZANATA_DB_USER: zanata
def_var ZANATA_DB_USER "${ZANATA_DB_USER}/documents"

### :ZANATA_DB_PASS: zanata
def_var ZANATA_DB_PASS zanata

### :ZANATA_EHCACHE_DIR: {ZANATA_HOME}/ehcache
def_var ZANATA_EHCACHE_DIR "${ZANATA_HOME}/ehcache"

### :ZANATA_WAR_DOWNLOAD_URL: http://sourceforge.net/projects/zanata/files/latest/download?source=files
def_var ZANATA_WAR_DOWNLOAD_URL "http://sourceforge.net/projects/zanata/files/latest/download?source=files"

#### End Var

#===== Start Guide Functions =====

## Exit status
export EXIT_CODE_OK=0
export EXIT_CODE_INVALID_ARGUMENTS=3
export EXIT_CODE_DEPENDENCY_MISSING=4
export EXIT_CODE_ERROR=5
export EXIT_CODE_FAILED=6
export EXIT_CODE_SKIPPED=7
export EXIT_CODE_FATAL=125


function extract_variable(){
    local file=$1
    local nameFilter=$2
    awk -v nameFilter="$nameFilter" \
	'BEGIN {FPAT = "(\"[^\"]+\")|(\\(.+\\))|([^ ]+)"; start=0; descr=""} \
	/^#### End Var/ { start=0} \
	(start==1 && /^[^#]/ && $2 ~ nameFilter) { sub(/^\"/, "", $3); sub(/\"$/, "", $3); print $2 "\t" $3 "\t" descr ; descr="";} \
	(start==1 && /^###/) { gsub("^###[ ]?","", $0) ; descr=$0} \
	/^#### Start Var/ { start=1; } ' $file
}

function print_variables(){
    local format=$1
    local file=$2
    case $format in
	asciidoc )
	    extract_variable $file | awk -F '\\t' 'BEGIN { done=0 } \
		$2 ~ /^\$\{.*:[=-]/ { ret=gensub(/^\$\{.*:[=-](.+)\}/, "\\1", "g", $2) ; print ":" $1 ": " ret; done=1 }\
		done==0  {print ":" $1 ": " $2 ; done=1 }\
		done==1  {done=0}'
	    ;;
	bash )
	    extract_variable $file "^[A-Z]" | awk -F '\\t' \
		'$2 ~ /[^\)]$/ {print "export " $1 "=\""$2"\"" ;} \
		$2 ~ /\)$/ {print "export " $1 "="$2 ;} '
	    ;;
	usage )
	    extract_variable $file "^[A-Z]" | awk -F '\\t' '{print $1 "::"; \
		if ( $3 != "" ) {print "    " $3  }; \
		print "    Default: " $2 "\n"}'
	    ;;	    
	* )
	    ;;
    esac
}

function to_asciidoc(){  
    print_variables asciidoc $0
    # Extract variable

    awk 'BEGIN {start=0;sh_start=0; in_list=0} \
	/^#### End Doc/ { start=0} \
	(start==1 && /^[^#]/ ) { if (sh_start==0) {sh_start=1; if (in_list ==1 ) {print "+"}; print "[source,sh]"; print "----"} print $0;} \
	(start==1 && /^### \./ ) { in_list=1 } \
	(start==1 && /^###/ ) { if (sh_start==1) {sh_start=0; print "----"} gsub("^###[ ]?","", $0) ; print $0;} \
	/^#### Start Doc/ { start=1; } ' $0
    echo "== Default Environment Variables"
    echo "[source,sh]"
    echo "----"
    # Extract variable
    print_variables bash $0
    echo "----"
}

while [ -n "$1" ];do
    case $1 in
	--asciidoc )
	    to_asciidoc
	    exit 0
	    ;;
	--help | -h )
	    print_usage
	    exit 0
	    ;;
	* )
	    echo "Invalid argument $1" > /dev/stderr
	    exit ${EXIT_CODE_INVALID_ARGUMENTS}
	    ;;
    esac
    shift
done
#===== End Guide Functions =====

#### Start Doc
### = Installation Guide
###
### Version {revnumber},{revdate}
### 
### This document shows the steps to install Zanata-3.X on
### JBoss Enterprise Application Platform (EAP) 6.2.X,
### MySQL, and
### Red Hat Enterprise Linux (RHEL) 6.X. 
### Please make corresponding changes for other configuration.
### 
### == Preparation
### === Install JBoss
### You can obtain JBoss EAP from the yum repositories from RHN, 
if [ ! -e $JBOSS_HOME ];then
    sudo yum -y groupinstall jboss-eap6
fi
###
### or download from 
### http://www.jboss.org/jbossas/downloads/[JBoss Application Server 7]
### and follow the instruction of JBoss Quick Starts.
###
### We assume that JBoss deployment directory is located in +{DEPLOYMENTS_DIR}+,
### and standalone.xml is located in +{STANDALONE_XML}+.
###
### Set the following environment variable 
### [source,sh]
### [subs="attributes"]
### ----
### DEPLOYMENTS_DIR={deployments_dir}
### MODULE_XML={module_xml}
### STANDALONE_XML={standalone_xml}
### ZANATA_DB_USER={zanata_db_user}
### ZANATA_DB_PASS={zanata_db_pass}
### ZANATA_HOME={zanata_home}
### ZANATA_EHCACHE_DIR={zanata_ehcache_dir}
### ZANATA_WAR_DOWNLOAD_URL={zanata_war_download_url}
### ----
###
### === Install MySQL and driver
### Install MySQL server, client and java connector:
function install_missing(){
    _pkg=
    for p in $@; do
	if ! rpm -q $p &>/dev/null ;then
	    _pkg="$_pkg $p"
	fi
    done
    if [ -n "$_pkg" ];then
	sudo yum -y install $_pkg
    fi
}
install_missing mysql mysql-server mysql-connector-java
sudo ln -sf /usr/share/java/mysql-connector-java.jar $DEPLOYMENTS_DIR/mysql-connector-java.jar
###
### === Install Virus Scanner (Optional)
### To prevent virus infected document being uploaded, Zanata is capable of working with clamav.
### If clamav is not installed, a warning will be logged when files are uploaded.
### If clamav is installed but +clamd+ is not running, 
### Zanata may reject all uploaded files (depending on file type).  To install and run clamav:
# Assuming the function install_missing() is still available
if [ -e /usr/bin/systemctl ];then
    install_missing clamav-server clamav-scanner-systemd
    sudo systemctl enable clamd@scan
    sudo systemctl start clamd@scan
else
    install_missing clamd
    sudo chkconfig clamd on
    if ! service clamd status ;then
	sudo service clamd start
    fi
fi
###
### You should probably also ensure that freshclam is set to run at least once per day,
### to keep virus definitions up to date.
### The clamav package will probably do this for you, but you can check by looking for +/etc/cron.daily/freshclam+.
### To override the default behaviour above, you can set the system property +virusScanner+ when running the server. 
### +DISABLED+ means no virus scanning will be performed; all files will be assumed safe. 
### Any other value will be treated as the name of a virus scanner command: the command will be called with the name of a file to scan.
###
### === Install Fonts
### Some administration functions (ie JavaMelody) 
### are partially localized, so you may need to install, 
### for example, Chinese fonts on server for Chinese administrators by 
### using following command:
install_missing cjkuni-ukai-fonts cjkuni-uming-fonts
###
### == Installation
### === Create Zanata Home
### Zanata home hosts the documents, indexes, statistics and so on.
### Note that it should be owned by +jboss+.
sudo mkdir -p ${ZANATA_HOME}
sudo chown -R jboss:jboss ${ZANATA_HOME}
### === Configure Database
### Ensure MySQL is started.
if ! sudo bash -c "service mysqld status"; then 
    sudo bash -c "service mysqld start"
fi
###
### You may want to use user +{zanata_db_user}+  to access Zanata.
if [ "${ZANATA_DB_USER}" == "$(sudo mysql -B -N  -u root -e "SELECT User FROM mysql.user WHERE User='$ZANATA_DB_USER'")" ];then
    echo "[mysql] User ${ZANATA_DB_USER} is already created." > /dev/stderr
else
    sudo mysql -u root -e "CREATE USER '$ZANATA_DB_USER'@'localhost' IDENTIFIED BY '$ZANATA_DB_PASS'" mysql
    sudo mysql -u root -e "GRANT ALL ON zanata.* TO '$ZANATA_DB_USER'@'localhost'" mysql
fi


###
### To store multilingual text, Zanata database should be capable of dealing with UTF8 ### 
sudo mysql -u $ZANATA_DB_USER -p$ZANATA_DB_PASS -e "CREATE DATABASE zanata DEFAULT CHARACTER SET='utf8';"
###
### === Configure JBoss
### Prior configure JBoss, especially modifing +{standalone_xml}+ it is recommend to stop the jboss service by
if sudo bash -c "service jbossas status"; then 
    sudo bash -c "service jbossas stop"
fi
### Otherwise, JBoss might overwrite +{standalone_xml}+ with existing settings.
####
### For quick setup, download  following example configuration files:
### 
### * https://raw.github.com/wiki/zanata/zanata-server/standalone-zanata-release-openid.xml[standalone.xml]: Example of JBoss setting for internal and openid authentication. 
###   Copy this to +{standalone_xml}+.
### * https://raw.github.com/wiki/zanata/zanata-server/zanata-ds.xml[zanata-ds.xml]: Example of setting MySQL as data source
###   Copy this to +{zanata_ds_xml}+
### * https://raw.github.com/wiki/zanata/zanata-server/module-javamelody.xml[module.xml]: Example for setting Java melody.
###   Copy this to +{module_xml}+
###
### Scripts to achieve above:
wget -c -O /tmp/standalone-zanata-release-openid.xml https://raw.github.com/wiki/zanata/zanata-server/standalone-zanata-release-openid.xml
sudo bash -c "sed -e \"s|/var/lib/zanata|$ZANATA_HOME|\" /tmp/standalone-zanata-release-openid.xml  > $STANDALONE_XML"
sudo chown jboss:jboss $STANDALONE_XML
wget -c -O /tmp/zanata-ds.xml https://raw.github.com/wiki/zanata/zanata-server/zanata-ds.xml
sudo bash -c "sed -e \"s/ZANATA_DB_USER/$ZANATA_DB_USER/\" /tmp/zanata-ds.xml | sed -e \"s/ZANATA_DB_PASS/$ZANATA_DB_PASS/\" > $ZANATA_DS_XML"
sudo chown jboss:jboss $ZANATA_DS_XML
wget -c -O /tmp/module-javamelody.xml https://raw.github.com/wiki/zanata/zanata-server/module-javamelody.xml
sudo cp /tmp/module-javamelody.xml $MODULE_XML
sudo chown jboss:jboss $MODULE_XML
###
### ==== Configure Data Source
### This can be done by either one of following methods:
###
### . Edit zanata-ds.xml
### . JBoss administration console
### . Edit standalone.xml
### 
### Method 1 is recommended, as it is easier to maintain to be persist when upgrading the JBoss.
### 
### ===== Edit zanata-ds.xml
### In +{zanata_ds_xml}+, edit:
###
### [source,xml]
### <?xml version="1.0" encoding="UTF-8"?>
### <!-- http://docs.jboss.org/ironjacamar/schema/datasources_1_0.xsd -->
### <!--
### Using this datasource:
### 1. create a jboss module for mysql-connector and activate it using jboss-cli.sh
### 2. save this datasource as JBOSS_HOME/standalone/deployments/zanata-ds.xml
### See http://jaitechwriteups.blogspot.com/2012/02/jboss-as-710final-thunder-released-java.html
### -->
### <datasources>
###    <datasource jndi-name="java:jboss/datasources/zanataDatasource" enabled="true" use-java-context="true" pool-name="zanataDatasource">
###        <connection-url>jdbc:mysql://localhost:3306/zanata?characterEncoding=UTF-8</connection-url>
###        <driver>mysql-connector-java.jar</driver>
###        <security>
###            <user-name>$ZANATA_DB_USER</user-name>
###            <password>$ZANATA_DB_PASS</password>
###        </security>
###     </datasource>
### </datasources>
### 
### ===== http://docs.jboss.org/jbossas/6/Admin_Console_Guide/en-US/html/Administration_Console_User_Guide-Accessing_the_Console.html[JBoss Administration Console]
###
### . Login with administrator role
### . Click *Profiles* on the top tabs.
### . Expand *Subsystems* on the left panel.
### . Expand *Datasources* on the left panel.
### . Add datasource
### .. Click *Add*
### .. Type `zanataDatasource` in *Name*
### .. Type `java:jboss/datasources/zanataDatasource` in *JNDI*
### .. Click *Next*
### .. Select *mysql* as driver.
### .. Click *Next*. The data under *Attributes* should be filled accordingly.
### . Edit *Connection*
### .. Click *Connection*
### .. Click *Edit*
### .. Type `jdbc:mysql://localhost:3306/zanata?characterEncoding=UTF-8` in *Connection URL*.
### .. Click *Save*
### . Enable zanataDatasource:
### .. Select `zanataDatasource` in Table *Available Datasources*
### .. Click *Enable*
### . Test datasource
### .. Click *Connection*
### .. Click *Test Connection*
###
### ==== Edit standalone.xml
### In +{standalone_xml}+, search subsystem `<datasources>` and inserts the following after that tag:
### [source,xml]
### <datasource jta="false" jndi-name="java:jboss/datasources/zanataDatasource" pool-name="zanataDatasource" enabled="true" use-java-context="true" use-ccm="false">
###   <connection-url>jdbc:mysql://localhost:3306/zanata?characterEncoding=UTF-8</connection-url>
###   <driver-class>com.mysql.jdbc.Driver</driver-class>
###   <driver>mysql-connector-java.jar</driver>
###   <security>
###     <user-name>$ZANATA_DB_USER</user-name>  # <1>
### 	<password>$ZANATA_DB_PASS</password>    # <2>
###    </security>
###    <validation>
###      <validate-on-match>false</validate-on-match>
###      <background-validation>false</background-validation>
###    </validation>
###    <statement>
###      <share-prepared-statements>false</share-prepared-statements>
###    </statement>
### </datasource>
### 
### <1> Replace +$ZANATA_DB_USER+ with your username.
### <2> Replace +$ZANATA_DB_PASS+ with your password.
###
### ==== Configure JNDI
### In +{standalone_xml}+, search subsystem `xmlns="urn:jboss:domain:naming:"` and add bindings as following. Adjust the value accordingly. 
### [source,xml]
### <subsystem xmlns="urn:jboss:domain:naming:{namingVer}">
###   <bindings>           
###     <simple name="java:global/zanata/files/document-storage-directory" value="{ZANATA_DOCUMENT_STORAGE_DIRECTORY}"/> # <1>
###     <simple name="java:global/zanata/security/auth-policy-names/internal" value="zanata.internal"/>        # <2> 
###     <simple name="java:global/zanata/security/auth-policy-names/openid" value="zanata.openid"/>            # <3>
###     <simple name="java:global/zanata/security/admin-users" value="admin"/>                                 # <4>
###     <simple name="java:global/zanata/email/default-from-address" value="no-reply@zanata.org"/>             # <5>
###   </bindings>
###   <remote-naming/>
### </subsystem>
### 
### <1> link:Document-Storage-Directory{ext-relative}[]
### <2> Remove this line to disable internal authentication.
### <3> Remove this line to disable OpenId authentication.
### <4> Replace +admin+ with the lists of users that will become the admin once they finished registration. Use with care!
### <5> Replace +no-reply@zanata.org+ with the email address you want your user to see as "From:".
###
### Please refer to source code in 
### https://github.com/zanata/zanata-server/blob/master/zanata-war/src/main/java/org/zanata/config/JndiBackedConfig.java[org.zanata.config.JndiBackedConfig].
### for other JDNI configuration options.
###
### ==== System properties
### In +{standalone_xml}+, insert following after +'</extenstion>'
### <system-properties>
###     <property name="hibernate.search.default.indexBase" value="${user.home}/indexes"/>
###     <property name="ehcache.disk.store.dir" value="/var/lib/zanata/ehcache"/>
### </system-properties>
###
### ==== JavaMelody
### JavaMelody is for monitoring Java or Java EE application servers.
###
### In section +<system-properties>+ in +{standalone_xml}+, insert following:
### [source,xml]
### <system-properties>
###        ...
###     <property name="javamelody.storage-directory" value="${user.home}/stats"/>
### </system-properties>
###
### Also insert the following immediately after +<paths>+
### [source,xml]
### <path name="com/sun/management"/>
###
### ==== Security Domains
### Insert following under element +<security-domains>+:
### [source,xml]
### <security-domains>
###     ...
###     <security-domain name="zanata">
###         <authentication>
###             <login-module code="org.zanata.security.ZanataCentralLoginModule" flag="required"/>
###         </authentication>
###     </security-domain>
###     <security-domain name="zanata.openid">
###         <authentication>
###             <login-module code="org.zanata.security.OpenIdLoginModule" flag="required"/>
###         </authentication>
###     </security-domain>
###     <security-domain name="zanata.internal">
###         <authentication>
###             <login-module code="org.jboss.seam.security.jaas.SeamLoginModule" flag="required"/>
###         </authentication>
###     </security-domain>
###     ...
### </security-domains>
###
### === Install zanata.war
### http://sourceforge.net/projects/zanata/Download zanata.war[Download zanata.war], then copy it to `/etc/jbossas/deployments/zanata.war`. Such as:
wget -c -O /tmp/zanata-latest.war $ZANATA_WAR_DOWNLOAD_URL
sudo cp /tmp/zanata-latest.war $DEPLOYMENTS_DIR/zanata.war
###
### [NOTE]
### By default, the filename of the war file in {deployments_dir} determines the URL of your zanata server.
### In other word, if your war file is +zanata-3.0.war+, your zanata server URL is +http://<zanataHost>:8080/zanata-3.0+.
### Rename the +zanata.war+ to +ROOT.war+ 
### should make the Zanata home page become:
### +http://<zanataHost>:8080+
### 
### == Run Zanata Server
### Start the zanata server by start the jbossas services:
sudo bash -c "service jbossas start"
### 
### If zanata server start successfully, Zanata server home page is at:
http://<zanataHost>:8080/zanata
### 
### == Other Things That Might Help
### === zanata-setup.sh
### https://raw.github.com/zanata/zanata-scripts/master/zanata-setup.sh[zanata-setup.sh] 
### is a script to execute the steps mentioned above.
### Download it and run it with user that is able to sudo:
### [source,sh]
### ----
###  ./zanata-setup.sh
### ----
###  
### === +{jboss_home}/bin/standalone.conf+
### * To increase memory for classes (and multiple redeployments), change `-XX:MaxPermSize=256m` to 
### ----
### -XX:MaxPermSize=512m
### ----
###
### * To enable debugging, uncomment 
### ----
### JAVA_OPTS="$JAVA_OPTS -Xrunjdwp:transport=dt_socket,address=8787,server=y,suspend=n"
### ----
###
### * To fix the JBoss EAP 6 problem where most of the logging is missing, add this line:
### ----
### JAVA_OPTS="$JAVA_OPTS -Dorg.jboss.as.logging.per-deployment=false"
### ----
###
### === JBoss Administration Console
### . To create an JBoss Admin user, run following command and follow the instruction:
### [source,sh]
### /usr/share/jbossas/bin/add-user.sh
###
### . To login the JBoss Administration Console, use the following URL:
http://<Host>:9990/
###
#### End Doc
