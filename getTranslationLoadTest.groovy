#!/usr/bin/env groovy
package org.zanata.adhoc

@Grab(group='org.codehaus.groovy.modules.http-builder', module='http-builder', version='0.7')

import groovyx.net.http.RESTClient

def cli = new CliBuilder(usage:'get translation from zanata (sort of load testing)')
cli.h(longOpt: 'help', 'print help')
cli._(longOpt: 'url', args: 1, 'zanata url (default http://localhost:8080/zanata)')
cli.p(longOpt: 'project', args: 1, 'targeting project (default skynet-topics)')
cli.i(longOpt: 'project-version', args: 1, 'targeting project version (default 1)')
cli.u(longOpt: 'username', args: 1, 'username (default admin)')
cli.k(longOpt: 'apiKey', args: 1, 'API key (default b6d7044e9ee3b2447c28fb7c50d86d98)')

def options = cli.parse(args)

if (options.help) {
    cli.usage()
    System.exit(1)
}

def zanataInstance = options.url ?: "http://localhost:8080/zanata"
def zanataRestUrl = "$zanataInstance/rest/"

def zanataRestClient = new RESTClient(zanataRestUrl, "application/xml")
zanataRestClient.handler.failure = {
    it
}

def projectSlug = options.p ?: 'skynet-topics'
def versionSlug = options.i ?: '1'
def authHeaders = ['X-Auth-User': "admin", 'X-Auth-Token': "b6d7044e9ee3b2447c28fb7c50d86d98"]

// get all resource names
def resourcePath = "projects/p/$projectSlug/iterations/i/$versionSlug/r"
def response = zanataRestClient.get(headers: authHeaders, path : resourcePath)
assert response.status == 200 : "Error getting resource for $projectSlug/$versionSlug at $resourcePath"

def namespaces = ['http://zanata.org/namespace/api/': 'api']
def resources = response.data.declareNamespace(namespaces)
def names = resources.'resource-meta'.collect {
    it.name
}

println "resource names: $names"

// get all available locales
def statsResponse = zanataRestClient.get(headers: authHeaders, path: "stats/proj/$projectSlug/iter/$versionSlug")
assert statsResponse.status == 200 : "Error getting statistics for $projectSlug/$versionSlug"

def locales = statsResponse.data.declareNamespace(namespaces).stats.stat.'@locale'.collect {
    it
}

println "locales: $locales"

// get translations
println "getting translations for all these locales and resources"
locales.each { locale ->
    names.each { resId ->
        def msg = "getting translation for $resId for locale $locale"
        def resp = zanataRestClient.get(headers: authHeaders, path: "$resourcePath/$resId/translations/$locale")
        // we don't really care the response content
        println "$msg -> $resp.status"
    }
}
