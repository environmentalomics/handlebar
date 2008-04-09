#!/usr/bin/perl
#query_barcodes.perl - created Fri Apr  1 11:25:43 2005
use strict; use warnings;

# CVS $Revision: 1.9 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#Can't connect just yet, as we play silly beggars 
#for the master-query case.
use barcodeUtil;
#use Data::Dumper;

our $q = bcgetqueryobj();
our $bc = $q->param('bc');

our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};
our $MASTER_SEARCH = $CONFIG{MASTER_SEARCH};

our $ENABLE_REPORTS = $barcodeUtil::ENABLE_REPORTS;

our $highestbc;
our $lowestbc;
our $database_label;

#Remove any hyphens etc from the thing.
our $querycode = bcdequote($bc);

my $main = sub
{
    print bcheader();

#     $q->delete('bc');
    print bcstarthtml("$PAGE_TITLE - Quick Query"),
	  bcnavbanner(),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Query the barcode database"),
	  $q->h2("Enter a barcode to see details"),
	  $q->start_form(-name=>"queryform", -method=>"GET"),
	  $q->hidden(-name=>"username"), #See note below
	  $q->table( {-class=>"formtable"},
	    $q->Tr($q->td(
		[$q->textfield("bc"), $q->submit( -value=>"Query" )]
	    ))
	  ),	
	  $q->end_form();

    #Note - the user name field is just here so that if the user does some admin, then some queries, then
    #goes back to the admin tab, the username field has been preserved.  It has no relevance to the query.

    #Now the input field should be focussed ready for the user to scan a code
    print "<script type='text/javascript'>
	   var bcbox = document.queryform.bc;
	   bcbox.focus();
	   bcbox.select();
	   </script>";

    if(defined $bc)
    {
	print $q->hr(),
	      $q->h4($q->escapeHTML("Results of your search on $bc :"));

	if(! $querycode)
	{
	    print $q->p("You need to enter a valid numeric barcode to search on.");
	} 
	elsif($MASTER_SEARCH)
	{
	    runquery_master($bc);
	}
	else
	{
	    #Connect with DB params found in config
	    barcodeUtil::connectnow();

	    #Find out highest and lowest barcodes.
	    $highestbc = bcgethighestbc();
	    $lowestbc = bcdequote($CONFIG{MIN_BAR_CODE}) || 1;
	    
	    runquery($bc);

	    bcdisconnect();
	}

	print $q->end_div(), bcfooter();
    }
    else
    {
	if($ENABLE_REPORTS)
	{
	    print $q->p('This is the quick query page.  Use the <a href="report_barcodes.cgi">report maker</a> 
			to see the full selection of available reports.');
	}
    
	print $q->end_html();
    }
};

sub codetolink
{
    my $code = bcquote(shift());
    $q->a({-href=>$q->url(-relative=>1)."?bc=$code"}, $code);
}

sub usertolink
{
    return @_ if !$ENABLE_REPORTS;
    my $user = shift;

    #If the reportmaker is enabled, link to the 'Show Users' query
    my $link = 'report_barcodes.cgi?queryname=Show+Users;qp_USERNAME='
             . CGI::escape($user)
	     . ';rm=results#results';

    $q->a({-href => $link}, $user);
}

sub typetolink
{
    my $type = shift;

    #Use the type summariser, as linked in the Show Item Types report
    my $link = 'request_barcodes.cgi?typespopup=1#'
               . CGI::escape($type);

    $q->a({-href => $link}, bczapunderscores($type));
}

sub blocktolink
{
    my ($fromcode, $tocode) = @_;
    my $label = bcquote($fromcode) ." to  ". bcquote($tocode);

    if(!$ENABLE_REPORTS)
    {
	return $label;
    }

    my $link = "report_barcodes.cgi?queryname=Data+Summary;qp_FROMCODE="
	     . "$fromcode;qp_TOCODE=$tocode;rm=results#results";
    
    $q->a({-href => $link}, $label);
}

sub runquery
{
    eval{
	bcgetinfofornumber($querycode);
    };
    if( $@ )
    {
	#Not found - print an error and maybe say what the highest barcode is.
	print $q->p("This barcode has not been allocated."); 
	if( $querycode > $highestbc )
	{
	    print $q->p("The highest allocated barcode in the database is " .
			($highestbc ? bcquote($highestbc) : "[nothing allocated]") . "." );
	}
	elsif( $querycode < $lowestbc )
	{
	    print $q->p("The lowest possible barcode in this database is " .
			 bcquote($lowestbc) );
	}
    }
    else
    {
	reportoncode($querycode);
    }
}

sub runquery_master
{
    #Hmm, complexities.
    #Run through all databases each time so we can carp about a bad config.
    #But the target db will be the first one to potentially contain the
    #code.  Overlaps in the ranges will not be spotted here.
    my $nn;
    my $targetdb;
    my %configclone = %CONFIG;

    for($nn = 1; $nn <= $MASTER_SEARCH; $nn++)
    {
	my $lowcode = bcdequote($CONFIG{"LOW_CODE_$nn"});
	my $highcode = bcdequote($CONFIG{"HIGH_CODE_$nn"});

	defined($lowcode) && defined($highcode) && $highcode > $lowcode or
	    die "Error in the config file for database $nn in the master search.";
	
	if($querycode >= $lowcode && $querycode <= $highcode)
	{
	    $targetdb ||= $nn;
	}
    }

    if(!$targetdb)
    {
	print $q->p("This barcode is out of range.  There are $MASTER_SEARCH databases registered
	             in the configuration file but none should contain this code.");
    }
    else
    {
	#Fix up the connection params
	for(qw{DATABASE_HOST DATABASE_USER DATABASE_NAME DATABASE_PASS DATA_SCHEMA PREFIX_LENGTH
	       POSTFIX_LENGTH SPACER_CHAR})
	{
	    my $override = $CONFIG{"${_}_$targetdb"};
	    if($override)
	    {
		$configclone{$_} = $override;
	    }
	}
	barcodeUtil::connectnow(\%configclone);
	
	$database_label = $CONFIG{"LABEL_$targetdb"};
	$highestbc = bcgethighestbc();
	$lowestbc = bcdequote($CONFIG{"LOW_CODE_$targetdb"}) || 1;

	runquery();

	bcdisconnect();
    }
}

sub reportoncode
{
    my $bc = shift();
    my( $username, $typename, $datestamp, $comments, $fromcode, $tocode)
		= bcgetinfofornumber($bc);

    #When this is called we know we have a valid allocated bc, but it may or may not have
    #info associated with it.
    
    my $table = bctypetotable($typename);
    my $sth = bcprepare("
		SELECT * FROM $table WHERE
		barcode = ?
		");
    $sth->execute($bc);
    my $bcinfo = $sth->fetchrow_hashref();
    my $bcfields = $sth->{NAME_lc};

    #Find anything in the links table
    $sth = bcprepare("
		SELECT childtype, childcode from barcode_link_index WHERE
		parentcode = ?
		ORDER BY childtype, childcode
		");
    $sth->execute($bc);
    my @childcodes = @{$sth->fetchall_arrayref()};

    #See if this code was disposed, and if so print a warning.
    my ($dispdate, $dispcomments) = bcdisposedateandcomments($bc);
    if($dispdate)
    {
	print $q->p({-class=>'alertbox'},
		"This barcode has been marked <b>disposed</b> as of $dispdate" .
		($dispcomments ? " with the comments:\n<br />$dispcomments<br />" : ". ") .
		"The item no longer exists.");
    }

    print $q->start_table({-class=>"neat1"}),
	  $q->Tr( $q->td( [ '<b>Barcode</b>' => codetolink($bc) ]) ),
	  $database_label ? $q->Tr( $q->td( [ '<b>In database</b>' => $database_label ]) ) : "",
	  $q->Tr( $q->td( [ '<b>Owned by</b>' => usertolink($username) ]) ),
	  $q->Tr( $q->td( [ '<b>Type</b>' => typetolink($typename) ]) ),
	  $q->Tr( $q->td( [ '<b>Part of block</b>' => blocktolink($fromcode, $tocode) ]) ),
	  $q->Tr( $q->td( [ '<b>Allocated on</b>' => $datestamp ]) );
    print $q->Tr( $q->td( [ '<b>Range comment</b>' => $comments ]) ) if $comments;

    if( !$bcinfo )
    {
	print $q->Tr( $q->td({ -colspan=>2 }, 
	              $q->i("No data about this item has been submitted yet") ) );
    }
    else
    {
	my $printrow = sub {
	    my $name = shift();
	    my $flags = shift();

	    my $val;
	    if(!defined($bcinfo->{$name}))
	    {
		$val = $q->i('null');
	    }
	    elsif($flags->{bc})
	    {
		#Try to discover what type of thing the code links to
		my ( undef, $linked_code_type ) = eval{ bcgetinfofornumber($bcinfo->{$name}) };
		$val = codetolink($bcinfo->{$name});
	        $val .= ' (' . bczapunderscores($linked_code_type) . ')' if $linked_code_type;
	    }
	    else
	    {
		$val = $q->escapeHTML($bcinfo->{$name});
	    }
	    print $q->Tr( $q->td( [ bczapunderscores($name) => $val] ) ); 
	};
    
	my @demoted;
	for(@$bcfields)
	{
	    next if $_ eq 'barcode';

	    #Now deal with barcode links.  I was going to have some cunning way to guess when
	    #a number was a code, but instead just use the descriptions table to make it explicit
	    my $flags = bcgetflagsforfield($typename, $_);
	    
	    if($flags->{demote})
	    {
		unshift @demoted, [$_, $flags];
	    }
	    else
	    {
		&$printrow($_, $flags);
	    }
	}

	&$printrow(@$_) for @demoted;
    }

    #Finally list any links to child codes
    if(@childcodes)
    {
	print $q->Tr( $q->td( [ "<b>Derived items</b>" => 
		join( $q->br, map { codetolink($_->[1]) . ' (' .
				    bczapunderscores($_->[0]) . ')'
				  } @childcodes )
			      ] ) ); 
    }

    print $q->end_table();
}

&$main();
