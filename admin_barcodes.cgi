#!/usr/bin/perl
use strict; use warnings;

# CVS $Revision: 0.00 $ committed on $Date: 2006/04/20 08:34:45 $ by $Author: tbooth $

# This page provides some advanced admin functions for the barcode database.
# If you want to allow users to do these things set ENABLE_ADMIN or
# or PASSWORD_FOR_ADMIN in the config file.
# To enable only certain admin functions set ADMIN_FUNCTIONS to a comma separated
# list.  If a both PASSWORD_FOR_ADMIN and ADMIN_FUNCTIONS are set then all functions
# will be available but those not in the list will require a passowrd.

use barcodeUtil;
use barcodeTypeExporter;
use Data::Dumper;
# use IO::String; #Should not be needed for perl 5.8+

# Grab config
our %CONFIG = %{bcgetconfig()};
our $ENABLE_ADMIN = $CONFIG{ENABLE_ADMIN} ? 1 : 0;
our $PASSWORD_FOR_ADMIN = $CONFIG{PASSWORD_FOR_ADMIN};
our $ADMIN_FUNCTIONS = $CONFIG{ADMIN_FUNCTIONS};
our $PAGE_DESC = $CONFIG{PAGE_DESC};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};

$barcodeTypeExporter::PG_DUMP = $CONFIG{PG_DUMP} || 'pg_dump';

#Setting a password implies turning on admin
#Er, no, keep it simple - eh?
#$ENABLE_ADMIN = 1 if $PASSWORD_FOR_ADMIN;

#A CGI query object
my $q = bcgetqueryobj();
my $dbh;

#What can we do?  Some things are still unimplemented.
#my @ALLFUNCS = qw(steal split grow shrink convert usermodify blockmodify undispose deallocate reindex export);
my @ALLFUNCS = qw(steal split usermodify blockmodify undispose deallocate reindex export);
my (%FORMS, %ACTIONS); #Hashes of functions - defined after main()

# Determine what functions are available,passworded,disabled
sub main
{
    my(%funcs_avail, %funcs_pwd);
   
    if(!$ENABLE_ADMIN)
    {
	#No functions are available - you should not be here!
    }
    elsif($ADMIN_FUNCTIONS)
    {
	my %funcs_listed;
	$funcs_listed{$_}++ for (ref($ADMIN_FUNCTIONS) ? @$ADMIN_FUNCTIONS : $ADMIN_FUNCTIONS);
    
	if($PASSWORD_FOR_ADMIN)
	{
	    #Everything goes in either the avail or pwd list
	    for(@ALLFUNCS)
	    {
		($funcs_listed{$_} ? \%funcs_avail : \%funcs_pwd)->{$_}++ for @ALLFUNCS;
	    }
	}
	else 
	{
	    #Everything is available or out the window
	    {
		for(@ALLFUNCS)
		{
		    $funcs_avail{$_}++ if $funcs_listed{$_}
		}
	    }
	}
    }
    else
    {
	#Bung all into the correct hash
	($PASSWORD_FOR_ADMIN ? \%funcs_pwd : \%funcs_avail)->{$_}++ for @ALLFUNCS;
    }

    #Debug:
    #print Dumper(\%funcs_avail, \%funcs_pwd);

    my $output = "";
    #Is there an action to do?
    if(my $action = $q->param('action'))
    {
	#Special case for export_dl.  Should check the password, but never mind, this isn't the Pentagon...
	if($action eq 'export_dl' && $funcs_avail{export})
	{
	    barcodeUtil::connectnow();
	    eval{print do_export_dl()};
	    my $lasterr = $@;
	    bcdisconnect();
	    return unless $lasterr;

	    #There must have been an error.
	    $output = gen_error($lasterr);
	}
    	else
	{
	    if($funcs_pwd{$action})
	    {
		if($PASSWORD_FOR_ADMIN = $q->param('password'))
		{
		    $output = do_action($action);
		}
		else
		{
		    $output = gen_error("You did not supply the correct password for action '$action'.");
		}
	    }
	    elsif($funcs_avail{$action})
	    {
		$output = do_action($action);
	    }
	    else
	    {
		$output = gen_error("The action '$action' is either invalid or unavailable.");
	    }
	}
    }

    #Let's have some output
    if($output)
    {
	$output .= "\n" . $q->hr();
    }
    
    my @availfuncs = grep {$funcs_pwd{$_} || $funcs_avail{$_}} @ALLFUNCS;

    print bcheader,
	  bcstarthtml("$PAGE_TITLE - Extra Admin"),
	  bcnavbanner,
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Administrative tasks"),
	  jumplinks(@availfuncs),
	  $q->p({-class=>"result"}, $output);
	  
	  #$q->h2("Available admin tasks");
    
    
    my $passprompt = 
	$q->Tr($q->td({-colspan=>"2"}, "<i>You need to supply the admin password to use this function</i>")) .
	$q->Tr($q->td( ["Password ", $q->password_field(-name=>'password')] ));
    for(@availfuncs)
    {	
	$q->param( action => $_ );
	print $q->a({-name=>$_}, '');
	if($funcs_pwd{$_})
	{
	    print &{$FORMS{$_}}(passprompt => $passprompt);
	}
	elsif($funcs_avail{$_})
	{
	    print &{$FORMS{$_}}(passprompt => "\n");
	}
	#It must have been in one or the other!
    }

    #The footer
    print $q->end_div(), bcfooter();

}

sub jumplinks
{
    my $res = "\n" .
    #Some quick links to navigate the page
    $q->start_p( {-class => 'jumpto'} ) . "Jump to: ";

    my $nn = 0;
    for(@_)
    {
	$res .=  $q->a({-href=>"#$_"}, ucfirst($_));
    };
    $res .= $q->end_p() . "\n";
    $res;
}


sub do_action
{
    my $action = shift;
    my $func = $ACTIONS{$action} or return gen_error(
	"Sorry - the action '$action' is not yet supported in this release of the software."
	);
    barcodeUtil::connectnow();
    my $res = eval{ &$func(@_) };
    my $error = $@;
    bcdisconnect();
#     $@ ? gen_error($@) : $res;

    #Now with logging:
    my $saved_query = '';
    open my $ios, \$saved_query;
    $q->save($ios);
    if($error)
    {
	my $error_report = gen_error($error);

	bclogevent( 'error', $action, int_nowarn($q->param('basecode')), undef,
		    "$saved_query\n$error_report" );
	return $error_report;
    }
    #else
    bclogevent( 'admin', $action, int_nowarn($q->param('basecode')), undef,
		"$saved_query\n$res" );
    return $res;
}

sub gen_error
{
    my $res = "\n" .
      $q->div({-class=>"errorbox", -style=>"margin-top:1em"}, "<p><b>Error:</b></p>" . join("<br />\n", @_));

    #DEBUG: Get a dump of the last SQL statement too
#     if( my $h = $DBI::lasth )
#     {
# 	$res .= $q->div({-class=>"errorbox", -style=>"margin-top:1em"},
# 			"Last SQL was:<pre>\n$h->{Statement}</pre>");
#     }

    $res;
}

#Now a set of subs that show the forms for the various actions
$FORMS{steal} = sub{

    my %params = @_;
    
    $q->h2("Steal codes from another user") .
    $q->p("To claim ownership of a block of codes from another user you must know the 
	   first code in the block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["New owner ", $q->textfield("newowner")] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form(); 
};

$FORMS{"split"} = sub{

    my %params = @_;

    $q->h2("Split an allocated block of codes in two") .
    $q->p("To split a block of codes into two blocks you you must know the
           first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.<br />
	   The code you split on will become the first code of the second block.  You can supply
	   a new comment for either or both blocks, or leave the boxes blank to keep the original
	   comments.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["Split at code ", $q->textfield("splitcode")] )),
	$q->Tr($q->td( ["New comment for block 1 ", $q->textfield({-size=>60},"newcomment1")] )),
	$q->Tr($q->td( ["New comment for block 2 ", $q->textfield({-size=>60},"newcomment2")] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{blockmodify} = sub{

    my %params = @_;

    $q->h2("Change the comment on a block of codes") .
    $q->p("You you must know the first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.<br />") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["New comment for block ", $q->textfield({-size=>60},"newcomment")] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{grow} = sub{

    my %params = @_;

    $q->h2("Expand a block of codes") .
    $q->p("You you must know the first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.<br />
	   The block will be extended as much as possible without overlapping adjoining blocks.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["Extend up ", $q->checkbox({-name => "extendup", -label => '', -checked => 1})] )),
	$q->Tr($q->td( ["Extend down ", $q->checkbox({-name => "extenddown", -label => '', -checked => 1})] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{shrink} = sub{

    my %params = @_;

    $q->h2("Shrink down a block of codes") .
    $q->p("You you must know the first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.<br />
	   The block will be shrunk as much as possible while retaining the used codes.  If there is
	   no data submitted then the block will be removed entirely.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["Lose high codes ", $q->checkbox({-name => "shrinkhigh", -label => '', -checked => 1})] )),
	$q->Tr($q->td( ["Lose low codes ", $q->checkbox({-name => "shrinklow", -label => '', -checked => 1})] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{convert} = sub{

    my %params = @_;

    $q->h2("Convert a block of codes") .
    $q->p("You you must know the first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet, assuming the code was not disposed of.<br />
	   Note that converting codes is generally a <b>bad</b> idea.  Using the 'force' option is a <b>really bad</b> idea
	   as it allows data to be lost!  Using the 'drop data' mode is <b>just plain wreckless</b> but if you
	   know what you are doing you can restore the data from spreadsheet.  Note that the 'drop data' option will
	   also undispose all the codes in the block.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$q->Tr($q->td( ["Convert to type ", $q->textfield("newtype")] )),
	$q->Tr($q->td( ["Force mode ", $q->checkbox({-name => "forcemode", -label => '', -checked => 0})] )),
	$q->Tr($q->td( ["Drop data ", $q->checkbox({-name => "dropmode", -label => '', -checked => 0})] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{usermodify} = sub{

    my %params = @_;

    $q->h2("Change user details") .
    $q->p("Give the username to modify and the new details.  
           If a field is left blank the existing value will be kept.<br />") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["User name ", $q->textfield("username")] )),
	$q->Tr($q->td( ["Full name ", $q->textfield("fullname")] )),
	$q->Tr($q->td( ["E-mail ", $q->textfield("email")] )),
	$q->Tr($q->td( ["Institute ", $q->textfield("institute")] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{undispose} = sub{

    my %params = @_;

    $q->h2("Undispose codes") .
    $q->p("Enter numbers of codes to undispose in the same format as for disposal (ie. you may use a colon to denote a
           continuous range).  <br />
	   As a sanity check the system will object if you try to undispose a code which was disposed
	   of more than 24 hours ago, unless you override it.  The ownership will not be checked, so use with caution!") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["Codes to undispose ", ""] )),
	$q->Tr($q->td( {-colspan => 2}, $q->textarea(-name=>'undisplist', -rows=>8, -columns=>40) )),
	$q->Tr($q->td( ["Maximum days to undo", $q->textfield(-size=>4, -name=>'undispmaxdays', -default=>1)] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{deallocate} = sub{

    my %params = @_;

    $q->h2("Deallocate codes") .
    $q->p("You you must know the first code in the original block.<br />
           You can find this out via the admin interface or the report interface or by looking at the
	   first line of the spreadsheet.<br />
	   The block will be deallocated only if no data was yet logged against any code.  
	   If there is any data submitted the deallocation will be aborted, but if
	   any of the unused codes were marked disposed then the block will be removed anyway and  
	   the disposal comments will be lost.<br />
	   ") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["First barcode in block ", $q->textfield("basecode")] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();

};

$FORMS{reindex} = sub{

    my %params = @_;

    $q->h2("Rebuild the link index") .
    $q->p("The link index table keeps track of which codes link to each other, allowing the query
	   interface to find items that derive from other items.  In normal operation the index should
	   be kept up-to-date by Handlebar as codes are added and updated, but you may choose to rebuild the whole
	   index from scratch if need be.") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class =>  "formtable"},
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] ))
    ) .
    $q->end_form();
};

$FORMS{export} = sub{

    my %params = @_;

    #If the action ran it will keep a copy of the types found to populate a dropdown
    #Otherwise the user needs to type the name in a text box
    our $_bc_types_found;

    my $typefield = $_bc_types_found ?
		    $q->popup_menu(-name=>'typename',-values=>$_bc_types_found):
		    $q->textfield('typename');

    $q->h2("Export type definition") .
    $q->p("Give the name of the type to be exported.<br />
           You can get a summary of available types via the admin interface or the report interface.<br />
	   SQL commands will be generated suitable for recreating this type definition in another
	   database instance.<br />
	   ") .
    $q->start_form() .
    $q->hidden(-name=>'action') .
    $q->table( {-class => "formtable"},
	$q->Tr($q->td( ["Name of type to export ", $typefield] )),
	$params{passprompt},
	$q->Tr($q->td( ["", "", $q->submit(-value=>"Go")] )) 
    ) .
    $q->end_form();
};

###======= END OF FORMS ====================================
###======= NOW THE ACTUAL ACTIONS ==========================

# Now the actual actions...
$ACTIONS{steal} = sub{

    my $basecode = $q->param('basecode') or die "No base code given\n";
    my $newowner = $q->param('newowner') or die "No new owner given\n";

    #Convert basecode and check it
    $basecode = bcdequote($basecode);
    $basecode == bcrangemembertobase($basecode) or die
			"The code " . bcquote($basecode) . " is not the base of any block\n";
			
    my( $oldowner, $typename, undef, undef, $fromcode, $tocode)
                    = bcgetinfofornumber($basecode);

    bcchkuser($newowner) or die "The username $newowner does not exist in the system\n";
    $oldowner ne $newowner or die "That block is already owned by $oldowner\n";

    #So we are transferring a valid block to a valid user.  Sounds good.
    my $sth = bcprepare("UPDATE barcode_allocation 
			 SET username = ?
			 WHERE fromcode = $basecode");
    $sth->execute($newowner);

    #Don't forget to commit
    bccommit();

    #And report
    my $codecount = $tocode - $fromcode + 1;
    "The $codecount codes of type " . bczapunderscores($typename) . " beginning from " . bcquote($basecode) . " 
     have been stolen from $oldowner and now belong to $newowner";
};

$ACTIONS{"split"} = sub{
 
    my $basecode = $q->param('basecode') or die "No base code given\n";
    my $splitcode = $q->param('splitcode') or die "No code given to split on\n";
    my $newcomment1 = $q->param('newcomment1');
    my $newcomment2 = $q->param('newcomment2');

    #Convert basecode and check it
    $basecode = bcdequote($basecode);
    $basecode == bcrangemembertobase($basecode) or die
			"The code " . bcquote($basecode) . " is not the base of any block\n";

    my( undef, undef, undef, $comments, $fromcode, $tocode) = bcgetinfofornumber($basecode);

    $splitcode = bcdequote($splitcode);

    #Now $splitcode will be the first code in the second block, so it must be greater than $fromcode
    #and <= $tocode
    ($splitcode > $fromcode && $splitcode <= $tocode) or die
			bcquote($splitcode) . " is not within the range (" . bcquote($fromcode) . "-" .
			bcquote($tocode) . "]";
    
    #OK, now I can check out the comments
    $newcomment1 ||= $comments;
    $newcomment2 ||= $comments;

    #Insert the second allocation by cloning the first
    my $sth;
    $sth = bcprepare("INSERT INTO barcode_allocation (username, typename, fromcode, tocode, comments)
		      SELECT username, typename, ?, tocode, ?
		      FROM barcode_allocation 
		      WHERE fromcode = ?");
    $sth->execute($splitcode, $newcomment2, $fromcode);

    #Modify the first allocation with the new range and comment
    #Note this will result in a new timestamp for the seconf block but the old timestamp for the first block
    $sth = bcprepare("UPDATE barcode_allocation SET
		      tocode = ?,
		      comments = ?
		      WHERE fromcode = ?");
    $sth->execute($splitcode - 1, $newcomment1, $fromcode);

    bccommit();

    "The block of " . ($tocode - $fromcode + 1) . " codes from " . bcquote($fromcode) . " to " . bcquote($tocode) . 
    " has been split into two blocks, with the first code in the second block being " . bcquote($splitcode) . ".";
};

$ACTIONS{usermodify} = sub{
    
    my $username = lc($q->param('username')) or die "No user name given\n";
    my $fullname = $q->param('fullname');
    my $email = $q->param('email');
    my $institute = $q->param('institute');

    bcchkuser($username) or die "The username $username does not exist in the system\n";

    ($fullname || $email || $institute) or die "Nothing to update\n";
    
    #For simplicity, update one at a time
    my $sth;
    if($fullname)
    {
	$sth = bcprepare("UPDATE barcode_user
			  SET realname = ?
			  WHERE username = ?");
	$sth->execute($fullname, $username);
    }
    if($email)
    {
	$sth = bcprepare("UPDATE barcode_user
			  SET email = ?
			  WHERE username = ?");
	$sth->execute($email, $username);
    }
    if($institute)
    {
	$sth = bcprepare("UPDATE barcode_user
			  SET institute = ?
			  WHERE username = ?");
	$sth->execute($institute, $username);
    }
    bccommit();

    "Details for $username have been updated:" .
    ($fullname ? "<br />Full name is now '$fullname'" : "" ) .
    ($email ? "<br />E-mail is now '$email'" : "" ) .
    ($institute ? "<br />Institute is now '$institute'" : "");
};

$ACTIONS{blockmodify} = sub{
    
    my $basecode = $q->param('basecode') or die "No base code given\n";
    my $newcomment = $q->param('newcomment') || '';

    #Convert basecode and check it
    $basecode = bcdequote($basecode);
    $basecode == bcrangemembertobase($basecode) or die
                        "The code " . bcquote($basecode) . " is not the base of any block\n";

    my( $oldowner, $typename, undef, $comments, $fromcode, $tocode)
                    = bcgetinfofornumber($basecode);

    #Shove in the new comment
    my $sth = bcprepare("UPDATE barcode_allocation
                         SET comments = ?
                         WHERE fromcode = $basecode");
    $sth->execute($newcomment);

    #Don't forget to commit
    bccommit();

    my $codecount = $tocode - $fromcode + 1;
    "The $codecount codes of type $typename beginning from " . bcquote($basecode) . 
    ($newcomment eq '' ? " have had the comment removed<br/>"
		      : " now have the comment '$newcomment'<br/>" ) .
    ($comments eq '' ? "There was no comment previously"
		    : "The previous comment was '$comments'");
};

$ACTIONS{convert} = sub{

    die "Not implemented";
    #This is going to be fiddly.  Basic method would be

    my $basecode = $q->param('basecode') or die "No base code given\n";
    my $newtype = $q->param('newtype') or die "No target type specified\n";
    my $forcemode = $q->param('forcemode') || 0;
    my $dropmode = $q->param('dropmode') || 0;
    
    #Validate newtype exists.
    #Get a list of barcodes for which data was logged
    #If there is no data or we are in dropmode
	#Remove all disposals for used codes, to enable re-uploading
	#(keep disposals for unused ones)
	#Scrub all data
    #Else
    #if forcemode
    #	grab a list of all the columns in the source table
    #	grab a list of all columns in the target table, with types
    #	create an insert statement with explicit type conversions for
    #	    all common columns (the explicit conversions permit string truncation etc)
    #	run it (there may be errors due to impossible conversions or constraint violations)
    #	remove from old table
    #else
    #	grab a list of columns in source and destination tables
    #	for any column in the source which is not in the destination, see if there
    #	    are any entries in the source codes where this column is not null, and
    #	    if so fail
    #	create an insert statement with no explicit casts, so that string truncation will
    #	    raise an error
    #	run it and see
    #	remove from old table
    #Update barcode_allocation to reflect the new type

};


#This is copy-and-pasted from request_barcodes.  Should be shared in barcodeUtil.
#Designed to be totally watertight
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
#             if(abs($2 - $1) > 10000) { die "Range $_ is larger than the maximum number of codes allowed
#                                             for disposal in one go.  Aborting.\n" };
            if($2 - $1 < 0) { push(@res, $2..$1) }
            else            { push(@res, $1..$2) }
        }
        else
        {
            #This catches something like 30:40:50
            die "Range $_ is not a valid range of codes.\n";
        }
    }

    return @res;
}

sub remove_disposals
{
    my ($codes_to_remove, $undispmaxdays) = @_;
     
    my $sth = bcprepare("DELETE FROM barcode_deletion WHERE barcode = ?");
    my $checksth;
    if($undispmaxdays)
    {
      $checksth = bcprepare("
	SELECT to_char(datestamp, 'dth Mon yyyy') FROM barcode_deletion WHERE barcode = ?
	AND extract('days' from (now() - datestamp) ) >= $undispmaxdays
	");
    }

    my $removals = 0;
    my $codecount = scalar(@$codes_to_remove);
    for(@$codes_to_remove)
    {
	if($undispmaxdays)
	{
	    $checksth->execute($_);
	    if( my ($outofdate) = $checksth->fetchrow_array() )
	    {
		die "The code $_ was disposed of on $outofdate, which is more than " .
		    "$undispmaxdays days ago.\n";
	    }
	}

	#With the Pg driver you always find out the number of affected rows
	$removals += $sth->execute($_);
    }

    $removals;
}

$ACTIONS{undispose} = sub{

    my $undisplist = $q->param('undisplist') or die "Nothing specified for undisposal\n";
    my $undispmaxdays = $q->param('undispmaxdays') || 1;
    
    #Run the input through the same routine used for disposal.
    my @codes = displist_normalise($undisplist) or die "No codes specified for undisposal\n";
    my $codecount = scalar(@codes);

    #Ensure this is an integer
    $undispmaxdays = int_nowarn($undispmaxdays) || 1;

    #Remove the buggers
    my $removals = remove_disposals(\@codes, $undispmaxdays);
    bccommit();

    $removals or die "None of the $codecount codes you asked to undispose were actually marked disposed\n";
    
    #report
    ($removals == $codecount) 
	? "All $codecount codes were successfully undisposed"
	: "You specified $codecount codes to undispose.  $removals codes were successfully undisposed, but
	   the remainder were not found in the disposals table.\n";
};

$ACTIONS{deallocate} = sub{

    my $basecode = $q->param('basecode') or die "No base code given\n";

    #Convert basecode and check it
    $basecode = bcdequote($basecode);
    $basecode == bcrangemembertobase($basecode) or die
                        "The code " . bcquote($basecode) . " is not the base of any block\n";

    my( $oldowner, $typename, undef, $comments, $fromcode, $tocode)
                    = bcgetinfofornumber($basecode);

    #Check that there is nothing in the data table
    my $datatable = bctypetotable($typename);

    my $sth = bcprepare("SELECT count(*) FROM $datatable WHERE
			 barcode >= ? AND barcode <= ?");
    $sth->execute($fromcode, $tocode);

    my ($datacount) = $sth->fetchrow_array();
    $datacount and die "Cannot deallocate this block, as data has been uploaded against $datacount barcodes.";

    #Remove any disposals
    my $disposal_count = remove_disposals([$fromcode..$tocode]);

    #And kill the entry in the allocation table
    $sth = bcprepare("DELETE FROM barcode_allocation WHERE fromcode = ?");
    $sth->execute($fromcode);

    bccommit();

    my $res = "Block of codes belonging to $oldowner successfully deallocated.";
    $res .= ($comments ? "<br />The comment on the block was: $comments."
                       : "<br />There was no comment set on this block." );
    $disposal_count and $res .= "<br />$disposal_count of these had entries in the disposal table.";

    $res;
};

$ACTIONS{reindex} = sub{

    #No parameters for this one.  The indexer code does support indexing only certain tables, but I can't
    #really see a good reason for that.
    
    require barcodeIndexer;
    import barcodeIndexer qw(rebuildindex);

    my $sth;
    #Lock the table just in case some parallel operation wants to update the
    #index.  This is possibly redundant as the big delete should lock out the
    #table for me.
    $sth = bcprepare("LOCK $barcodeIndexer::INDEX_TABLE IN EXCLUSIVE MODE");
    $sth->execute();

    #See how many entries there are in the barcode_link_index table
    #Some more fancy SQL coming up...
    my $selecta = "SELECT n, count(barcode_link_index.*) 
		   FROM $barcodeIndexer::INDEX_TABLE RIGHT OUTER JOIN
		   (SELECT 'null' AS n
		    UNION
		    SELECT 'notnull' AS n) AS foo
		   ON (n = 'null' AND external_id IS NULL)
		      OR (n != 'null' AND external_id IS NOT NULL)
		   GROUP BY n";
    $sth = bcprepare($selecta);
    $sth->execute();
    my %linkcount1 = map {@$_} @{$sth->fetchall_arrayref()};

    rebuildindex();
 
    $sth = bcprepare($selecta);
    $sth->execute();
    my %linkcount2 = map {@$_} @{$sth->fetchall_arrayref()};

    bccommit();

    "The index has been rebuilt.  Previously the index table had $linkcount1{null} entries" .
    ($linkcount1{notnull} ? ", as well as $linkcount1{notnull} entries relating to external codes." : ".") .
    "<br />There are now $linkcount2{null} entries in the table.";
};

$ACTIONS{export} = sub{
    
    #Snaffle the list of barcode types:
    our $_bc_types_found = [bczapunderscores( @{bcgetbctypes({showhidden=>1})} )];
    
    my $typename = $q->param('typename') or die "No type specified for export\n";
    $typename = bczapspaces($typename);

    my $res = dump_sql($typename);

    #Now format to HTML.  Needs to be <pre>
    $res = $q->escapeHTML($res);

	#And make a link to download
	my $linky = "admin_barcodes.cgi?action=export_dl;typename=" . CGI::escape($typename);

    qq{<pre>$res</pre><p><a href="$linky">Download SQL</p>};
};

sub do_export_dl
{
	#Verify the type as above
    our $_bc_types_found = [bczapunderscores( @{bcgetbctypes({showhidden=>1})} )];
    
    my $typename = $q->param('typename') or die "No type specified for export\n";
    $typename = bczapspaces($typename);

    my $res = dump_sql($typename);
	
	#Appropriate header
    bcheader(-type=>'text/plain',
             -content_disposition=>"attachment;filename=$typename.sql") .
	$res;
}

#    steal split grow shrink convert usermodify blockmodify undispose deallocate
main;
