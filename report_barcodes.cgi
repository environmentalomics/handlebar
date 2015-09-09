#!/usr/bin/perl 
use strict; use warnings;

#The report thing should look like part of the whole barcode system, but
#it uses GenQuery::WebQuery and the various templates.

#The stub CGI application.  Locations need to be set here explicitly to
#bootstrap finding the config file and modules.

#FIXME - this should not be in the released code!
use lib '/home/tbooth/sandbox/genquery/new';

use barcodeUtil;

my $params = {config_data => make_config(),
	     };

#This actually fires up GenQuery
use GenQuery::WebQuery;
my $cgiapp = GenQuery::WebQuery->new(PARAMS => $params);

#Strictly for debuggeration:
#$cgiapp->savetofile("/tmp/last_hb_report_run.out");

$cgiapp->run();

sub make_config
{
    #I seem to have made barcodes.conf and genquery.conf completely
    #incompatible.  Oops.  Plan is therefore to read the db connection
    #stuff etc. from barcodes.conf, hard-code some other stuff and feed
    #the whole lot as a data structure to GenQuery.

    my $barcodes_conf = bcgetconfig();

    my $dschema = $barcodes_conf->{DATA_SCHEMA} || 'data';
    $barcodes_conf->{SYSTEM_SCHEMA} and $dschema = "$barcodes_conf->{SYSTEM_SCHEMA}, $dschema";

    my %conf;

    $conf{db_connection} = { 0 => {
	    db_type => 'Pg',
	    db_host => $barcodes_conf->{DATABASE_HOST},
	    db_name => $barcodes_conf->{DATABASE_NAME},
	    db_user => $barcodes_conf->{DATABASE_USER},
	    db_pass => $barcodes_conf->{DATABASE_PASS},
	    db_port => $barcodes_conf->{DATABASE_PORT},
	    db_schema => "genquery, $dschema",

	    query_defs => 'query_def',
	    query_params => 'query_param' }
			   };

    $conf{bookmarks_on_links} = 'yes';
    $conf{cache_queries} = 'no';

    $conf{template_dir} = $barcodes_conf->{TEMPLATE_DIR};
    $barcodeUtil::divs_open = 1;
    $conf{template_vars} = {
	    STYLESHEET => $barcodes_conf->{STYLESHEET},
	    NAVBANNER => bcnavbanner(),
	    PAGE_DESC => $barcodes_conf->{PAGE_DESC},
	    PAGE_TITLE => $barcodes_conf->{PAGE_TITLE},
	    CUSTOM_FOOTER => bcfooter(),
    };

    \%conf;
}

