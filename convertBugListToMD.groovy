#!/usr/bin/groovy

import java.util.regex.Matcher

// Download a csv from bugzilla with column 1 as bug number, column 2 as bug summary.
// Run this script with the csv file as argument and it will print output in markdown format to screen. 
// You may pipe it to a file or clipboard.
File bugList = new File(args[0])

assert bugList.exists()

bugList.readLines().each {
    Matcher matcher = it =~ /^(\d+)\s(.+)/
    if (matcher) {
        def bugNumber = matcher[0][1]
        def bugSummary = matcher[0][2]
        println "* [$bugNumber](https://bugzilla.redhat.com/show_bug.cgi?id=$bugNumber) - $bugSummary"
    }
}
