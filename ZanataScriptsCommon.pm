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
use Data::Dumper qw(Dumper);

use constant {
    EXIT_OK                       => 0,
    EXIT_FATAL_UNSPECIFIED        => 1,
    EXIT_FATAL_INVALID_OPTIONS    => 3,
    EXIT_FATAL_MISSING_DEPENDENCY => 4,
    EXIT_FATAL_UNKNOWN_MODULE     => 5,
    EXIT_FATAL_FAIL               => 6,

    EXIT_ERROR_FAIL   => 20,
    EXIT_RETURN_FALSE => 40
};

use constant JIRA_SERVER_URL    => 'https://zanata.atlassian.net';
use constant JIRA_PROJECT       => 'ZNTA';
use constant GITHUB_REST_SERVER => 'api.github.com';

##== Subroutines Start ==
use HTTP::Tiny;
use HTTP::Request;
use HTTP::Response;
use LWP::Protocol::https;
use LWP::UserAgent;
$HTTP::Request::Common::DYNAMIC_FILE_UPLOAD = 1;

my $userAgent = LWP::UserAgent->new();

sub http_request_new {
    my ( $method, $url, $header, $content ) = @_;
    return HTTP::Request->new( $method, $url, $header, $content );
}

sub rest_response {
    my ( $method, $url, $header, $content, $contentCb, $readSizeHint ) = @_;
    my $request = http_request_new( $method, $url, $header, $content );
    return $userAgent->request( $request, $contentCb, $readSizeHint );
}

## Exit code
sub response_die_if_error {
    my ( $response, $prompt ) = @_;
    unless ( $response->is_success ) {
        my ( $package, $filename, $line ) = caller;
        die $prompt
          . " Code: "
          . $response->code
          . "  Message: "
          . $response->message . "\n"
          . "  at $package::$filename, line $line\n";
    }
}

my %zanataScriptsIniHash;
my $zanataScriptsIni = $ENV{'HOME'} . '/.config/zanata-scripts.ini';

sub zanata_scripts_ini_load {
    die "zanata-scripts.ini not found at $zanataScriptsIni" unless ( -r $zanataScriptsIni );
    open( my $fh, '<', $zanataScriptsIni )
      or die "Cannon read $zanataScriptsIni: $!";
    while ( my $line = <$fh> ) {
        chomp $line;
        if ( $line =~ /^[A-Za-z].*=.*$/ ) {
            my ( $key, $value ) = split( /=/, $line, 2 );
            $zanataScriptsIniHash{$key} = $value;
        }
    }
}

sub zanata_scripts_ini_key_is_defined {
    my ($key) = @_;
    return defined $zanataScriptsIniHash{$key};
}

sub zanata_scripts_ini_key_get_value {
    my ($key) = @_;
    return undef unless zanata_scripts_ini_key_is_defined($key);
    return $zanataScriptsIniHash{$key};
}

BEGIN {
    my $ZnatNoEOL = 0;
    my $StageLast;

    sub print_status {
        if ( defined $ENV{'ZANATA_QUIET_MODE'}
            and $ENV{'ZANATA_QUIET_MODE'} == 1 )
        {
            return;
        }
        my ( $stage, $message, $optionStr ) = @_;
        $StageLast = $stage if $stage;
        my %optionHash;
        if ($optionStr) {
            foreach my $o ( split( '', $optionStr ) ) {
                return if ( $o eq 'q' );
                $optionHash{$o} = 1;
            }
        }

        my $outputStr;
        if ( $ZnatNoEOL == 0 ) {
            ## Previous line already ended
            $outputStr .= "### [$StageLast]";
        }

        if ( defined $optionHash{'s'} ) {
            $outputStr .= "==============================";
        }

        $outputStr .= "$message";
        print STDERR $outputStr;
        unless ( defined $optionHash{'n'} ) {
            print STDERR "\n";
        }
        $ZnatNoEOL = ( defined $optionHash{'n'} ) ? 1 : 0;
    }
}

##== Subroutines End  ==
##== Export ==
require Exporter;
our @ISA    = 'Exporter';
our @EXPORT = qw(EXIT_OK EXIT_FATAL_UNSPECIFIED EXIT_FATAL_INVALID_OPTIONS
  EXIT_FATAL_MISSING_DEPENDENCY EXIT_FATAL_UNKNOWN_MODULE
  EXIT_FATAL_FAIL

  EXIT_ERROR_FAIL EXIT_RETURN_FALSE
  JIRA_SERVER_URL JIRA_PROJECT

  GITHUB_REST_SERVER

  print_status
  github_credential_has_value
  github_logined_post_form
  github_logined_rest_response
  github_rest_response
  http_request_new
  progress_bar_set_total_size
  progress_bar_cb

  rest_response
  response_die_if_error

  zanata_scripts_ini_key_is_defined
  zanata_scripts_ini_key_get_value
  zanata_scripts_ini_load

);

1;
