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
use barcodeUtil;
barcodeUtil::connectnow();
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
our $PUBLIC_QUERY_URL = $CONFIG{PUBLIC_QUERY_URL};

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
#2a) Prompt linked from report maker
#3) Actually create the collection, then show the editor
#4) Just show the editor, given a collection to edit
#5) Save edits (and show the editor)
#6) Delete collection

#The event dispatcher.  CGI::Application-esque but open coded.
my $rm = $q->param('rm') || $q->url_param('rm') || 'none';
$q->delete('rm');

#Special case for deletion
if($q->param('deletebtn')){ $rm = 'deletecollection' }

for(1)
{
    $rm eq 'create' && do #3
    {
	my ($collectionid, $result) = eval{ create_collection() };
	if($collectionid)
	{
	    bccommit();
	    print prompt_small(), $result, show_editor_or_error($collectionid);

	    #Showing the editor should always work as I have just made the collection
	}
	else
	{
	    bcrollback();
	    print prompt_small(), gen_create_error($@), prompt_for_create();
	}
    last};


    $rm eq 'prompt_for_create' && do #2
    {
	print prompt_for_create();
    last};

    $rm eq 'pfc' && do #2a
    {
	$q->param(codes => join("\n", $q->param('bc')));

	print prompt_for_create();
    last};

    $rm eq 'edit' && do #4
    {
	my @res = (show_editor_or_error($q->param('c')));
	print prompt_small(), @res;
	#This might fail if the collection is duff, so need better error trapping
    last};

    $rm eq 'saveedits' && do #5
    {
	#Similar to creation
	my @res;
	my ($collectionid, $result) = eval { edit_collection() };
	if($collectionid)
	{
	    bccommit();
	    @res = ($result, show_editor_or_error($collectionid));
	}
	else
	{
	    bcrollback();
	    @res = (gen_error($@), show_editor_or_error($q->param('id')));
	}
	print prompt_small(), @res;
    last};

    $rm eq 'deletecollection' && do #6
    {
	my ($collectionid, $result) = eval{ delete_collection() };

	if($collectionid)
	{
	    bccommit();
	    print $result,
		  prompt_for_query(); #Hmm - this should put the user back where they
				      #were before deleting...
	}
	else
	{
	    bcrollback();
	    print gen_error($@), show_editor_or_error($q->param('id'));
	}
			      
    last};

    #else - 1
    print prompt_for_query(), link_to_create();
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
sub gq_link
{
    my $gq_link = "report_barcodes.cgi?rm=results;queryname=Show+Collections";
    if($_[0])
    {
	$gq_link .= ";qp_USER=$_[0]";
    }
    "$gq_link#results";
}

sub prompt_for_query
{
    my $username = $q->param('username');
    my $usertext = ($username ? " for $username" : '');

    $q->h2("Enter a collection ID or nickname to see details") .
    $q->startform({-action=>'', -name=>"showcollectionform", -method=>"GET", -enctype=>CGI::URL_ENCODED()}) .
    $q->table( {-class=>"formtable"}, $q->Tr($q->td([
	    "<input type='hidden' name='rm' value='edit' />" ,
	    $q->hidden('username'),
	    $q->textfield("c"),
	    $q->submit("Show collection"),
    ]))) .
    $q->end_form() .
    $q->p("or... " . $q->a({-href=>gq_link($username)}, "<b>List collections$usertext in the report maker</b>"));
}

sub prompt_small
{
    my $username = $q->param('username');
    my $usertext = ($username ? " for $username" : '');

    $q->div( {-name=>'quick_coll_search'},
	$q->startform({-action=>'', -name=>"showcollectionform", -method=>"GET", -enctype=>CGI::URL_ENCODED()}) ,
	'Search : ', 
	"<input type='hidden' name='rm' value='edit' />" ,
	$q->hidden('username') ,
	$q->textfield("c") ,
	$q->submit("Show collection") ,
	' / ' ,
	$q->a({-href=>gq_link($username)}, "List collections$usertext") ,
	$q->end_form()
    );
}

sub link_to_create
{
    my $create_link = '?rm=create';
    $q->param(rm => 'prompt_for_create');

    $q->h2("Create a collection") ,
    $q->p("You can create a collection directly from a report, or you can make one manually by pasting in
	   a list of codes.") ,
    $q->p($q->a({-href=>"?rm=prompt_for_create"}, "<b>Create a new collection</b>")) ,
#     $q->startform({-name=>"create", -method=>"GET"}) .
#     $q->table( {-class=>"formtable"}, $q->Tr($q->td([
# 	    $q->hidden({-name=>'rm'}),
# 	    $q->submit("Create a new collection"),
#     ]))) ,
#     $q->end_form()
      ;

}


#Shows the boxes for the user to create a new collection.  When clicking in from GenQuery or wherever
#these should be already filled in.
sub prompt_for_create
{
    $q->param(rm => 'create');

    my @publication = ();
    if($PUBLIC_QUERY_URL)
    {	
	@publication = (
	  $q->td([
	    "Publish", $q->checkbox({ -name => "publish_codes", 
				      -value => '1',
				      -id => 'pc', 
				      -onClick => 'pc_clicked()', 
				      -label => "This collection" }) . " &nbsp;<i>and</i> " .
		       $q->checkbox({ -name => "publish_ancestors", 
				      -value => '1',
				      -id =>'pa', 
				      -onClick => 'pa_clicked()', 
				      -label => "All ancestor samples" }) . " &nbsp; " .
		       $q->checkbox({ -name => "publish_descendants", 
				      -value => '1',
				      -id=>'pd', 
				      -onClick => 'pd_clicked()', 
				      -label=>"All derived samples"})
	  ]) );
    }

    $q->h2("Define a new collection of barcodes") .
    $q->start_form({-name=>"makecollectionform", -method=>"POST"}) .
    $q->hidden({-name=>'rm'}),
    $q->table( {-class=>"formtable"}, $q->Tr([
	$q->td([
	    "User name", $q->textfield("username") 
	]),$q->td([
	    "Nickname for collection", $q->textfield("nickname") 
	]),$q->td([
	    "Comments", $q->textarea(-name => "comments", -rows => 4, - columns => 40) 
	]),
	@publication,
	$q->td([
	    "Codes to add", $q->textarea(-name => "codes", -rows => 8, -columns => 40) 
	]),$q->td([
	    '', $q->submit("Create collection") 
    ]),])) .
    $q->end_form() ;
}

sub check_nickname
{
    return undef unless defined $_[0];
    my $nickname = lc($_[0]);

    #Nickname can be up to 20 chars and must be only alphanum, underscore or space
    #Nickname must either be unique (will be caught by db constraint) or blank
    for($nickname)
    {
	#Catch invalid guff
	/[^\w ]/ and die 
		"If you want to give a nickname to your collection, " . 
		"it must contain only letters, numbers, underscores and spaces.\n";
	#Also trim repeated, leading or trailing spaces with some line noise
	tr/ / /s ; s/^ // ; s/ $// ;
	#Return undef if that left us with a blank
	/./ or return undef;
	#Also must contain at least one non-number to differentiate from a collection ID
	/\D/ or die "The nickname may not consist entirely of digits.\n";
    }
    $nickname;
}

#This takes the params from CGI, validates and tries to make a collection
#If there is an error, dies
#On success, returns the ID of the new collection and a message for the user
sub create_collection
{
	$userdata or die bad_user_error();
	my $nickname = check_nickname($q->param('nickname'));
	my $comments = $q->param('comments');
	my $publish_codes = $q->param('publish_codes');
	my $publish_ancestors = $q->param('publish_ancestors');
	my $publish_descendants = $q->param('publish_descendants');
	my $codes_to_add = $q->param('codes');
	my $message = $q->h2("Creating a new collection...") . "\n";

	#Codes list will be expanded as per the disposals box
	my @codelist = codelist_normalise($codes_to_add);
# 	my @dupesfound = codelist_killdupes(\@codelist);
	#TODO - report to the user if dupes were removed.

	#Decide what prefix I should be using for collections
	my $prefix = $COLLECTION_PREFIX ||
		    "coll." . substr(bcquote($MIN_BAR_CODE), 0, $PREFIX_LENGTH);
	$prefix =~ s/\.$//;

	if(!$publish_codes) { $publish_ancestors = $publish_descendants = 0 };

	my $new_collection_id = bccreatecollection($prefix, $userdata->{username}, $nickname,
						   $comments, $publish_codes, $publish_ancestors, $publish_descendants);

	#Super, now add all the codes into it.
	my $codesadded = bcappendtocollection($new_collection_id, \@codelist);
	my $codecount = scalar(@codelist);

	if($codecount - $codesadded)
	{
	    $message .= "WARNING: " . ($codecount - $codesadded) . " duplicate codes were pruned from the list.\n";
	}

	$message .= $q->p("A new collection $prefix.$new_collection_id has been created with $codecount items.\n");
	
	$message .= $q->p( "The collection will be " . publish_message($publish_codes, $publish_ancestors, $publish_descendants) . ".\n" );

	($new_collection_id, $message);
}

sub publish_message
{
    my ($publish_codes, $publish_ancestors, $publish_descendants) = @_;

    $publish_codes ? (
	($publish_ancestors && $publish_descendants) ?
	    "publicly viewable, along with the sample information and the information
	     on <b>all</b> related samples, including anything linked directly or indirectly to these samples in the future"
	: $publish_ancestors ?
	    "publicly viewable, along with the sample information and information
	     on any linked samples going right back to the original source"
	: $publish_descendants ?
	    "publicly viewable, along with the sample information and information
	     on <b>all</b> samples which link back directly or indirectly to any item in this collection, 
	     including those added in the future"
	: #else
	    "publicly viewable, along with the sample information for the collected codes"
    ) :
	#Assume that the other boxes are unchecked - enforced above.
	"visible only to logged-in users of Handlebar";
};

# sub add_codes
# {
    #Some sort of wrapper around bcappendtocollection

#     "$added codes were appended to the collection.";
#     "$dupes duplicte codes were not added";
# }

#Show the form to edit barcodes.  This includes the feature to move the codes up and down, so it is not simple.
sub show_editor
{
    my ($collectionid) = @_;

    #Split into prefix and id number with regex most cunning
    my ($prefix, $id) = ($collectionid =~ /(?:(.*)\.|^)(\d+)/);

    #If the ID is undefined this must be a nickname - check it has no dots
    if(!defined($id) && $collectionid =~ /\./)
    {
	die "The term you searched for neither looks like a nickname nor an identifier\n";
    }

    my $collection_info = bcgetcollectioninfo($id || $collectionid) or die "No such collection <i>$collectionid</i>\n";

    #Check prefix
    if(defined($prefix) and $prefix ne $collection_info->{prefix})
    {
	die "No such collection <i>$collectionid</i>, thought there is a collection 
	     <i>$collection_info->{prefix}.$collection_info->{id}</i>\n";
    }

    my $collection_items = bcgetcollectionitems($collection_info->{id});
    my $codecount = (scalar(@$collection_items) == 1) ? "1 item" : scalar(@$collection_items) . ' items';

    #For the fist shot, just list the info.  TODO - add up/down/delete editing function.
    my $res = $q->h2("View and edit collection");
    $res .= $q->p("Collection <i>$collection_info->{print_name}</i> ($codecount)<br />\n");
    
    $q->param(rm => 'saveedits');
    for(qw(id username nickname comments publish_codes publish_ancestors publish_descendants))
    {
	$q->param($_ => $collection_info->{$_});
    }
    $q->delete('really');
    $q->delete('codes');

    my @publication = ();
    if($PUBLIC_QUERY_URL)
    {	
	@publication = (
	    $q->td([
		"Publish", $q->checkbox({ -name => "publish_codes", 
					  -value => '1',
					  -id => 'pc', 
					  -onClick => 'pc_clicked()', 
					  -label => "This collection" }) . " &nbsp;<i>and</i> " .
			   $q->checkbox({ -name => "publish_ancestors", 
					  -value => '1',
					  -id =>'pa', 
					  -onClick => 'pa_clicked()', 
					  -label => "All ancestor samples" }) . " &nbsp; " .
			   $q->checkbox({ -name => "publish_descendants", 
					  -value => '1',
					  -id=>'pd', 
					  -onClick => 'pd_clicked()', 
					  -label=>"All derived samples"}) .
			   $q->p( $q->i( "Collection " . 
			   publish_message(@$collection_info{qw(publish_codes publish_ancestors publish_descendants)})))
	    ]),
	    $q->td([ "Public query link", 
		     $collection_info->{publish_codes} ? 
			qq*<a href="$PUBLIC_QUERY_URL?bc=$collection_info->{prefix}.$collection_info->{id}">* . 
			qq*$PUBLIC_QUERY_URL?bc=$collection_info->{prefix}.$collection_info->{id}</a>* :
			qq*<i>$PUBLIC_QUERY_URL?bc=$collection_info->{prefix}.$collection_info->{id}</i>*])
	);
    }

    $res .= $q->start_form({-name=>"amendcollection", -id=>"amendcollection", -method=>"POST"}).
		$q->hidden({-name=>'rm'}) .
		$q->hidden({-name=>'id'}) .
		$q->start_table( {-class=>"neat1"} ) . $q->Tr([
		    $q->td([
			"Identifier", $q->b( colltolink("$collection_info->{prefix}.$collection_info->{id}") )
		    ]),$q->td([
			"Owner", $q->textfield("username") 
		    ]),$q->td([
			"Nickname", $q->textfield("nickname") 
		    ]),$q->td([
			"Comments", $q->textarea({-columns=>"40", -rows=>"4", -name=>"comments"}) 
		    ]),
		    @publication,	
		    $q->td([
			"Created", $q->b( $collection_info->{creation} )
		    ]),$q->td([
			"Last Updated", $q->b( $collection_info->{modification} )
		    ]),$q->td({-style=>'background:none'}, [
			'', $q->submit({-name=>'commit', -label=>"Commit changes", -onClick=>'submit_hook()'}) 
		    ]),$q->td({-style=>'background:none'}, [
			'', $q->checkbox({-name=>'really',-label=>'really',-onClick=>'really_clicked()'}) . 
			    "&nbsp; " . $q->submit(-name=>'deletebtn', -id=>'deletebtn', -label=>"Delete collection") 
		]),]);

    $res .= $q->start_Tr() . $q->td("Codes") . $q->start_td();

    if(@$collection_items)
    {
	$res .= emit_shuffle_code();

	my $allinfo = get_info_for_codes($collection_items);
	my $alllabels;

	$res .= $q->start_table({-class=>"neat1", -id=>"items"}) .
		$q->Tr( $q->th( ["", "Code", "Type", "Info"]) );
	for(@$collection_items)
	{
	    my ($acode, $rank) = @$_;
	    my $info = $allinfo->{$acode};
	    my $data = $info->{data};
	    my $rowclass = '';

	    #Do I need disposal info?  It does mean a lot of extra DB access.
# 	    my ($dispdate, $dispcomments) = bcdisposedateandcomments($bc);
# 	    if($dispdate)
# 	    {
# 		$rowclass = "disposed";
# 	    }

	    #Build a code description from the info we have
	    my $codedesc;
	    my @labels = @{ $alllabels->{$info->{type}} ||= [ get_printable_column($info->{type}) ] };
	    if($data)
	    {
		$codedesc = ( @labels ? (join(' / ', @$data{@labels}) . '.') : '');
		$codedesc .= " $data->{comments}.";
		#Or else
		$codedesc .= " $data->{created_by} on $data->{creation_date}.";
	    }
	    else
	    {
		$codedesc = "No data recorded.";
		$rowclass = "unused";
	    }
	    if($info->{comments})
	    {
		$codedesc .= " Block: $info->{comments}.";
	    }

	    $res .= "\n" . $q->Tr({-id=>"$rank", -class=>$rowclass, -code=>$acode}, $q->td([
		make_buttons($acode, $rank),
		codetolink($acode),
		bczapunderscores($info->{type}),
		$codedesc
	    ]));
	}

	$res .= $q->end_table() . emit_images();
    }
    else
    {
	$res .= "<span style='color:red; font-weight:bold'>No codes in collection</span>";
    }

    $res .= $q->end_td() . $q->end_Tr() .  
	    $q->Tr($q->td([
		"Codes to add", $q->textarea(-name => "codes", -rows => 8, -columns => 40) 
	    ])) .
	    $q->end_table() .
	    $q->br .
	    $q->submit({-name=>'commit', -label=>"Commit changes", -onClick=>'submit_hook()'});

    #Now the JavaScript
    $res .= "
    <script type='text/javascript'>
	var delbtn = document.amendcollection.deletebtn;
	delbtn.setAttribute('disabled',true);

	var pc_check = document.amendcollection.pc;
	var pa_check = document.amendcollection.pa;
	var pd_check = document.amendcollection.pd;

	function really_clicked(){
	    if(document.amendcollection.really.checked)
		delbtn.removeAttribute('disabled');
	    else
		delbtn.setAttribute('disabled', true);
	}

	function pc_clicked(){
	  if(!pc_check.checked)
		pd_check.checked = pa_check.checked = false;
	}

	function pd_clicked(){
	  if(pd_check.checked || pa_check.checked)
	    pc_check.checked = true;
	}

	function pa_clicked(){
	    pd_clicked();
	}

    </script>
    ";

    $res;
}

sub get_info_for_codes
{
    my @codes = sort {$a <=> $b} map {$_->[0]} @{$_[0]};

    #Retrieve information about codes and return a hashref of code => {info}
    my %allinfo;

    #Cache range info for all codes so I don't have to alternate between calling
    #bcgetinfofornumber and fetching data
    for my $code (@codes)
    {
	my $info = $allinfo{$code} = {};

	@$info{qw(owner type date comments fromcode tocode)} = bcgetinfofornumber($code);
    }

    #Now try to get the info without too many queries.  Maybe a bit fiddly, but in most cases
    #will minimise database hits, which is good!
    my $lasttype = '';
    my $lastcode = 0; my $firstcode = 0;
    my $sth = undef; my $res;
    for my $code (@codes, -1)
    {
	my $info = $allinfo{$code};
	if($code == -1 || $info->{type} ne $lasttype || $code - $lastcode > 100)
	{
	    if($sth)
	    {
		$sth->execute($firstcode, $lastcode);
		$res = $sth->fetchall_arrayref({});

		for(@$res)
		{
		    if($allinfo{$_->{barcode}})
		    {
			$allinfo{$_->{barcode}}->{data} = $_;
		    }
		}
	    }

	    next if $code == -1;
	    $sth = bcprepare("
		     SELECT * FROM ". bctypetotable($info->{type}) . " WHERE
		     barcode >= ? and barcode <= ?");
	    $lasttype = $info->{type};
	    $lastcode = $firstcode = $code;
	}
	else
	{
	    $lastcode = $code;
	}
    }
    \%allinfo;
}

sub get_printable_column
{
    my ($itemtype) = @_;

    #Return the names of all printable columns in order.
    #Cut-and-paste from print_barcodes.cgi

    #Get all the column names - this is cut-and-paste from reqcsv in request_barcodes
    #but I should really have a utility function to get a list of col names.
    my $sth = bcprepare("
            SELECT * FROM " . bctypetotable($itemtype) . "
            LIMIT 1");
    $sth->execute();

    #We need to know about the headers, data or no data
    my @headings = @{$sth->{NAME}};
    $sth->finish();

    #Now find "print" flags while I apply demotions - messy
    my (@demoted, @undemoted);
    for(@headings)
    {
        my $flags = bcgetflagsforfield($itemtype, $_);
        if($flags->{print})
        {
            $flags->{demote} ? push(@demoted, $_) : push(@undemoted, $_);
        }
    }
    ( @undemoted, @demoted );
}


sub emit_shuffle_code
{
    #Give me some javascript that will allow the items to be moved up and down
    # TODO - have a non-JS version, maybe?
    q|<script type='text/javascript'>

	var items_table;
	var items_moved = false;

	function get_items(){
	    if(items_table == undefined)
	    {
		items_table = document.getElementById("items").getElementsByTagName("tbody")[0];
	    }
	    return items_table;
	}

	function move_row(i, j){
	    var fromtr = items_table.rows[i];
	    var totr = items_table.insertRow(j);
	    while(fromtr.hasChildNodes())
	    {
		totr.appendChild(fromtr.childNodes[0]);
	    }
	    /* Copying all attributes fails in IE so just copy id, code, style and class */

	    var atts = ['id', 'code', 'style', 'class'];
	    for(var nn = 0; nn < atts.length; nn++)
	    {
		try {
		    totr.setAttribute(atts[nn], fromtr.attributes[atts[nn]].value);
		} catch(e) {;}
	    }
	    
	    items_table.removeChild(fromtr);

	    items_moved = true;
	}

	function flash_row(i)
	{
	    var tr = items_table.rows[i];
	    xflash(tr.getAttribute('id'), 0, -2);
	}

	function xflash(i, col1, col2)
	{
	    var tr = items_table.rows.namedItem(i);
	    if(tr == undefined) return;
	    if(col1 < tr.cells.length)
	    /* This fails in IE		
		tr.cells[col1].setAttribute('style', 'background-color:lightblue'); */
	    tr.cells[col1].style.backgroundColor = 'lightblue';
	    if(col2 >= 0)
		tr.cells[col2].removeAttribute('style');
	    if(col2  + 1 < tr.cells.length)
		setTimeout('xflash(' + i + ',' + (col1 + 1) + ',' + (col2 + 1) + ')', 50);
	}

	function xdel(i, col1, col2)
	{
	    var tr = items_table.rows.namedItem(i);
	    if(tr == undefined) return;
	    if(col1 < tr.cells.length)
		tr.cells[col1].style.backgroundColor = 'red';
	    if(col2 >= 0)
		tr.cells[col2].removeAttribute('style');
	    if(col2  + 1 < tr.cells.length)
		setTimeout('xdel(' + i + ',' + (col1 + 1) + ',' + (col2 + 1) + ')', 50)
	    else
		items_table.deleteRow(tr.rowIndex);
	}
	    
	function move_up(i){
	    get_items();
	    var fromtr = items_table.rows.namedItem(i);
	    var fromidx = fromtr.rowIndex;

	    if(fromidx <= 1) return;
	    move_row(fromidx, fromidx - 1);
	    flash_row(fromidx - 1);
	}

	function move_down(i){
	    get_items();
	    var fromtr = items_table.rows.namedItem(i);
	    var fromidx = fromtr.rowIndex;

	    //Can I get away with not testing if this is the last row??
	    if(fromidx + 1 == items_table.rows.length) return;

	    move_row(fromidx, fromidx + 2);
	    flash_row(fromidx + 1);
	}

	function delete_the_bugger(i){ 
	    get_items();

	    xdel(i, 0, -2);

	    items_moved = true;
	}

	function submit_hook(){
	    /*If any shuffling was done, save the new list of codes into the codes1
	    hidden parameter*/
	    if (! items_moved) return;
	    var amendform = document.getElementById('amendcollection');
	    var codes_list = 'c';

	    for(var nn = 1; nn < items_table.rows.length; nn++)
	    {
		codes_list = codes_list + ' ' + items_table.rows[nn].getAttribute('code');
	    }

	    var codes1 = amendform.ownerDocument.createElement("input");
	    codes1.setAttribute("type", "hidden");
	    codes1.setAttribute("id", "codes1");
	    codes1.setAttribute("name", "codes1");
	    codes1.setAttribute("value", codes_list);
	    amendform.appendChild(codes1);
	}

    </script>|;
}

sub emit_images
{
    #Embed the icons in the HTML because I can.  This won't work on IE.  Tough luck.
    #IE users don't deserve pretty images.

    (my $upimg = 'data:image/png;base64,
	    iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAABGdBTUEAALGPC/xhBQAAAAZiS0dE
	    AAAAAAAA+UO7fwAAAAlwSFlzAAAASAAAAEgARslrPgAAAAl2cEFnAAAADAAAAAwAzqUyfgAAAF5J
	    REFUKM+tj8ENwDAIA5OuxE7sFGbCM7mPSlFKklao5cMD22dK+WO0ObU5V7cjGzYZnOzJospXQ4rg
	    JIG7IFImAgaHiH5/uo6PmmEpAuzaZrUTduJYLV/JST6lx2onqAcqzeWKWrgAAAAASUVORK5CYII=
	    ' ) =~ s/\n\s*//g;

    (my $downimg = 'data:image/png;base64,
	    iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAABGdBTUEAALGPC/xhBQAAAAZiS0dE
	    AAAAAAAA+UO7fwAAAAlwSFlzAAAASAAAAEgARslrPgAAAAl2cEFnAAAADAAAAAwAzqUyfgAAAGJJ
	    REFUKM+tkdERgDAIQ0lXYqcyk8wkM+FXW6w9Rc988QHJy4Hd3VWNMjJTKgKgVk4tkypKyjqoH9yl
	    mGmfEde2RZ+Gckl4jdTEPDIjyvJAAPBcJeD8gyTAcJzcPyXg+cdnHWPPH/CqJD7aAAAAAElFTkSu
	    QmCC' ) =~ s/\n\s*//g;

    (my $delimg = 'data:image/png;base64,
	    iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAABGdBTUEAALGPC/xhBQAAAAZiS0dE
	    AAAAAAAA+UO7fwAAAAlwSFlzAAAASAAAAEgARslrPgAAAAl2cEFnAAAADAAAAAwAzqUyfgAAASRJ
	    REFUKM+dkc9KAnEUhb+fiLiYGBBKJoJsI+aEbgwC160VfZKgFyh6hB7CVRD1DkoEmjMWiAudjZGJ
	    pKP5l9uiNK0W1VlcLpfvLs45yj065i/yzJdONi33zxX5CjSC/pW7Zw43z08x+j4aQb8sw27pBqPv
	    o5NNy+Jh5NSQ4YxALI5byFOdPcnj/p64hTxm5IBAPMbIqQGglj3UXWRbXkHgY2BXi6xFkoQ01IoH
	    gJCG6pYtpNtHugN6lg2D6QIG8H6LYTxBekMUIOMJjCY/p1R3kXLuWjTdoOk8YJWKaLrB7sYOd7mr
	    1ZRaZkJeLi4xw1Fs22KaPGTz7ATbtlAozHCUlpn4TMkb2Xrvou2gZ1KENNR65VbpmRS2bdFpOwtG
	    /bvp3+oNequBWMrcoDwAAAAASUVORK5CYII=' ) =~ s/\n\s*//g;

    qq|<script type='text/javascript'>
	var upimg = '$upimg';
	var downimg = '$downimg';
	var delimg = '$delimg';

	function apply_one_image(spanelem, name, img)
	{
	    spanelem.innerHTML = '';
	    var imgelem = spanelem.appendChild(document.createElement('img'));
	    imgelem.setAttribute('alt', name);
	    imgelem.setAttribute('border', '0');
	    imgelem.setAttribute('src', img);
	}

	function apply_images()
	{
	    get_items();
	    for(var nn = 1; nn < items_table.rows.length; nn++)
	    {
		var col =  items_table.rows[nn].cells[0].getElementsByTagName('span');
		apply_one_image(col.namedItem('up'), 'up', upimg);
		apply_one_image(col.namedItem('down'), 'down', downimg);
		apply_one_image(col.namedItem('del'), 'del', delimg);
	    }
	}

	if(navigator.userAgent.indexOf("MSIE") == -1) apply_images();

    </script>|;
}

#Make the buttons to do the move up/down
sub make_buttons
{
    my ($acode, $rank) = @_;

#     $q->i("up/down/delete");
#     $q->a({-onClick => "move_up($rank)", -href => 'javascript:;'}, "<img alt='up' id='up' src='' border='0'/>") . '/' .
#     $q->a({-onClick => "move_down($rank)", -href => 'javascript:;'}, "<img alt='down' id='down' src='' border='0'/>") . '/' .
#     $q->a({-onClick => "delete_the_bugger($rank)", -href => 'javascript:;'}, "<img alt='del' id='del' src='' border='0'/>") ;
    $q->a({-onClick => "move_up($rank)", -href => 'javascript:;'}, "<span id='up'>up</span>") . '/' .
    $q->a({-onClick => "move_down($rank)", -href => 'javascript:;'}, "<span id='down'>down</span>") . '/' .
    $q->a({-onClick => "delete_the_bugger($rank)", -href => 'javascript:;'}, "<span id='del'>del</span>") ;
}

sub edit_collection()
{
	$userdata or die bad_user_error();
	my $id = int_nowarn($q->param('id'));
	my $nickname = check_nickname($q->param('nickname'));
	my $comments = $q->param('comments');
	my $codes_to_shuffle = $q->param('codes1');
	my $codes_to_add = $q->param('codes');
	my @publish = map {$q->param($_) || '0'} qw(publish_codes publish_ancestors publish_descendants);
	my $message = $q->h2("Updating collection...") . "\n";

	if($codes_to_shuffle)
	{
	    #Remove existing
	    bcdeletefromcollection($id);
	    bcappendtocollection($id, [codelist_normalise($codes_to_shuffle)]);
	} 

	#Codes list will be expanded as per the disposals box
	my @codelist = codelist_normalise($codes_to_add);

	bcupdatecollection($id, undef, $userdata->{username}, $nickname, $comments, @publish);

	my $codesadded = bcappendtocollection($id, \@codelist);
	my $codecount = scalar(@codelist);

	if($codecount - $codesadded)
	{
	    $message .= "WARNING: " . ($codecount - $codesadded) . " duplicate codes were pruned from the list.\n";
	}

	$message .= $q->p("Collection has been updated" . ($codecount ? " and $codesadded codes were added" : '') . ".\n");
	($id, $message);
}

#Convert a code to a hyperlink
sub codetolink
{
    my $code = bcquote(shift());
    $q->a({-href=>"query_barcodes.cgi?bc=$code"}, $code);
}

#Convert a collection to a hyperlink
sub colltolink
{
    my ($code) = @_;
    $q->a({-href=>"collect_barcodes.cgi?c=$code;rm=edit"}, $code);
}

#Wrap the editor to catch exceptions
sub show_editor_or_error
{
	my @result = eval{ show_editor(@_) };
	return (@result ? join('', @result) : gen_error($@) );
}

sub delete_collection
{
    my $id = int_nowarn($q->param('id'));
    $q->param('really') or die "Deletion aborted as the 'Really' box was unchecked\n";

    bcdeletecollection($id);

    ($id, "Collection $id was successfully deleted.\n");
}


#Borrowed from admin_barcodes.  Makes an error message into an HTML error box.
sub gen_error
{
    "\n" . $q->div({-class=>"errorbox", -style=>"margin-top:1em"}, 
			"<p><b>Error:</b></p>" . join("<br />\n", @_));
}

sub gen_create_error
{
    #This version will detect the error when a duplicate nickname is used and say something more sensible
    if($_[0] =~ /duplicate key value violates unique constraint/)
    {
	return "\n" . $q->div({-class=>"errorbox", -style=>"margin-top:1em"}, 
			"<p><b>Sorry:</b></p>" .
		        "The nickname you chose is already in use.  
			Please try another or leave the nickname blank.");
    }
    gen_error(@_);
}

sub bad_user_error
{
	$q->param('username')
	  ?	"The user '" . $q->param('username') . "' is not known.\n"
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

		#Now trim
		s/^ //; s/ $//;
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
	my $orig_count = scalar(@$numbers);
	
	my %seen;
	$numbers = grep {!$seen{$_}++} @$numbers;

 	return wantarray ? (grep { $_ > 1 } values %seen) : ($orig_count - scalar(@$numbers));
}

### Now some barcodeUtil stuff which is only relevant to collections...
do{
package barcodeUtil;

our ($dbobj, $dbh);

sub bccreatecollection
{
    my ($prefix, $username, $nickname, $comments, @publish) = @_;

    #Could get the database to assign the ID internally.  Usual problem that I then need to
    #do a read to get the ID back which is a pain.
    
    #First get a write lock as below
    $dbh->do("LOCK barcode_collection IN EXCLUSIVE MODE");

    my ($next_id) = $dbh->selectrow_array("
	    SELECT max(id) + 1 FROM barcode_collection
	    ");
    #Case where the table is empty
    $next_id ||= 1;

    #And no undefs in the publish array
    $publish[$_] ||= 0 for (0..2);

    #Log the collection in the database
    $dbh->do("INSERT INTO barcode_collection
              (prefix, id, username, nickname, comments, publish_codes, publish_ancestors, publish_descendants)
				values
			  (?,?,?,?,?,?,?,?)", undef,
			$prefix, $next_id, $username, $nickname, $comments, @publish);

    #Log it
    bclogevent( 'newcoll', $username, undef, undef,
		"User $username created a new collection $next_id with " . 
		defined($nickname) ? "nickname $nickname." : "no nickname."
	);
    
    $next_id;
}

sub bcupdatecollection
{
    #my ($id, $prefix, $username, $nickname, $comments, @publish_*) = @_;
    my $id = shift;

    #Now need to pad args array to 7
    $_[6] = $_[6];

    my $rows = $dbh->do("UPDATE barcode_collection SET
		prefix = coalesce(?, prefix),
		username = coalesce(?, username),
		nickname = coalesce(?, nickname),
		comments = coalesce(?, comments),
		modification_timestamp = now(),
		publish_codes = coalesce(?, publish_codes),
		publish_ancestors = coalesce(?, publish_ancestors),
		publish_descendants = coalesce(?, publish_descendants)
	      WHERE id = $id", undef, @_);

    $rows or die "No collection with ID $id.";
    
    #Log it
    bclogevent( 'editcoll', $_[1], "coll$id", undef,
		"Collection with ID $id was updated:\n" . join("\n", @_));
}

sub bcappendtocollection
{
    my ($collid, $codes) = @_;

    #Adds codes and returns the number added.
    #Skips any dupes
    #Dies on a bad code
    #Need to check that the codes are not in there already and add them to the end.

    my $codescount = scalar(@$codes) or return 0;

    #First get a write lock to make this concurrency-safe
    $dbh->do("LOCK barcode_collection_item IN EXCLUSIVE MODE");

    #Fetch existing codes for collid
    my $existing = bcgetcollectionitems($collid);

    #Remove codes found in $existing or duplicate in list
    my %seen;
    map {$seen{$_->[0]}++} @$existing;
    my @remaining = grep {!$seen{$_}++} map {int($_)} @$codes;

    return 0 if !@remaining;

    #Check that all the remaining codes are allocated in the database
    for(@remaining)
    {
	bcrangemembertobase($_) or die "Code ". bcquote($_) . " is not allocated.\n";
    }
    my $rank = @$existing ? $existing->[-1]->[1] : 0;

    my $sth = $dbh->prepare("INSERT INTO barcode_collection_item 
			     (collection_id, barcode, rank) 
			     VALUES (?, ?, ?)");
    
    $sth->execute($collid, $_, ++$rank) for @remaining;

    scalar(@remaining);
}

sub bcdeletefromcollection
{
    my ($collid, $codes) = @_;

    #Will delete all the given codes and report the number of successes.  Codes in the list but not
    #in the collection will have no effect.
    $codes and die "Deleting just a subset of codes currently doesn't work!";

    my $deletions = $dbh->do('DELETE FROM barcode_collection_item WHERE collection_id = ?', undef, $collid);

    return $deletions;
}

sub bcdeletecollection
{
    my ($collid) = @_;

    #Expunge a whole collection.  Should I even allow this???
    $dbh->do("DELETE FROM barcode_collection_item WHERE collection_id = ?", undef, $collid);

    $dbh->do("DELETE FROM barcode_collection WHERE id = ?", undef, $collid) or die
	"Failed to delete collection with ID $collid.\n";
}

sub {
    local our @EXPORT =  qw(bccreatecollection bcupdatecollection bcappendtocollection 
			    bcdeletefromcollection bcdeletecollection);
    barcodeUtil->export_to_level(1);
};

} #end package spazz

->();#  # Is this some kind of ASCII-art dude?


main();

