#!/usr/bin/perl
use strict; use warnings;

# CVS $Revision: 1.17 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#Testing - capture all warnings.
# (or maybe use diagnostics)
# use Carp;
# $SIG{__WARN__} = sub { confess(@_) };

# This is the 6th and maybe final installment of the Handlebar interface.
# It manages collections of codes, or playlists as somebody else termed such things.
# A collection has an owner, id and associated dates.  It may also have a comment and a nickname.
# A collection is a poset - it is ordered but may not contain dupes.
# A barcode can be in any number of collections, and the user need not match
# Currently the barcode must be an existing code in the database, but it would be possible in principle
# to allow collections to span databases.
use barcodeUtil('-connect');
#use Encode;

# No need to load CGI::Carp - barcodeUtil does this for you!
#  use CGI::Carp qw(fatalsToBrowser);

#First load in the config file

our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};
our $STRICT_USER_NAMES = $barcodeUtil::STRICT_USER_NAMES;

our $PAGE_MAINTAINER = $CONFIG{PAGE_MAINTAINER};

our $COLLECTION_PREFIX = $CONFIG{COLLECTION_PREFIX};
our $PREFIX_LENGTH = $CONFIG{PREFIX_LENGTH};
our $MIN_BAR_CODE = bcdequote($CONFIG{MIN_BAR_CODE});

#A CGI query object
my $q = bcgetqueryobj();

#Other modules
use Data::Dumper; #For teh debugging and some error reporting
use IO::String;
{ package IO::String; no warnings; sub str{${shift()->string_ref }} }

#Set auto-newline so the HTML source is legible
$\ = "\n";

#Check the username
our $userdata = bcchkuser($q->param('username'));

sub main
{
#Right, first decide if this is a downlaod action of some sort...
#None defined yet, so print the standard header.

print bcheader(),
      bcstarthtml("$PAGE_TITLE - Manage Collections"),
      bcnavbanner(),
      bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Manage collections of barcodes");

#Things we may need to do:
#
#1) Show a welcome interface with a search box for collections
#1a) Show the list in full or filtered in various ways (eg by user) (could these two be done by GQ??)
#2) Prompt to create a new collection from a block or from a list of codes.
#3) Actually create the collection, then show the editor
#4) Just show the editor, given a collection to edit
#5) Save edits (and show the editor)
#6) Delete collection

#The event dispatcher.  CGI::Application-esque but open coded.
for my $rm ($q->param('rm'))
{
	$rm eq 'create' && do #3
	{
		my ($collectionid, $result) = eval{ create_collection() };
		if($collectionid)
		{
			print $result,
				  show_editor_or_error($collectionid);

			#Showing the editor should always work as I have just made the collection
		}
		else
		{
			print gen_error($@),
				  prompt_for_create();
		}
	last}


	$rm eq 'prompt_for_create' && do #2
	{
		print prompt_for_create();
	last}

	$rm eq 'edit' && do #4
	{
		print show_editor_or_error($q->param('collectionid'));
		#This might fail if the collection is duff, so need better error trapping
	}

	$rm eq 'saveedits' && do #5 - come to this later
	{
		die "Erm...";
	last}

	$rm eq 'deletecollection' && do #6
	{
		my ($collectionid, $result) = eval{ delete_collection() };

		if($collectionid)
		{
			print $result,
				  prompt_for_query(); #Hmm - this should put the user back where they
									  #were before deleting...
		}
				  
	last}

	#else - 1
	print prompt_for_query();
}

#And always do this:
print bcfooter(), $q->end_html();

}

###########################################
# END OF DISPATCHER LOGIC - NOW THE ACTIONS
###########################################

#Query prompt shows a box to go directly to a collection summary and a link to GenQuery for
#searching (link should probably show all collections by default - the user will still see the
#filters)
sub prompt_for_query
{
	$gq_link = "report_barcodes.cgi?rm=query;queryname=lalala";

      $q->h2("Enter a collection ID or nickname to see details") .
	  $q->form({-name=>"showcollectionform", -method=>"get"}
		  $q->textfield("c"),
		  $q->submit(),
	  ) .
	  $q->h2($q->a({-href=>$gq_link}, "Search for collections in the report maker"));
}

#Shows the boxes for the user to create a new collection.  When clicking in from GenQuery or wherever
#these should be already filled in.
sub prompt_for_create
{
	$q->h2("Define a new collection of barcodes") .
	$q->form({-name=>"makecollectionform", -method=>"post"},
		"User name" . $q->textfield("username"),
		"Nickname for collection" . $q->textfield("nickname"),
		"Comments" . $q->textarea("comments"),
		"Codes to add" . $q->textarea("codes"),
		$q->submit(),
	) .
	"doop de do";
}

#This takes the params from CGI, validates and tries to make a collection
#If there is an error, dies
#On success, returns the ID of the new collection and a message for the user
sub create_collection
{
	$userdata or die bad_user_error();
	my $nickname = lc($q->param('nickname'));
	my $comments = $q->param('comments');
	my $codes_to_add = $q->param('codes');
	my $message = "Creating a new collection...\n";

	#Comments can be anything
	#Nickname can be up to 20 chars and must be only alphanum, underscore or space
	#Nickname must either be unique (will be caught by db constraint) or blank
	for($nickname)
	{
		/[^\w ]/ and die 
			"If you want to give a nickname to your collection, " . 
			"it must contain only letters, numbers, underscores and spaces.";
		#Also trim repeated, leading or trailing spaces with some line noise
		s/^ // ; s/ $// ; tr/ //s;
	}
	#The above checks let through ' ' and '';
	$nickname = undef if $nickname !~ /\w/;

	#Codes list will be expanded as per the disposals box
	my @codelist = codelist_normalise($codes_to_add);
	my @dupesfound = codelist_killdupes(\@codelist);
	#TODO - report to the user if dupes were removed.

	if(@dupesfound)
	{
		$message .= "WARNING: " . scalar(@dupesfound) . " duplicate codes were pruned from the list.\n";
	}

	#Decide what prefix I should be using for collections
	my $prefix = $COLLECTION_PREFIX ||
				 "coll." . substr(bcquote($MIN_BAR_CODE), $PREFIX_LENGTH);
	$prefix = "coll" if $prefix eq "coll.";

	my $new_collection_id = bccreatecollection($prefix, $userdata->{username}, $nickname,
											   $comments);

	#Super, now add all the codes into it.
	bcappendtocollection($new_collection_id, \@codelist);
	my $codecount = scalar(@codelist);

	$message .= "A new collection $new_collection_id has been created with $codecount items.\n";
	($new_collection_id, $message);
}

#Show the form to edit barcodes.  This includes the feature to move the codes up and down, so it is not simple.
sub show_editor
{
	my $collectionid = (@_);

	my $collection_info = bcgetcollectioninfo($collectionid) or die "No such collection $colelctionid\n";
	my @collection_items = bcgetcollectionitems($collectionid);

	#For the fist shot, just list the info.  TODO - add up/down/delete editing function.
	my $res = "Collection $collectionid:<br />\n";
	
	$res .= "<pre>" . Dumper($collection_info) . "</pre>";

	for my $acode (@collection_items)
	{
		my ($owner, $type, $date, $comments, $fromcode, $tocode) = bcgetinfofornumber($acode);

		$res .= "$acode ($type) from block ${fromcode}:${tocode} owner $owner comments : $comments<br />\n";

	$res;
}

#Wrap the editor to catch exceptions
sub show_editor_or_error
{
	my @result = eval{ show_editor(@_) };
	return (@result ? join('', @result) : gen_error($@) );
}

#Borrowed from admin_barcodes.  Makes an error message into an HTML error box.
sub gen_error
{
	"\n" .
    $q->div({-class=>"errorbox", -style=>"margin-top:1em"}, 
			"<p><b>Error:</b></p>" . join("<br />\n", @_));
}

sub bad_user_error
{
	$q->param('username')
	  ?	"The user name " . $q->param('username') . " is not a known user in the database.\n"
	  : "Please supply a valid user name.\n";
}

sub codelist_normalise
{
    #Take the box with the numbers in and return an array of codes
	#This is copy-and-pase from request_barcodes but a little different -
	#ranges given in reverse order will be preserved in that order.
	#Also, everything will be converted to an integer.
    my $list = shift;
    my @res;

    for($list) {
		#Knock out all the hyphens
		tr/-//d;

		#Then make sure that every character which is not a colon or a digit is converted to a space.
		#And remove duplicate whitespace.
		tr/:0-9/ /cs;
		
		#Now collapse any spaces which are not bounded by digits
		s/ :/:/g;s/: /:/g;
    }

    #Right-ho
    for(split / /, $list)
    {
		if(/^\d+$/) { push(@res, int($_)) }
		elsif(/^(\d+):(\d+)$/)
		{
			if(abs($2 - $1) > 10000) { die "Range $_ is larger than the maximum number of codes allowed " .
										   "for processing in one go.  Aborting.\n" };
			if($2 < $1) { push(@res, reverse($2..$1)) }
			else        { push(@res, $1..$2) }
		}
		else
		{
			#This catches something like 30:40:50
			die "Range $_ is not a valid range of codes.\n";
		}
    }

    return @res;
}

sub codelist_killdupes
{
	#Given a reference to an array of numbers, remove any duplicates found and report
	#how many things were removed (scalar) or all the removed values (list).  
	#The array is not assumed to be sorted, but it is
	#assumed that all elements will be integers (ie. no leading zero issue)
	my ($numbers) = @_;

	my %seen;
	$seen{$_}++ and	delete $_ for @$numbers;

	grep { $_ > 1 } values %seen;
}

### Now some barcodeUtil stuff which is only relevant to collections...
package barcodeUtil {
sub bccreatecollection
{
	my ($prefix, $username, $nickname, $comments) = @_;

	#Could get the database to assign the ID.  Usual problem that I then need to
	#do a read to get the ID back which is a pain.
	
	#First get a write lock as below
	$dbh->do("LOCK barcode_collection IN EXCLUSIVE MODE");

	my ($next_id) = $dbh->selectro_array("
		SELECT max(id) + 1 FROM barcode_collection
		");

    #Log the collection in the database
    $dbh->do("INSERT INTO barcode_collection
              (prefix, id, username, nickname, comments)
				values
			  (?,?,?,?,?)", undef,
			$prefix, $next_id, $username, $nickname, $comments);
    $dbh->commit();

    #Log it
    bclogevent( 'newcoll', $username, undef, undef,
		"User $username created a new collection $next_id with " . 
		defined($nickname) ? "nickname $nickname." : "no nickname."
	);
    
	$next_id;
}

sub bcappendtocollection
{
	my ($collid, $codes) = @_;
}

} #end package spazz
barcodeUtil->export_to_level(1, qw(bccreatecollection bcappentdtocollection bcdeletefromcollection
								   bcgetcollectioninfo bcgetcollectionitems));

main();

