#!/usr/bin/env perl 
#===============================================================================
#
#         FILE: zanata-common-perl.pl
#
#        USAGE: ./zanata-common-perl.pl  
#
#  DESCRIPTION:  Zanata Perl common definitions and subroutine
#
#      OPTIONS: ---
# REQUIREMENTS: ---
#         BUGS: ---
#        NOTES: ---
#       AUTHOR: Ding-Yi Chen
#      CREATED: 18/04/16 10:59:32
#     REVISION: ---
#===============================================================================
package ZanataScriptsCommon;
use strict;
use warnings;
use utf8;

use constant {
	EXIT_OK=>0,
	EXIT_FATAL_UNSPECIFIED=>1,
	EXIT_FATAL_INVALID_OPTIONS=>3,
	EXIT_FATAL_MISSING_DEPENDENCY=>4,
	EXIT_FATAL_UNKNOWN_MODULE=>5,
	EXIT_FATAL_FAIL=>6,

	EXIT_ERROR_FAIL=>20,
	EXIT_RETURN_FALSE=>40
};

use constant JIRA_SERVER_URL => 'https://zanata.atlassian.net';
use constant JIRA_PROJECT => 'ZNTA';

require Exporter;
our @ISA = 'Exporter';
our @EXPORT = qw(EXIT_OK EXIT_FATAL_UNSPECIFIED EXIT_FATAL_INVALID_OPTIONS
    EXIT_FATAL_MISSING_DEPENDENCY EXIT_FATAL_UNKNOWN_MODULE
    EXIT_FATAL_FAIL

    EXIT_ERROR_FAIL EXIT_RETURN_FALSE 
	JIRA_SERVER_URL JIRA_PROJECT
	);

1;
