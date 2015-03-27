#!/bin/env groovy

/*
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
 *
 * Please note that this script is not remotely finished!
 *
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
 */



import groovy.util.XmlParser
import groovy.xml.XmlUtil
import groovy.xml.dom.DOMCategory
import groovy.xml.DOMBuilder
import groovy.xml.MarkupBuilder
import java.security.MessageDigest
import org.w3c.dom.Element


// TODO make these configurable
String fqdn = 'zanata-master-kerberos.lab.eng.bne.redhat.com'
String krbDomain = 'REDHAT.COM'
String javamelodyDir = '/var/lib/zanata/stats'
String hibernateSearchDir = '/var/lib/zanata/index'
String docsDir = '/var/lib/zanata/documents'
String adminUsers = 'admin'
String authEnableKerberos = true

//def scriptDir = new File("${System.properties.'user.home'}/src/zanata-configure-container")
def scriptDir = new File('.')
def input = new File(scriptDir, 'standalone.xml').getText('UTF-8')

def reader = new StringReader(input)
def doc = DOMBuilder.parse(reader)
def root = doc.documentElement
//def root = new XmlParser().parseText(input)

def firstElement(parent) {
    def el = parent.firstChild
    while (el && el.nodeType != org.w3c.dom.Node.ELEMENT_NODE) {
        el = el.nextSibling
    }
    el
}


def newNode = { String ns, String xml ->
    def newDoc = DOMBuilder.parse(new StringReader(
        '<doc xmlns="'+ns+'">'+xml+'</doc>'))

    doc.importNode(firstElement(newDoc.firstChild), true)
}


def replaceChild(parent, oldNode, newNode) {
    if (oldNode) {
        //parent.insertBefore(newNode, oldNode)
        //parent.removeChild(oldNode)
        parent.replaceChild(newNode, oldNode)
    } else {
        parent.appendChild(newNode)
    }
}

def md5(String s) {
    return MessageDigest.getInstance("MD5").digest(s.getBytes("UTF-8"))
}

def md5(Element el) {
    md5(XmlUtil.serialize(el))
}

def oldMD5 = md5(root)
//println oldMD5.encodeHex()
use(DOMCategory) {

    def subsys = root.profile.subsystem

    // Enable connection debugging
    // https://community.jboss.org/wiki/DetectingAndClosingLeakedConnectionsInJBoss71
    def jca = subsys.find{ it.'@xmlns'.startsWith('urn:jboss:domain:jca:') }
    def ccm = jca.'cached-connection-manager'[0]

    ccm['@debug'] = 'true'

    // create security domains
    def domains = subsys.find{ it.'@xmlns'.startsWith('urn:jboss:domain:security:') }.'security-domains'[0]

    def replaceDomain = { String name, String xml ->
        def oldDomain = domains.'security-domain'.find{ it.'@name'.equals(name) }
        def node = newNode(domains.namespaceURI, xml)
        replaceChild(domains, oldDomain, node)
    }

    // security-domain zanata
    replaceDomain('zanata', '''
                <security-domain name="zanata">
                    <authentication>
                        <login-module code="org.zanata.security.ZanataCentralLoginModule" flag="required"/>
                    </authentication>
                </security-domain>
''')

    // (not strictly required for Kerberos)
    replaceDomain('zanata.internal', '''
                <security-domain name="zanata.internal">
                    <authentication>
                        <login-module code="org.jboss.seam.security.jaas.SeamLoginModule" flag="required"/>
                    </authentication>
                </security-domain>
''')

    replaceDomain('zanata.kerberos', '''
                <security-domain name="zanata.kerberos">
                    <authentication>
                        <login-module code="org.jboss.security.negotiation.spnego.SPNEGOLoginModule" flag="sufficient">
                            <module-option name="password-stacking" value="useFirstPass"/>
                            <module-option name="serverSecurityDomain" value="host"/>
                            <module-option name="removeRealmFromPrincipal" value="true"/>
                            <module-option name="usernamePasswordDomain" value="krb5"/>
                        </login-module>
                    </authentication>
                </security-domain>
''')

    replaceDomain('krb5', '''
                <security-domain name="krb5">
                    <authentication>
                        <login-module code="com.sun.security.auth.module.Krb5LoginModule" flag="sufficient">
                            <module-option name="storePass" value="false"/>
                            <module-option name="clearPass" value="true"/>
                            <module-option name="debug" value="true"/>
                            <module-option name="doNotPrompt" value="false"/>
                        </login-module>
                    </authentication>
                </security-domain>
''')

    replaceDomain('host', """
                <security-domain name="host">
                    <authentication>
                        <login-module code="com.sun.security.auth.module.Krb5LoginModule" flag="required">
                            <module-option name="storeKey" value="true"/>
                            <module-option name="useKeyTab" value="true"/>
                            <module-option name="principal" value="HTTP/${fqdn}@${krbDomain}"/>
                            <module-option name="keyTab" value="/usr/share/jbossas/standalone/configuration/jboss.keytab"/>
                            <module-option name="doNotPrompt" value="true"/>
                            <module-option name="debug" value="true"/>
                        </login-module>
                    </authentication>
                </security-domain>
""")

    // TODO jdk module definition for javamelody ??

    // TODO JNDI variables
    // TODO system properties

    // listen on all interfaces
    // TODO make this optional

    def interfaces = root.interfaces.interface
    interfaces.find{ it.'@name' == 'public'}.'inet-address'[0]['@value'] = '${jboss.bind.address:0.0.0.0}'
    interfaces.find{ it.'@name' == 'unsecure'}.'inet-address'[0]['@value'] = '${jboss.bind.address:0.0.0.0}'


/*
  # Change System properties:
  # JavaMelody directory
  # Search Index directory
*/
//        println root.extensions[0].class
/*
    def sysProps = root.'system-properties'
    if (!sysProps[0]) {
        //root.extensions.
        //println root.extensions.class
        sysProps.appendNode('property', [name:'value'])
    }


    println sysProps
*/
//    setSystemProperty('javamelody.storage-directory', '/var/lib/zanata/stats')
//    setSystemProperty('hibernate.search.default.indexBase', '/var/lib/zanata/index')

}

//println root

def newMD5 = md5(root)
def changed = !(oldMD5 == newMD5)
println "Changed: " + changed
if (changed) {
    String pretty = XmlUtil.serialize(root)
    String prettier = pretty.replaceFirst(
        /<\?xml(.*)\?><server/,
        '<?xml$1?>\n\n<server')
    println(prettier)
}
null
