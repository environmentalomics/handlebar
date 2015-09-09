#!/usr/bin/perl
#define_experiment.pm - created Wed Jul 18 18:09:46 BST 2012

#FIXME - this should not be in the released code!
use lib '/home/tbooth/sandbox/genquery/new';

package Handlebar::Plugin::define_experiment;
use strict;
use warnings;

use GenQuery::EmbedQuery;

our $QUERY_ID_IN_GQ = 110;

# This is "require"d from the request_barcodes.cgi

sub get_tag
{
    "Experiments";
}

sub get_label
{
    "Define nanoparticle exposure experiments.";
}
    
sub show_summary
{
    my (undef, $q) = @_;

    my $output = "";

    #Print a blurb
    $output .=
    $q->p('This database logs nanoparticle exposure experiments.  To create a new experiment, use the helper
	   plugin.  To amend or update any information after the experiment has already been created,
	   retrieve the data to edit it in a spreadsheet <a href="#retrieve" style="font-style:italic">(see below)</a>.
	  ');

    #Show the button to jump to the form
    $output .=
    $q->p( { style=>"text-align:center"}, $q->submit( -name=>"gotoplugin", -value=>"Use plugin", -style=>"width:300px") );

    #Gather config data for GQ (see report_barcodes)
    # see make_config()

    #Use a mini in-line template to activate GenQuery and print a table of results
    
    my $template = '
    <em>Experiments currently logged: <TMPL_VAR NAME="ROWS_RETURNED"></em>

    <TMPL_IF NAME="ROWS_RETURNED">
      <table class="neat1">
	<tr align="left" valign="top"><TMPL_VAR NAME="RESULTS_TABLE_HEADER"></tr>

	<TMPL_LOOP name="RESULTS_TABLE_ROW">
            <tr align="left" valign="top"><TMPL_VAR NAME="ROW_DATA"></tr>
        </TMPL_LOOP>
      </table>
    </TMPL_IF>
    ';

    my $gq = new GenQuery::EmbedQuery( config_data => make_config(), link_base => 'report_barcodes.cgi' );

    $gq->set_query( id => $QUERY_ID_IN_GQ );
    $gq->set_template( $template );

    $output . $gq->run_and_print( );
}

#Sorry, this is copy-pasted from report_barcodes.cgi.  Should be shunted into the util library.
sub make_config
{
    #This bit is naughty, but I don't want to import all the config routines.
    my $barcodes_conf = $barcodeUtil::conf;

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

   $conf{template_dir} = undef;

   $conf{template_vars} = {};

   \%conf;
}

bless \"LOL ZOMG $!";
