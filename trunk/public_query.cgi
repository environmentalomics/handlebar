#!/usr/bin/perl
#query_barcodes.perl - created Fri Apr  1 11:25:43 2005
use strict; use warnings;

# CVS $Revision: 1.9 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

# This is going to be similar to the query_barcodes.cgi but designed to display information to the
# public.  Therefore I want to show both individual codes and collections and display things
# a little differently to how query_barcodes does things.

#Can't connect or configure just yet, as we play silly beggars 
#for the master-query case.
use barcodeUtil '-noconf';
use Data::Dumper;

our $q = bcgetqueryobj();
our $bc = $q->param('bc') || '';
our($querycode, $querycoll, $coll_prefix) = (undef, undef, undef);

#OK, now I've allowed the SPACER_CHAR to be user configurable but the collections all get separated
#by a '.'.  See what I have.
if($bc =~ /\./)
{
    ($coll_prefix, $querycoll) = ($bc =~ /(?:(.*)\.|^)(\d+)/);
}
else
{   #Remove any hyphens etc from the thing.
    $querycode = bcdequote($bc);
}

our $highestbc;
our $lowestbc;
our $database_description;
our $lookup_error;
our $disable_publication_check;

#Sort out the configuration
sort_out_the_configuration();

our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE ||= $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $database_description || $CONFIG{PAGE_DESC};

$disable_publication_check = 1 if $CONFIG{DISABLE_PUBLICATION_CHECK};

my $main = sub
{
    #TODO - allow a different stylesheet for each database.

    print bcheader();

#     $q->delete('bc');
    print bcstarthtml("$PAGE_TITLE - Public Query"),
# 	  bcnavbanner(),
          $q->start_div({-id=>"topbanner", -dd=>$barcodeUtil::divs_open++}),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Public Query"),
	  $q->h2("Enter a barcode or collection ID to see details"),
	  $q->start_form(-name=>"queryform", -method=>"GET"),
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


    if($bc ne '')
    {
	print $q->hr(),
	      $q->h4($q->escapeHTML("Results of your search on $bc :"));

	if($lookup_error)
	{
	    #Bad configurations should trigger a CGI::Carp error message, but for the case where
	    #the barcode or collection looks valid but didn't match any databases I want to catch it here.
	    print $q->p($q->escapeHTML($lookup_error));
	}
	elsif(! ($querycode || $coll_prefix))
	{
	    print $q->p("You need to enter a valid barcode or collection ID to search on.");
	} 
	else
	{
	    #Connect with DB params found in the appropriate config file.
	    barcodeUtil::connectnow();
	    bcgetdbobj()->autocommit(1);
	    $lowestbc = bcdequote($CONFIG{MIN_BAR_CODE}) || 1;
	    $database_description ||= $CONFIG{PAGE_DESC};

	    if(bcgetdbobj())
	    {
		bcgetdbobj()->autocommit(1);

		#Find out highest barcode (I got the lowest from the config).
		$highestbc = bcgethighestbc();
		$coll_prefix ? runquery_coll() : runquery_code();

		bcdisconnect();
	    }
	}
    }

    print $q->end_div(), bcfooter();
};

sub sort_out_the_configuration
{
    #Here I want to see if these is a master.conf and if so to use it.
    #Otherwise just try to load barcodes.conf as normal.
    my $mc;
    if(-e 'master.conf')
    {
	$mc = {};
	#Maybe I should open-code Config::Simple to avoid the horror of it.
	Config::Simple->import_from('master.conf', $mc);

	$disable_publication_check = 1 if $mc->{DISABLE_PUBLICATION_CHECK};
    }
    else
    {
	barcodeUtil::_configure('barcodes.conf');
	return;
    }

    #If there is no barcode or collection prefix then I just need to get the
    #stylesheet out of the master.conf file and I'm done.
    unless($querycode || $coll_prefix)
    {
	barcodeUtil::_configure($mc);
	return;
    }

    #Now some variant on connect_master but bootstrapping the right config file.
    my $nn;
    my $targetdb;
    my $master_search = $mc->{MASTER_SEARCH};

    for($nn = 1; $nn <= $master_search; $nn++)
    {
	my $lowcode = bcdequote($mc->{"LOW_CODE_$nn"});
	my $highcode = bcdequote($mc->{"HIGH_CODE_$nn"});

	#Rather than scanning every config file to work out what codes are found where, make
	#master.conf list them explicitly.  Otherwise it gets silly.
	my $prefixes = $mc->{"COLLECTION_PREFIX_$nn"} || $mc->{"COLLECTION_PREFIXES_$nn"};
	my @prefixes = ref($prefixes) ? @$prefixes : $prefixes;
	map {s/\.$//} @prefixes;

	defined($lowcode) && defined($highcode) && $highcode > $lowcode or
	    die "Error in the config file for database $nn in the master search.";

	if($querycode)
	{
	    if($querycode >= $lowcode && $querycode <= $highcode)
	    {
		$targetdb ||= $nn;
	    }
	}
	else
	{
	    if(grep {$_ eq $coll_prefix} @prefixes)
	    {
		$targetdb ||= $nn;
	    }
	}
    }

    if(!$targetdb)
    {
	if($querycode)
	{
	    $lookup_error ="This barcode is out of range.  There are $master_search databases registered
			 in the configuration file but none should contain this code.";
	}
	else
	{
	    $lookup_error = "This collection cannot be found.  There are $master_search databases registered
			 in the configuration but none matches the prefix $coll_prefix.";
	}
	barcodeUtil::_configure($mc);
	return;
    }

    $PAGE_TITLE = $mc->{PAGE_TITLE};
    barcodeUtil::_configure($mc->{"CONFIG_FILE_$targetdb"});

    #Determine the database label/description
    $database_description = $mc->{"DESCRIPTION_$targetdb"};
}

sub codetolink
{
    my $code = bcquote(shift());
    $q->a({-href=>$q->url(-relative=>1)."?bc=$code"}, $code);
}

sub colltolink
{
    my $coll = shift;
    my $label = shift || $coll;
    $q->a({-href=>$q->url(-relative=>1)."?bc=".$q->escape($coll)}, $label);
}

sub runquery_code
{
    eval{
	bcgetinfofornumber($querycode);
    };
    if( $@ )
    {
	#Not found - print an error and maybe say what the highest barcode is.
	print $q->p("This barcode has not been allocated (in the $database_description database)."); 
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
	eval{ check_barcode_public($querycode) };
	if($@){	
	    print $q->p($@) 
	}
	else
	{
	    reportoncode($querycode);
	}
    }
}

sub runquery_coll
{
    my $info = bcgetcollectioninfo($querycoll);

    if(!$info)
    {
	print $q->p("No collection with the identifier $coll_prefix.$querycoll could be found.");
	return;
    }

    unless($info->{publish_codes} || $disable_publication_check)
    {
	print $q->p("This collection cannot be displayed as it has not been published.");
	return;
    }
    
    my @items = map {codetolink($_->[0])} @{bcgetcollectionitems($querycoll)};
    my $codecount = (scalar(@items) == 1) ? "1 item" : scalar(@items) . ' items';
    @items = "<i>empty collection</i>" unless @items;
    
    #Get user info
    my $userdata = bcgetalluserdata()->{$info->{username}};

    #Generate a publication string
    # my $pub_status
    # TODO - not sure I really need this

    #print $q->pre(Dumper($info));
    print $q->start_table({-class=>"neat1"}),
	  $q->Tr( $q->td( [ '<b>Collection</b>' => $info->{print_name} . " ($codecount)" ]) ),
	  $q->Tr( $q->td( [ '<b>Identifier</b>' => colltolink("$info->{prefix}.$info->{id}") ]) ),
	  $database_description ? $q->Tr( $q->td( [ '<b>In database</b>' => $database_description ]) ) : "",
	  $q->Tr( $q->td( [ '<b>Owned by</b>' => "$userdata->{realname}, $userdata->{institute}" ]) ),
	  $q->Tr( $q->td( [ '<b>Comments</b>' => $q->escapeHTML($info->{comments}) ]) ),
	  $q->Tr( $q->td( [ '<b>Created on</b>' => $info->{creation} ]) ),
	  $q->Tr( $q->td( [ '<b>Last modified</b>' => $info->{modification} ]) ),
# 	  $q->Tr( $q->td( [ '<b>Publication status</b>' => $pub_status ]) );
	  $q->Tr( $q->td( [ '<b>Codes</b>' => join('<br />', @items) ]) );

    #TODO - check robust quoting of the above.
    print $q->end_table();
}

sub check_barcode_public
{
    my $bc = shift;

    #Check if the code can be seen by the public, or die with a reason why.
    #The collection manager is designed never to set a collection so that the derived
    #or ancestor codes are public while the collection is not, but here I'll just follow
    #the strict settings of the flags.
    
    #See if checking has been bypassed
    return 1 if $disable_publication_check;

    my $no_index_message = "Unable to read from the <i>barcode_link_index</i> table.  This feature is required for the public
	query to run.  To enable indexing, please see the deployers manual.\n";

    #First see if the code is in a public collection
    my $sth = bcprepare("
        SELECT collection_id FROM barcode_collection c 
	    INNER JOIN barcode_collection_item i ON c.id = i.collection_id
	WHERE i.barcode = ? AND c.publish_codes LIMIT 1");
    $sth->execute($bc);

    if($sth->fetchrow_arrayref())
    {
	$sth->finish();
	#I'd like to always fail if the barcode index table is missing, rather than half working.
	#Therefore, a completely unnecessary SELECT on that table
	eval{
	    $sth = bcprepare("SELECT * FROM barcode_link_index WHERE false");
	    $sth->execute();
	};
	if($@){ die $no_index_message };

	return 'publish_codes';
    }

    #No dice on direct publication
    #Now find all the ancestor codes and see if any of these is in a collection with publish_descendants set

    #If fails, do exactly the same thing for descendants.  Same algorithm but there are potentially loads more 
    #to check.
    #Sorry for the confusing loop.  It was either that or cut-and-paste
    for my $foo ( ['publish_descendants', 'SELECT parentcode FROM barcode_link_index WHERE childcode = ?'],
		  ['publish_ancestors', 'SELECT childcode FROM barcode_link_index WHERE parentcode = ?'] )
    {
	my %seen = (); #Loop detection
	my @codestocheck;

	my $sth_pub = bcprepare("
	    SELECT collection_id FROM barcode_collection c 
		INNER JOIN barcode_collection_item i ON c.id = i.collection_id
	    WHERE i.barcode = ? AND c.$foo->[0] LIMIT 1");

	my $sth_parents;
	eval{
	    $sth_parents = bcprepare("$foo->[1] AND external_id IS NULL");
	    $sth_parents->execute($bc);
	    @codestocheck = map {$seen{$_->[0]}++ ? () : $_->[0]} @{$sth_parents->fetchall_arrayref()};
	};
	if($@){ die $no_index_message };

	while(@codestocheck)
	{
	    my $acode = shift(@codestocheck);
	    $sth_pub->execute($acode);
	    return $foo->[0] if ($sth_pub->fetchrow_arrayref());
	    $sth_parents->execute($acode);
	    push @codestocheck, map {$seen{$_->[0]}++ ? () : $_->[0]} @{$sth_parents->fetchall_arrayref()};
	}
    }
    
    #No dice
    die "Cannot show you the data for ", bcquote($bc), " as it has not been included in any published collections.  Sorry.\n";
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
    my @childcodes;
    eval{
	$sth = bcprepare("
		    SELECT childtype, childcode from barcode_link_index WHERE
		    parentcode = ?
		    ORDER BY childtype, childcode
		    ");
	$sth->execute($bc);
	@childcodes = @{$sth->fetchall_arrayref()};
    };

    #Get user info
    my $userdata = bcgetalluserdata()->{$username};

    #See if this code was disposed, and if so print a warning.
    my ($dispdate, $dispcomments) = bcdisposedateandcomments($bc);
    if($dispdate)
    {
	print $q->p({-class=>'alertbox'},
		"This barcode has been marked <b>disposed</b> as of $dispdate" .
		($dispcomments ? " with the comments:\n<br />$dispcomments<br />" : ". ") .
		"The item no longer exists.");
    }

    #See if this code is found in any collections
    my @collections;
#      eval{
	$sth = bcprepare("
		    SELECT prefix, id, nickname, publish_codes FROM barcode_collection c
		    INNER JOIN barcode_collection_item i ON c.id = i.collection_id
		    WHERE i.barcode = ? ORDER BY prefix, id");
	$sth->execute($bc);
	@collections = @{$sth->fetchall_arrayref()};
#      };

    print $q->start_table({-class=>"neat1"}),
	  $q->Tr( $q->td( [ '<b>Barcode</b>' => codetolink($bc) ]) ),
	  $database_description ? $q->Tr( $q->td( [ '<b>In database</b>' => $database_description ]) ) : "",
	  $q->Tr( $q->td( [ '<b>Owned by</b>' => "$userdata->{realname}, $userdata->{institute}" ]) ),
	  $q->Tr( $q->td( [ '<b>Type</b>' => bczapunderscores($typename) ]) ),
	  $q->Tr( $q->td( [ '<b>Part of block</b>' => bcquote($fromcode) . ' to ' . bcquote($tocode) ]) ),
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

    #List any links to child codes
    if(@childcodes)
    {
	print $q->Tr( $q->td( [ "<b>Derived items</b>" => 
		join( $q->br, map { codetolink($_->[1]) . ' (' .
				    bczapunderscores($_->[0]) . ')'
				  } @childcodes )
			      ] ) ); 
    }

    print  $q->Tr( $q->td( [ "<b>In collections</b>" =>
		@collections ? join('<br />', map { colltolink("$_->[0].$_->[1]") . ($_->[2] && $_->[3] ? " ($_->[2])" : "") } @collections)
			     : "<i>not in any collections</i>" ] ) );

    #TODO - say what (public) collections this code is a member of.

    print $q->end_table();
}

&$main();
