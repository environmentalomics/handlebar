#!/usr/bin/perl
use strict; use warnings;

# CVS $Revision: 1.17 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#Testing - capture all warnings.
# use Carp;
# $SIG{__WARN__} = sub { confess(@_) }; 

# Request some barcodes for yourself.
use barcodeUtil('-connect');
use TableIO;
#use Encode;

# Detect mod_perl
our $apache = shift if($_[0] =~ /Apache/);
if($apache)
{
    die "This code is too crufty to run under mod_perl, and is not going to do so " .
	    "without a MAJOR cleanup!\n ";
}
#Basically, the -connect junk in barcodeUtil needs to be ripped out so that:
# - The module is initialised once
# - The configuration is read and reset on each run
# - The CGI object is generated once on each run
# (if several Handlebars are running, the module may be using a different config each time,
#  so a full flush is best!)
# - The database connections are properly cached (or re-made every time)
#My cruft about connecting in the BEGIN stage will no longer wash. 

# I also need to use something like CGI::Application and have a single stub script to dispatch
# calls to the right run modes.  This would allow me to run several instances on one server without
# a load of messy symlinks (GenQuery does this properly!)

# No need to load CGI::Carp - barcodeUtil does this for you!
#  use CGI::Carp qw(fatalsToBrowser);

#First load in the config file

our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};
our $DISPOSE_MASK = $CONFIG{DISPOSE_MASK} || '--';
our $MAX_CODES = $barcodeUtil::MAX_CODES;
our $STRICT_USER_NAMES = $barcodeUtil::STRICT_USER_NAMES;
our $STYLESHEET = $barcodeUtil::STYLESHEET;
our $ENABLE_PRINTING = $barcodeUtil::ENABLE_PRINTING;

our $PAGE_MAINTAINER = $CONFIG{PAGE_MAINTAINER};

#A CGI query object
our $q = bcgetqueryobj();

#Trap if I manage to get stuck in some error loop
#due to my crazy error handling.
our $errorloop = 0;

#Other modules
use Data::Dumper; #For teh debugging and some error reporting
use IO::String;
{ package IO::String; no warnings;
  sub str{${shift()->string_ref }} }

#Get params
our $username = $q->param("username");
our $bctype = $q->param("bctype");
our $bcquantity = bcdequote($q->param("bcquantity")); 
our $bccomments = $q->param("bccomments");
our $bcreqrange = bcdequote($q->param("bcreqrange")); 
our $impfile = $q->param("impfile");
our $displist = $q->param("displist");
our $dispcomments = $q->param("dispcomments");

#Set auto-newline so the HTML source is legible
$\ = "\n";

#Things we may need to do:
#
# 1) Display the request form
# 2) Allocate some numbers
# 2a) Show some information about a type. (popup)
# 2b) Show table of users of the system. (popup)
# 3) Confirm allocation and offer download
# 4) Confirm search and offer download of data.
# 5) Receive updates and report result (2 phase?)
# 7) Generate a CSV (or whatever) file
# 8) Dispose a batch of codes.

#Validate user, numbers, etc.
sub main
{
    my $error = "";

MAIN: for(1){

    if($q->param("reqcsv")) #7
    {
	$q->delete("reqcsv");
	
 	my $base = bcdequote($q->param("base") || $q->param("blocklist")) or 
  	    $error="Internal error: Request for export made with no valid base specified.", last MAIN;

	my($dispoption, $expformat); 
	for($q->param("dispoption") || '')
	{
	    $dispoption = 'mask';
	    /omit/i and $dispoption = 'omit';
	    /include/i and $dispoption = 'incl';
	}

	#reqcsv should not report any user errors.  It may die with an internal
	#error in which case CGI::Carp will pick up the pieces.
	$expformat = $q->param("expformat");
	reqcsv($base, $dispoption, $expformat);

	#reqcsv will output a text file.  We don't want any stray HTML in there, 
	#so at this point return:
	return 1;
    }

    #Only emit the header if this was not a download request.
    print bcheader();
    
    if($q->param("typespopup")) #2a
    {
	#Now as a convenience we can supply a list of types, comma sepearted.
	#Default is to show all types in alphabetical order.
	my $typeslist;
	if(my $tl = $q->param("tl"))
	{
		$typeslist = [split(",", $tl)];
	}
	
	print $q->start_html( -style=>{src=>$STYLESHEET}, -title=>"Info" ),
		  $q->div( {-id=>"typereport"},
		$q->h3("Types of barcode available") .
		bctypereport($typeslist)
		  );
	last MAIN;
    }

    if($q->param("userpopup")) #2b
    {
	print $q->start_html( -style=>{src=>$STYLESHEET}, -title=>"Info" ),
	      $q->div( {-id=>"userreport"},
		    $q->h3("Registered users of the barcode system") .
		    bcuserreport()
	      );
	last MAIN;
    }

    if($q->param("reqcodes")) #2
    {
	$q->delete("reqcodes");
	
	#Some quick checking
	$username or $error =
		"You need to supply a user name - click <u>Show Users</u> to see a list.", last MAIN;
	bcchkuser($username) or $error = 
		"The user '$username' is not known - click <u>Show Users</u> to see a list.", last MAIN;
	
	$bcquantity or $error = 
		"How many barcodes do you want to allocate?", last MAIN;
	$bcquantity <= $MAX_CODES or $error =
		"You can only request up to $MAX_CODES barcodes at a time.", last MAIN; 

	#Check bctype is valid - this is a security issue since this string will
	#be pasted unquoted into SQL.
	my $bcrealtype =  bczapspaces($bctype);
	bcchkbctype($bcrealtype) or $error="Internal error: Invalid barcode type set.", last MAIN;

	my $base = bcallocate($bcquantity, $username, $bcrealtype, $bccomments) 
		    or $error="Failed to allocate codes! Aieeee!!!", last MAIN; 
	my $qbase = bcquote($base);
	my $lastcode = bcquote($base + $bcquantity - 1);

	#Construct a link to the printing page
	my $printingpage = "print_barcodes.cgi?fromcode=$qbase&tocode=$lastcode&username=$username";

	#Offer a download
	print bcstarthtml("Request successful"),
	      bcnavbanner(),
	      bch1("Barcodes allocated"),
	      $q->p("You have allocated the block of barcodes from $qbase to $lastcode
	             inclusive to user <b>$username</b>. <br /> 
		     These codes now refer to samples of the type <b>$bctype</b>" .
		     ($bccomments 
			? $q->escapeHTML(", with the comment: \"$bccomments\"")
			: ""
		     ) .
		     ". <br /><br />
		     You should now download an empty data template and fill it out
		     in your favoured spreadsheet program."),
	      offer_download($base);
	if($ENABLE_PRINTING)
	{
	    print $q->p("Print or request labels with these codes : " .
		  $q->a({-href=>$printingpage}, "Go to printing page") );
	}
	print $q->hr,
	      $q->p({style=>"font-weight:bold"},
		     "The format of the records is as follows:"),
	      bcdescribetype($bcrealtype);
	
	last MAIN;
    }

    if($q->param("reqexp")) #4
    {
	$q->delete("reqexp");
	
	#Determine the base of this allocation block
	#If code is invalid we just end up with undef.
	my $base;
  	$base = ( $bcreqrange ? bcrangemembertobase($bcreqrange) : undef);

	#So the user has supplied a name and possibly a code.
	#Validate the name and show them the list of their stuff,
	#with the appropriate line selected if appropriate.
	if(!$username)
	{
	    if($STRICT_USER_NAMES)
	    {
		$error =  
		"You need to supply a user name - click <u>Show Users</u> to see a list.", last MAIN;
	    }
	    elsif(!$base)
	    {
		#The user supplied an invalid code
		$error =
		"You need to supply a username or a valid barcode in the range to be downloaded.", last MAIN;
	    }
	    else
	    {
		#It's OK - we can infer the user name from the code
		($username) = bcgetinfofornumber($base);
	    }
	}
	else
	{
	    bcchkuser($username) or $error = 
		"The user $username is not known - click <u>Show Users</u> to see a list.", last MAIN;

	    #We have a problem if the code does not belong to the user...
	    if($base)
	    {
		[bcgetinfofornumber($base)]->[0] eq $username or $base = undef;
	    }
	}

	#What if several username boxes are filled in?
	#We're ok - only the one for the submitted form gets sent.

	#Right ho:
	print bcstarthtml("$PAGE_TITLE - Main Request Interface"),
	      bcnavbanner(),
	      bch1("Ready to export barcode data"),
	      expform2($base);
	
	last MAIN;
    }
    
    if($q->param("reqimp")) #5
    {
	$q->delete("reqimp");

	my $headings;
	my @numbers;
	my ($owner, $type, $count, $tcount, $empties, $addedrows);
	
	#Check that a file has been provided and that we can load it into DBD::AnyData
	$impfile or $error="You must supply a spreadsheet or CSV file to be uploaded", last MAIN;
	my $impfilehandle = $q->upload("impfile") or
		$error=$q->cgi_error() || "Internal server error - unable to process uploaded file.", last MAIN;

	#Save the file in the log for later
	my ($impfileextn) = ($impfile =~ /.*\.(.*)/);
	binmode $impfilehandle;
	bclogevent( 'upload', $username || 'blank', 0, $impfileextn, $impfilehandle );

	my $tableio = new TableIO();
	my $impreader;
	
	eval{$impreader = $tableio->get_reader($impfilehandle, $impfile)};
	    $@ and $error="Unable to load the file:\n$@", last MAIN;

	#Check that there is a 'barcode' column
	my $bcfound = $impreader->find_barcode_column();
	defined($bcfound) or $error="No barcode column found in the uploaded file.", last MAIN;
		
	#Get numbers (ie the barcode column)
	@numbers = @{$impreader->get_all_barcodes()};
	#Ensure that there is no junk or blanks, as this stuffs up the SQL later
	$tcount = @numbers; #The total rows in the file.
	@numbers = map {bcdequote($_) || ()} @numbers;
	$count = @numbers or $error="No data in this file!", last MAIN;

	#Validate that all numbers are of same type and owner
	for($numbers[0])
	{
	    eval{
		($owner, $type) = bcgetinfofornumber($_);
	    };
	    $@ and $error="While checking first line ($_):\n$@", last MAIN;

	    #If strict user checking is in force, check now.
	    if($STRICT_USER_NAMES)
	    {
		 my $idxq = bcquote($_);
		 $username or $error = "You need to give a username to upload data.", last MAIN;

		 $username eq $owner or $error =
		    "You are trying to modify code $idxq but it belongs to $owner and you gave the username $username.",
		    last MAIN;
	    }
	}
	for(my $nn=1; $nn < @numbers; $nn++)
	{
	    my ($xowner, $xtype);
	    eval{
		($xowner, $xtype) = bcgetinfofornumber($numbers[$nn])
	    };
	    $@ and $error="While checking line " . ($nn + 1) . " (code " . bcquote($numbers[$nn]) . "):\n$@", last MAIN;
	    $xowner ne $owner and $error="All barcodes in an uploaded file must have the same owner.\n".
					 "Barcodes in this file belong to both $owner and $xowner.", last MAIN;
	    $xtype ne $type and $error="All barcodes in an uploaded file must be of the same type.\n".
				       "Barcodes of both types $type and $xtype found in this file.", last MAIN;

	}
	
	#Print a message saying please wait
	print bcstarthtml("$PAGE_TITLE - Main Request Interface"),
	      bcnavbanner(),
	      bch1("Data import in progress"),
	      $q->p("Reading file <i>$impfile</i>"),
	      $q->p("<b>$count codes</b> found of type <b>" . bczapunderscores($type). "</b> with owner <b>$owner</b>."),
	      $q->p("Processing...");
	      
	#Strip out disposed numbers
	my %disposedhash;
	for(@numbers)
	{
	    $disposedhash{$_}++ if bcdisposedateandcomments($_);
	}
	@numbers = grep {!$disposedhash{$_}} @numbers;
	my $disposedcount = scalar(keys(%disposedhash));
	
	#Delete, then re-insert all rows
	eval{ 
	    my $deletedhash = bcexpungerecords(\@numbers, $type);
	    $empties = importrecords($impreader, $bcfound, $type, $deletedhash, \%disposedhash); 
	    #The number of new rows will be $tcount - $empties - $disposedcount - scalar(keys(%$deletedhash)) 
	    $addedrows = $tcount - $empties - $disposedcount - scalar(keys(%$deletedhash));

	    #Now is a good time to update the link index
	    #This is the only point I should need to worry about indexing as it is the only time the data
	    #tables get updated.
	    require barcodeIndexer;
	    barcodeIndexer::indexcodes(@numbers);
	};
	if($@)
	{
	    #Not too good
	    bcrollback();
	    $impreader->flush();
	    $error="Failed to process all records - all updates have been rolled back.\n
		    $@", last MAIN;
	}
	
	#Commit
	bccommit();

	#Were there empties, disposed, etc?  Report!
	print $q->start_p;

	#Remember that empties = completely blank lines + lines without data
	$empties and print 
	    "Skipped <b>$empties empty lines</b> in the imported file.", $q->br;
	$disposedcount and print 
	    "Will not update <b>$disposedcount disposed codes</b>.", $q->br;
	$empties + $disposedcount == $tcount and print
	    "All the lines in this file were empty or referred to disposed codes - nothing will be updated!", $q->br;
	$addedrows == 1 and print 
	    "<b>1 new record</b> was added.", $q->br;
	$addedrows != 1 and print 
	    "<b>$addedrows new records</b> were added.", $q->br;
	$empties + $disposedcount != $tcount and print
	    "Total of <b>", $tcount - $empties - $disposedcount, " lines</b> from this file logged in the database.", $q->br;

	print $q->end_p;
	
	#Report success.
	print   $q->p($q->b("DONE - All data successfully committed to the database.")), 
		$q->hr, $q->hr;
	
# 	$impreader->flush();
	#Don't quit - show the main page again.
    }
    
    if($q->param("reqdisp")) #8
    {
	$q->delete("reqdisp");

	#Remove rogue chars and normalise space
	my @disparr = eval{ displist_normalise($displist) };
	$@ and $error = $@, last MAIN;
	
	!@disparr and $error = "You did not specify any barcodes to dispose.", last MAIN;
	
	#Check that all codes are allocated
	my @notdisposable = checkallocated(\@disparr, 4);

	if(@notdisposable)
	{
	    if(@notdisposable == 1)
	    {
		#The only reason for refusing a disposal is if the thing is unallocated.
		$error = "The barcode " . bcquote($notdisposable[0]) . " is not allocated yet."; 
	    }
	    elsif(@notdisposable <= 3)
	    {
		$error = scalar(@notdisposable) . " of the barcodes you  asked to dispose of are not allocated.\n" .
			 "These were: " . join(', ', map {bcquote($_)} @notdisposable) . ".";
	    }
	    else
	    {
		$error = "Some of the barcodes you asked to dispose of are not allocated.\n" .
			 "eg. " . join(', ', map {bcquote($_)} @notdisposable[0..2]) . ", etc...";
	    }
	    last MAIN;
	}

	#Finally check the owner matches
	if($STRICT_USER_NAMES)
	{
	    $username or $error = "You must supply the correct user name to dispose of barcodes.", last MAIN;

	    for my $acode (@disparr)
	    {
		my ($codeowner) = bcgetinfofornumber($acode);
		if($username ne $codeowner)
		{
		    $error = "You are trying to dispose of code " . bcquote($acode) . " but it belongs to $codeowner, not $username.";
		    last MAIN;
		}
	    }
	}
	
	#Mark all deletions
	my($disposedlist, $nodatalist, $alreadydisplist) = bcdodisposal(\@disparr, $dispcomments);
	my $dispcount = @$disposedlist;
	my $nodatacount = @$nodatalist;
	my $alreadydispcount = @$alreadydisplist;
	my $totaldispcount = @$disposedlist + @$nodatalist;
	
	#Commit
	bccommit();

	#Log it
    	bclogevent( 'disp', $username, $disparr[0], undef,
		    "Disposed of " . @disparr . " codes owned by $username with comment:\n$dispcomments.\n" 
		    .formatcodes(\@disparr)
	);
	
	#Success
	$q->delete("displist");

	#Print message and then redisplay form.
	print bcstarthtml("$PAGE_TITLE - Main Request Interface"),
	      bcnavbanner(),
	      bch1("Disposing of " . @disparr . " barcode" . (@disparr != 1 ? "s" : ""));
	
	#Summary rules:
	#If there was just one code just say what happened.
	#Otherwise list by type.	

	print $q->start_p;
	if(@disparr == 1)
	{
	    #A single code
	    my $idxq = bcquote($disparr[0]);
	    print(
		($dispcount)
		    ? "Successfully disposed of barcode $idxq."
		    :($nodatacount)
			? "Successfully disposed of barcode $idxq, which was allocated but unused."
			: "The barcode $idxq was already marked as disposed!"
	    );
	}
	else
	{
	    #More than one code
	    print(
	      ($dispcount)
		? "The following $dispcount barcodes were marked disposed:" 
		  .formatcodes($disposedlist)
		: "",
	      ($nodatacount)
		? "The following $nodatacount barcodes were allocated but unused, and have been marked disposed:"
		  .formatcodes($nodatalist)
		: "",
	      ($alreadydispcount)
		? "The following $alreadydispcount codes have not been changed, as they are already disposed:"
		  .formatcodes($alreadydisplist)
		: ""
	    );
	}

	print
	      $q->end_p,
	      $q->p("No information has been removed from the database.  If you made a mistake and need to un-do
		     this disposal please use the \"Extra Admin\" menu or contact the database administrator."),
	      $q->hr, $q->hr;
    }

    #otherwise must be a new request #1

    print bcstarthtml("$PAGE_TITLE - Main Request Interface"),
	  bcnavbanner(),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Request interface"),
	  jumplinks(),
	  ( $CONFIG{PAGE_MESSAGE} ? $q->p($CONFIG{PAGE_MESSAGE}) : '' ),
	  reqform(),
	  $q->hr, expform(),
	  $q->hr, impform(),
	  $q->hr, dispform(),
	  $q->hr,
	  $q->p( $q->h4("Notes:"), $q->ul( {-id=>"noteslist"},
	    $q->li([ $q->a({-name=>'note1'}, "") .
		     "Use the main menu at the top of this page to access the various Handlebar features.",
		     "New types need to be defined within the underlying database.  To get a type added, 
		      please contact the system maintainer, $PAGE_MAINTAINER.  More information
		      can be found in the online help.",
		     "If you need to change ownership or type of records,
		      or you need to change the comment block then this can be done manually. 
		      Again, please contact the maintainer.",
		     "Usernames are used to keep track of who is doing what - there is
		      no security enforcement so you can make requests on behalf of any
		      other user.",
		   ]) 
	       ));
		    
    
}
#Ending bit
if($error)
{
    print bcheader(), bcstarthtml("Error - $PAGE_TITLE");
    $error =~ s/\n/<br \/>\n/g;
    print $q->p({-class=>"errorbox"},
	        "The following error occured:\n<br /><br />$error");

    #Log the error too
    bclogevent( 'error', $username || 'blank', 0, undef, $error );
		
    #Clear params and go again:
    if($errorloop++)
    {
	die "Oh dear - this script is broken.";
    }
    else
    {
	main();
    }
}
else
{
    print $q->end_div(), bcfooter();
}    
};#done main

sub jumplinks
{
    #Some quick links to navigate the page
    $q->p(  {-class => 'jumpto'}, 
	    "Jump to: " .
      $q->a({-href=>'#allocate'}, "Allocate") . 
      $q->a({-href=>'#retrieve'}, "Retrieve") . 
      $q->a({-href=>'#submit'}, "Submit") . 
      $q->a({-href=>'#dispose'}, "Dispose") 
    );
}

sub reqform
{
my $ios = new IO::String;

    #Generate link to view users or describe a type
    my $myurl = $q->url(-relative=>1);
    my $userlink = $q->a({ -href => "javascript:;",
			   -onClick => "window.open(
					'$myurl?userpopup=1', 'Info', 
					'width=800,height=600,resizable=yes,scrollbars=yes');" },
			 "Show users" );
    my $newuserlink = $q->a({ -href => "new_user_request.cgi" }, "Register new user");
    my $newtypelink = "Register new type - " . $q->a({ -href => "#note1" }, "see notes");
    my $typeslist = [bczapunderscores( @{bcgetbctypes({showhidden=>0})} )];
    my $typeslink = $q->a({-href => "javascript:;",
                           -onClick => 
			"window.open(
				'$myurl?typespopup=1#' + 
					zapspaces(
					  reqform.bctype[reqform.bctype.selectedIndex].value
					), 
				'Info',
				'width=800,height=600,resizable=yes,scrollbars=yes');" },
			  "Describe type" );

    print $ios
      $q->a({-name=>'allocate'}, ''),
      $q->start_form(-name=>"reqform", -method=>"POST"),
      $q->h2("Allocate a range of barcodes"),
      $q->p("You must request a range of barcodes before using them, and say
      what type of item they will be used to label.<br />
      It is better to request too many than too few.  You can request up to $MAX_CODES
      in a block."),
      $q->table( {-class => "formtable"},
	  $q->Tr($q->td( ["User name ", $q->textfield("username"), $userlink, $newuserlink] )),
	  $q->Tr($q->td( ["Type of item ",
			  $q->popup_menu( -name=>"bctype",
					  -values=>$typeslist ),
			  $typeslink, $newtypelink] )),
	  $q->Tr($q->td( ["How many ", $q->textfield("bcquantity"), ""] )),
	  $q->Tr($q->td( "Comment " ), 
		 $q->td({-colspan=>"3"}, $q->textfield({-size=>60, -name=>"bccomments"}))),
	  $q->Tr($q->td( ["", "", $q->submit( -name=>"reqcodes", -value=>"Make request")] )), 
      ),
      $q->end_form;

#Now we need a JS function which replaces spaces with underscores
    print $ios '<script type="text/javascript">',
	       bczapspaces_js(),
	       '</script>';

$ios->str;
}

sub expform
{
my $ios = new IO::String;
    #For getting a CSV file for an allocation block.
    #Will fill in data if it is there, otherwise will send out a template.


    
print $ios
      $q->a({-name=>'retrieve'}, ''),
      $q->start_form(-name=>"expform", -method=>"GET"),
      $q->h2("Retrieve a spreadsheet for an allocated range of codes"),
      $q->p( "You need to give your user name, and type in any number within the range
              of codes you want, or just click <b>retrieve</b> to see a list of all your codes."),
      $q->table( {-class => "formtable"},
	    $q->Tr($q->td( ["User name ", $q->textfield("username"), ""] )),
	    $q->Tr($q->td( ["Barcode in range ", $q->textfield("bcreqrange"), ""] )),
	    $q->Tr($q->td( ["", "", $q->submit( -name=>"reqexp", -value=>"Retrieve...")] )),
      ),
      $q->end_form;

$ios->str;
}

sub expform2
{
my $ios = new IO::String;

    my $base = shift();
    #Everything is validated (base is a real base or undef) - 
    #just emit a form with a link to download the CSV

    my $url = $q->url(relative=>1);
    my $retrlink = $q->a({ -href=> "",
                           -id=> "csvlink" },
                          "Nothing Selected" );

    #Get all allocation blocks for this user
    my $blocksforuser = bcgetblocksforuser($username);

    if($blocksforuser->active_blocks())
    {
        my $actualbase = $base || $blocksforuser->highest_active_base();
        print $ios  $q->start_form(-name=>"expform2", -method=>"GET"),
		    $q->p("These are the active blocks owned by $username:"),
		    $blocksforuser->render_scrolling_list({
					-default=> $actualbase,
				    #-onChange=> "javascript:setlink(this[this.selectedIndex].value)"
				    }),
		    $q->p("If the block of codes contains disposed items, you can choose to mask them
		           out with <b>$DISPOSE_MASK</b>, to include them as-is or else to omit them entirely.  If
			   you include any disposed codes in a file that you upload then they will simply
			   be skipped and not updated."),
		    $q->p("What to do with disposed codes? " . 
			$q->popup_menu({-name=>"dispoption", -values=>[qw(Mask Include Omit)], -default=>"Omit"})),
		    $q->p("Format for downloaded data: " . 
			$q->popup_menu({-name=>"expformat", 
					-values=>TableIO::get_format_names(), 
					-default=>"Excel"})),
                    $q->p("Click here to retrieve data : " . $q->submit(-name=>"reqcsv", -value=>"Download")),
                    $q->end_form;
		    
# 	my $baseurl = $q->url(-relative=>1,-query=>0);
#         print $ios '<script type="text/javascript">',
# 		   bcquote_js(),
# 	qq|
#                 function setlink(selected_barcode){
# 		    sb = bcquote(selected_barcode);
# 		    var newurl = "$baseurl?reqcsv=1&amp;base=" +sb;
# 		    document.getElementById("csvlink").href = newurl;
# 		    document.getElementById("csvlink").innerHTML = "CSV download (from " +sb+ ")";
#                 }
# 		setlink('$actualbase');
#                 </script>
#         |;

    }
    else
    {
        print $ios  $q->p("No active barcode blocks found in the database for $username.");
    }

$ios->str;
}

sub impform
{
my $ios = new IO::String;
    #Import - ie submit a CSV/Spreadsheet file to the database and get it checked in.
    #Don't forget that for file uploads you need to use 'start_multipart_form'

print $ios
      $q->a({-name=>'submit'}, ''),
      $q->start_multipart_form(-name=>"impform", -method=>"POST"),
      $q->h2("Submit barcode data to the central database"),
      $q->p( "Select a spreadsheet to save in the database.  
	      You can modify and re-submit the data as many times as you like."),
      $q->start_table( {-class => "formtable"} );
if($STRICT_USER_NAMES)
{
    print $ios
	  $q->Tr($q->td( ["User name ", $q->textfield("username"), ""] ));
}
print $ios
	  $q->Tr($q->td( ["File to upload ", $q->filefield(-name=>"impfile"),""] )),
	  $q->Tr($q->td( ["", "", $q->submit( -name=>"reqimp", -value=>"Submit")] )),
      $q->end_table,
      $q->end_form;

$ios->str;
}

sub dispform
{
my $ios = new IO::String;
    #Delete a barcode or a whole range of codes.
print $ios
      $q->a({-name=>'dispose'}, ''),
      $q->start_multipart_form(-name=>"dispform", method=>"POST"),
      $q->h2("Mark barcodes as being disposed"),
      $q->p( "If you are disposing of samples, you can tell the database that the barcodes
	      are no longer in use.  The information associated with the code will remain 
	      in the database for reference.  You can add a
	      comment to say who disposed of the items and why - the date will also be logged 
	      automatically."),
      $q->p( "Give a list of numbers to delete, separated by spaces or on several lines.  
	      You can also specify ranges of codes in the form " . bcquote(1230) . ":" . 
	      bcquote(1240) . "."),
      $q->start_table( {-class => "formtable"} ),
	  $q->Tr($q->td( [ 'Codes',
			   $q->textarea( -name=>'displist',
                                         -rows=>8,
		                         -columns=>40 ), '' ]));
if($STRICT_USER_NAMES)
{
    print $ios
	  $q->Tr($q->td( ["User name ", $q->textfield("username"), ''] ));
}
print $ios
	  $q->Tr($q->td( ["Comments ", $q->textfield({-size=>40 , -name=>"dispcomments"}), ''] )),
	  $q->Tr($q->td( [ '', '', $q->submit( -name=>"reqdisp", -value=>"Submit") ])),
	  $q->end_table;
      ;
$ios->str;
}

#Given an array of codes, check that they are all allocated
#give up after $failures failures
sub checkallocated
{
    my $codes = shift;
    my $failures = shift || 1;

    my @failedlist;

    for my $acode(@$codes)
    {
	eval{ bcgetinfofornumber($acode); };
	if($@)
	{
	    push @failedlist, $acode;
	    last unless --$failures;
	}
    }

    return @failedlist;
}


sub displist_normalise
{
    #Take the argument with the numbers in and return an array of codes
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
		if(/^\d+$/) { push(@res, $_) }
			elsif(/^(\d+):(\d+)$/)
		{
			if(abs($2 - $1) > 10000) { die "Range $_ is larger than the maximum number of codes allowed  
							for disposal in one go.  Aborting.\n" };
			if($2 < $1) { push(@res, $2..$1) }
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

sub offer_download
{
my $ios = new IO::String;
    #Offer the user the ability to download a CSV file (hopefully an OO file soon)
    #caller guarantees that $base is a sensible number
    my $base = shift;
    
    my $link = $q->url(-relative=>1) . "?reqexp=1&bcreqrange=$base&username=$username";

    #TODO - make sure this offers alternative formats.
    print $ios $q->p("Click here to retrieve template : ",
		    $q->a({-href=>$link}, "Download Template")
		    ),
	       ;
	    
$ios->str;
}

sub importrecords
{
    my ( $tio,		#Active TableIO object to read records from table
         $bcfound,	#Column containing barcode
         $type,
         $deletedhash,	#All the codes found in the file that were already in the DB
         $disposedhash ) = @_;

    my $table = bctypetotable($type);
    my $headings = $tio->get_column_names;

    my $empties = 0;
    #We need to deal with column name mismatches and fail or warn gracefully.
    #First off, must make sure that all the column names are valid SQL identifiers, and detect
    #any empty columns.
    #Then later if there is a header mismatch it will be caught by the database
    #Note - I'd originally assumed that the sheet would be rectangular, but it seems not - ie.
    #we may see longer rows (but not shorter??) further down.  Fortunately these are caught later
    #because the database sees extra bind values.  Leave in the check here as it is still applicable
    #to CSV.
    {local $Data::Dumper::Terse = 1;
    $headings = [map {tr/ /_/; s/\W//g; $_ || 
			   die "Invalid or blank column heading in first row of input file. " .
			       "This normally means that data has been inserted into a cell " .
			       "to the right of the last column which causes the sheet to expand and " .
			       "empty (undefined) headings to appear at the end. " .
			       "If this was the case please delete the whole final column and retry.\n" .
			       "Headings found were: \n" .
			       Dumper($headings)
		     } @$headings];
    }

    #See which columns are barcodes, other than the actual barcode.
    my @colswithbarcodes = ();
    for(my $nn = 0; $nn < @$headings; $nn++)
    {
	if(bcgetflagsforfield($type, $headings->[$nn])->{bc})
	{
	    push @colswithbarcodes, $nn;
	}
    }

    #Any old records should have been expunged, so just insert the new ones.
    my $inserth = bcprepare("
	    INSERT INTO $table (" . join(', ', @$headings) . ")
	    VALUES (" . join(', ', ('?') x @$headings) .")
	    ");
    while( my $row = $tio->get_next_row() )
    {
	#Have to check and then dereference.
	my @row = @$row or last;
    
	my $fieldsfound = 0;
	map { $fieldsfound++ if defined $_ && $_ ne '' } @row;

	#Skip totally blank rows
	if($fieldsfound == 0){ $empties++; next; }

	#Grab the barcode.  Note that this may still contain a hyphen or some other
	#junk, so force it to a number.
	my @rowcopy = @row;
	my $thisbarcode = $row[$bcfound] = bcdequote($row[$bcfound]);

	#Abort if there is a non-blank row with no barcode
	if(!$thisbarcode)
	{
	    die "The uploaded file contains a line with no value in the barcode column.\n",
		"Please erase any extraneous lines from the file before uploading.\n";
	}

	#Skip over anything in the disposed hash
	if($disposedhash->{$thisbarcode}) { next; }

	#Skip blank rows which are not in the deleted hash, ie. there was no data
	#for them anyway, else abort because the data has been removed.
	if($fieldsfound == 1)
	{
	    #We should be able to tell if the record existed beforehand
	    #and thus if we need to worry about deleting it.
	    if(! $deletedhash->{$thisbarcode})
	    {
		$empties++;
		next;
	    }
	    
	    #Make a custom warning for any row with just one field
	    #(which will be the previously-validated barcode)
	    #unless the thing was already blank.
	    die "The uploaded file contains a blank entry for barcode ", bcquote($thisbarcode),
		".\nIf you wanted to delete the existing record then the database ",
		"administrator must do this.",
		"\nIf you want to mark the codes as ",
		"being disposed, use the option on the main form, otherwise remove ",
		"this entire line from the spreadsheet to leave the record untouched.\n";
	}

	#Finally, de-quote any barcode fields before they go in
	$row[$_] = bcdequote($row[$_]) for @colswithbarcodes;

	#Finally finally, trim off any undefined values if the row is too long
	while(@row > @$headings && !defined($row[-1]))
	{
	    pop @row;
	}

	eval{
	    $inserth->execute(@row);
	};
	if($@)
	{
	    #Grab PG specific error number (always 7 unfortunately :-( )
	    # my $errnum = $inserth->err;
	    my $err = $inserth->errstr();
	    chomp($err);

	    #If this was a check constraint let the user know what it said, even though
	    #it is liable to be cryptic if you don't grok SQL
	    if($err =~ /violates check constraint "(\w+)"/)
	    {eval{
		#This diagnosis should be done after the database handle cleanup,
		#so I have to rollback early, which is a hack, but the alternative is to
		#re-factor the code (which I should) or to pull apart the message later, which
		#is also a hack.
		$inserth->finish();
 		bcrollback();
		my $csth = bcprepare("
		    SELECT consrc FROM pg_constraint con 
		    INNER JOIN pg_class c ON c.oid = con.conrelid 
		    WHERE contype = 'c' AND c.relname = ?
		    AND conname = ? LIMIT 1");
		$csth->execute($type, $1);
		my ($cdef) = $csth->fetchrow_array();

		if($cdef)
		{
		    $err .= "\n\nThe definition of the \"$1\" constraint is:
			     $cdef";
		}
	    };}

	    my $report = "The message from the server was:
			  $err\n 
			  The line in question was:";
	    for(my $nn = 0; $nn < @$headings || $nn < @rowcopy ; $nn++)
	    {
		my $hlabel = $headings->[$nn] || "!_extra_column_" . ($nn+1);
		$report .= $q->escapeHTML("\n$hlabel = ") .
			( defined $rowcopy[$nn] ? $q->escapeHTML($rowcopy[$nn]) : $q->i('NULL') );
	    }

	    #Re-throw the error
	    if($err =~ /fail to add null value in not null attribute/i)
	    {
		#Special case for NULL errors
		die "A compulsory field in a record was left empty.
		     \n$report\n"; 
	    }
	    elsif($err =~ /cannot insert a duplicate key into unique index/i)
	    {
		#Also for duplicate rows, which will not be caught by the code checker
		#since it seems superfluous to do so but will end up here, assuming you added a unique
		#index to the table for the barcode column - which you should!
		die "There is a duplicate entry - ie. two lines with the same barcode - in the uploaded file.
		     \n$report\n";
	    }
	    elsif($err =~ /called with \d+ bind variables when \d+ are needed/)
	    {
		#For rows which have data beyond the end of the row.
		die "A record contains extra data beyond the last \"$headings->[-1]\" column in the ",
		    "spreadsheet.  If this information is to be recorded, you should put it into the ",
		    "appropriate column.  Otherwise, delete the column(s) and resubmit.
		    \n$report\n";
	    }
	    else
	    {
		die "A data validation error occurred.  A record in your uploaded file does not validate against the ",
		    "type definition for " .bczapunderscores($type). ".
		     \n$report\n";
	    }
	}
    }
    
    #The function returns how many rows contained no data.    
    return $empties;
}

#Before reqcsv here is a little function which, given an arrayref
#and an index, shunts that item to the end of the array.
sub pushtoend
{
    my ($arr, $idx) = @_;
    push(@$arr, splice(@$arr, $idx, 1));
}

sub reqcsv
{
    #Grab the range from the database

    #This is called after the user has confirmed the range, so we 
    #don't need to re-check the user name, and if $fromcode is invalid
    #then it is an internal error.
    #This used to write the CSV directly, but now defers to TableIO

    local $\ = undef; #Deal with my own linefeeds for this bit
    
    my $fromcode = shift();
    my $dispoption = shift();
    my $filetype = shift() || "unspecified";
    my($tocode, $auser, $atype) = bccodetorange($fromcode);    

    die "Internal error: Base cannot be resolved to range" unless $tocode;
#     return "Username mismatch (user is $username but these records belong to
#             $auser)" unless $username eq $auser;

    my $fname = "${atype}_" . bcquote($fromcode) . "_to_" . bcquote($tocode);

    #Grab all relevant metadata
    my $idx = $fromcode;
    my $sth = bcprepare("
	    SELECT * FROM " . bctypetotable($atype) . " 
	    LIMIT 1");
    $sth->execute();

    #We need to know about the headers, data or no data
    my @headings = @{$sth->{NAME}};
    die "Internal error - the first column of every data table must be 'barcode int8'"
	unless $headings[0] eq 'barcode';
    $sth->finish();

    #See which columns need to be demoted or removed.  Can the barcode column be demoted?  Currently not.
    my @demotionflags = ('K'); #Can be Keep, Demote, Noexport
    my (@headings1, @headings2) = $headings[0];
    for(my $nn = 1; $nn < @headings; $nn++)
    {
	my $flags = bcgetflagsforfield($atype, $headings[$nn]);

	#Shuffle and filter the headings
	if($flags->{noexport})
	{
	    $demotionflags[$nn] = 'N';

	}
	elsif($flags->{demote})
	{
	    $demotionflags[$nn] = 'D';
	    push @headings2, $headings[$nn]; 
	}
	else
	{
	    $demotionflags[$nn] = 'K';
	    push @headings1, $headings[$nn];
	}
    }
    @headings = (@headings1, @headings2);

    #Create the writer object.
    my $tableio = new TableIO();
    my $expwriter = $tableio->get_writer($filetype);

    #How to print an empty line
    my $bcprintempty = sub {
	my $idx = shift();
	my $idxq = bcquote($idx);
	#Is it disposed?
	if(bcdisposedateandcomments($idx))
	{
	    if($dispoption eq 'incl'){
		$expwriter->add_empty_disposed($idxq);
	    }elsif($dispoption eq 'mask'){
		$expwriter->add_masked_disposed($idxq, $DISPOSE_MASK);
	    }
	    #else do nothing
	}
	else
	{
	    $expwriter->add_empty($idxq);
	}
    };

    #Appropriate header
    print bcheader(-type=>$expwriter->mime_type, 
		   -content_disposition=>"attachment;filename=$fname." . $expwriter->file_extension);
    #Too late to have an error message now!

    #Add a suitable header to the file
    $expwriter->set_header("${atype}: owner $auser on " . scalar(localtime));

    #Set column headings, removing underscores.
    $expwriter->set_column_names(bczapunderscores(@headings));
    
    #Work out which of the columns is flagged as a barcode - the first one will be
    #a barcode by default.
    #Set up the column descriptions properly
    #Both of these can only be done once the demotions have been completed, so I can't
    #put this in the loop above.  I think we can live with the inefficiency.
    my @colswithbarcodes = (0);
    my (%descidx, @descdata);

    #Get the table definitions out of the database.
    bcgetcolumninfo($atype, \%descidx, \@descdata);

    for(my $nn = 1; $nn < @headings; $nn++)
    {
	my %attrs = ();
	#Indirected lookup necessitated due to column demoting.
	my $desc = $descdata[$descidx{$headings[$nn]}];
    
	my $flags = bcgetflagsforfield($atype, $headings[$nn]);
	if($flags->{bc})
	{
	    push @colswithbarcodes, $nn;
	    $attrs{type} = 'barcode';
	    $attrs{format} = 'bc';
	}
	else
	{
	    #Extract real format
	    my( $typename, $columnsize ) = bcsqltypedemystify($desc->{TYPE_NAME}, $desc->{COLUMN_SIZE});
 	    $attrs{type} = $columnsize ? "$typename($columnsize)" : "$typename";
	    if($typename eq 'date')
	    {
		#TODO - review dates once Excel export is in place.
		$attrs{type} = "date(yyyy-mm-dd)";
		$attrs{format} = 'date';
	    }
	    elsif($typename =~ /^int/)
	    {
		$attrs{format} = '0';
	    }
	    elsif($typename eq 'real')
	    {
		$attrs{format} = '4'; #Arbitrary
	    }
	    #Otherwise no format - should default to text.
	}

	#Determine if the thing is required or nullable.
	$attrs{compulsory} = ! $desc->{NULLABLE};	
	
	$expwriter->set_attr($nn, \%attrs);
    }

    $sth = bcprepare("
	    SELECT * FROM " . bctypetotable($atype) . " WHERE
	    barcode >= $fromcode AND
	    barcode <= $tocode
	    ORDER BY barcode ASC");
    $sth->execute();

    while(my @data = $sth->fetchrow_array)
    {
	#Filter for demotions
	my(@data1, @data2);
	for(my $nn = 0; $nn < @demotionflags; $nn++)
	{
	    if($demotionflags[$nn] eq 'K')
	    {
		push @data1, $data[$nn];
	    }
	    elsif($demotionflags[$nn] eq 'D')
	    {
		push @data2, $data[$nn];
	    }
	}
	@data = (@data1, @data2);

	#The next idx may not match up with this row, since there will be no
	#row until data is entered.
	while( $idx < $data[0] )
	{
	    &$bcprintempty($idx);
	    $idx++;
	}
	#Do I need to modify any of the columns before printing?
	#Yes - quote all the columns which have barcodes in
	#(The barcode flags are calculated after the demotion step above)
	$data[$_] = bcquote($data[$_]) for @colswithbarcodes;

	#Is it disposed?
	if(bcdisposedateandcomments($idx))
	{
	    if($dispoption eq 'incl'){
		$expwriter->add_disposed(@data);
	    }elsif($dispoption eq 'mask'){
		$expwriter->add_masked_disposed($data[0], $DISPOSE_MASK);
	    }
	    #else do nothing
	}
	else
	{
	    $expwriter->add_row(@data);
	}
	$idx++;
    }
    
    #Spit out empty rows for all the rest
    while($idx <= $tocode)
    {
	#Is it disposed?
	&$bcprintempty($idx);
        $idx++;
    }

    #And print the lot
    $expwriter->print_out();
}

sub formatcodes
{
    #Format a big list of codes using <pre>
    my @codes = map {bcquote $_} @{shift()};
    
    my $ret = "<pre>\n";
    while(my $block = join(', ', splice(@codes, 0, 20)))
    {
	$ret .= "$block\n";
    }
    $ret .= "</pre>";
}

#The hook into main.
{
    main();
    bcdisconnect();
}

