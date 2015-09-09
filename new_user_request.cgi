#!/usr/bin/perl 
use strict; use warnings;

# CVS $Revision: 1.5 $ committed on $Date: 2006/01/23 12:17:23 $ by $Author: tbooth $
 
use barcodeUtil;

our $q = bcgetqueryobj();
our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};

our $sname = $q->param('sname');
our $fname = $q->param('fname');
our $institute = $q->param('institute');
our $email = $q->param('email');
our $close_flag = $q->param('c'); $q->delete('c');

my $main = sub
{
    print bcheader();

    print bcstarthtml($PAGE_TITLE),
	  ( $close_flag ? $q->start_div({-id=>"topbanner"}) . $q->p(['<br/>']) : bcnavbanner() ),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "User creation"),
	  ;

    if($q->param())
    {
	#Submit to database
	barcodeUtil::connectnow();
	if(createnewuser())
	{
	    print $q->p("Thankyou, the username '$sname' has been created for " .
			$q->escapeHTML($fname) . ".");
	    if(!$close_flag)
	    {
		print $q->p($q->a({-href=>"request_barcodes.cgi"}, "Return to the admin interface"));
	    }
	    else
	    {
		print $q->p($q->a({-href=>"javascript: self.close()"}, "Close this window"));
	    }
	}
	else
	{
	    #Reshow form
	    print $q->hr();
	    showform();
	}
	bcdisconnect();
    }
    else
    {
	showform();
    }
};

sub showform
{
    print $q->h2("Enter details to register a new user"),
	  $q->start_form(-name=>"newuserform", -method=>"POST"),
	  $q->hidden( -name => "c", -default => $close_flag ),
	  $q->table( {-class => "formtable"},
	    $q->Tr($q->td( ["User name ", $q->textfield(-name=>"sname", -size=>20), "Up to 20 characters."] )),
	    $q->Tr($q->td( ["Full name ", $q->textfield(-name=>"fname", -size=>40), ""] )),
	    $q->Tr($q->td( ["E-mail  ", $q->textfield(-name=>"email", -size=>40), ""] )),
	    $q->Tr($q->td( ["Institute ", $q->textfield(-name=>"institute", -size=>40), "eg. CEH Oxford"] )),
	    $q->Tr($q->td( ["", "", $q->submit( -value=>"Register" )] )),
	  ),
	  $q->br,
 	  $q->end_form();

}

sub createnewuser
{
    #Check that all the input is valid:
    my @errors;

    if(length($sname) < 2 || length($sname) > 20)
    {
	push @errors, "You need to supply a username between 2 and 20 characters long.";
    }
    if($sname =~ /\W/) 
    {
	push @errors, "The username may only contain letters, numbers and underscores.";
    }

    #Force $sname to lower case
    $sname = lc($sname);

    #Check if the name is already in use
    my @userrow;
    {
	my $sth = bcprepare("
	    SELECT realname, institute
	    FROM barcode_user
	    WHERE username = ?");
	$sth->execute($sname);
	@userrow = $sth->fetchrow_array();
    }

    if(@userrow)
    {
	push @errors, "The username $sname is already allocated to $userrow[0] at $userrow[1].";
    }

    #Check that the real name is supplied
    if(length($fname) == 0)
    {
	push @errors, "Please supply your real name.";
    }

    #Check that the institute name is supplied
    if(length($institute) == 0)
    {
	push @errors, "Please supply your institute name or group affilliation.";
    }

    if(!@errors)
    {
	eval{
	    my $sth = bcprepare("
		INSERT INTO barcode_user (username, realname, institute, email)
		VALUES (?, ?, ?, ?)
		");
	    $sth->execute($sname, $fname, $institute, $email);
	    #Don't forget autocommit is off!
	    bccommit();
	};
	$@ and push @errors, "Internal error while updating database:", $@;
    }
    
    
    if(@errors)
    {
	my $error = join("<br />\n", @errors);
	print $q->p({-style=>"color:red; display:block; background-color:#DDD"},
	        "The following error occured:\n<br /><br />$error");
	return 0;
    }
    
    1;
}

&$main();
