#!/usr/bin/perl
#print_barcodes.perl - created Tue Oct 25 16:21:57 2005
use strict; use warnings;

# CVS $Revision: 1.14 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#There seem to be several ways to offer printing:
#1) Use the supplied software on Windows
#2) Use script installed on BL, maybe with a basic TK interface
#3) Print from a macro in OOo
#4) Print from the web by using this script to generate EPL files

# All should be possible, but as people expect the system to be web
# based I will start off offering printing from the web.
# This also allows me to modify the print format without sending out
# software updates.

# Note to non-NERC users of the software: This code is very specific to the Zebra
# EPL printers.  For use on other hardware you will almost certainly have to
# modify this code or take your own approach to printing.

use barcodeUtil('-connect');

use Data::Dumper;
use Mail::Mailer;
use IO::String;
{ package IO::String; no warnings;
  sub str{${shift()->string_ref }} }

our $q = bcgetqueryobj();
our %CONFIG = %{bcgetconfig()};
our $PAGE_TITLE = $CONFIG{PAGE_TITLE};
our $PAGE_DESC = $CONFIG{PAGE_DESC};
our $SMTP_SERVER = $CONFIG{SMTP_SERVER};

our $CENTRE = $CONFIG{PRINT_CENTRE};
our $MAILRECIPIENT = $CONFIG{PRINT_MAIL_RECIPIENT};
our $MAILADDR = $CONFIG{PRINT_MAIL_ADDRESS};

#Top of label
#On a large label you can have a 36 character message at the top,
#which gives room for a custom message
#On the small, just 18 will fit so we just put the web reference
our $topmessage = $CONFIG{PRINT_TOPMESSAGE} || "BarcodeBase";
our $topmessagemaxlen = 36;

our $WIKIHARDWAREURL = "http://darwin.nerc-oxford.ac.uk/pgp-wiki/index.php/" .
		       "Barcode_user_guide#Setting_up_and_Using_the_Barcode_Hardware";

our %printers = (
    epl2824=> "Local Zebra TLP2824",
    mailout=> "Request printing from $CENTRE",
);

our %labelsize = (
    '25x10'=>"25x10mm suitable for individual Eppendorfs",
    '47x13'=>"47x13mm standard size",
);

#>> End of configuration
	
my $username = $q->param("username");
my $fromcode = bcdequote($q->param("fromcode"));
my $tocode = bcdequote($q->param("tocode"));
my $dest = $q->param("dest");
my $size = $q->param("size");

my $reqprint = $q->param("reqprint");
my $getepl = $q->param("getepl");
my $mailnebc = $q->param("mailnebc");

my $lastinfo;

#Set auto-newline so the HTML source is legible
$\ = "\n";

#Possible things we may need to do.
#1)Show the main request form
#2)Process form info and show next bit
#2a)Confirm request for code mailing
#2b)Offer download of EPL file and link to instrux
#3)Generate the actual EPL
#4)Generate a mail to the NEBC

sub main
{
    #If this is a file download request, go straight to that - no HTML
    #will be outputten
    if($getepl)
    {
	#Case 3
	return makeepl();	
    }

    print bcheader();

    print bcstarthtml("$PAGE_TITLE - Barcode Printing"),
	  bcnavbanner(),
	  bch1(($PAGE_DESC ? "$PAGE_DESC - " : "") . "Print or request barcode labels"),
#  	  $q->b({-style=>"color:red"},
#  		"This part of the page is still in development.  It is not yet functional!"),
		;

    if($mailnebc)
    {
	#Case 4
	eval{
	    validateinput();
	    print mailnebc();

	    $q->delete("fromcode");
	    $q->delete("tocode");
	};
    }
    elsif($reqprint)
    {
	#Case 2
	eval{
	    #We are onto the second stage, so either a prompt for
	    #more details or the download link for the EPL
	    validateinput(); #Will die on error.
	    
	    if(!$dest)
	    {
		die "Please select a printer to use.\n";
	    }
	    elsif($dest eq "mailout")
	    {
		#Case 2a
		print mailoutform(),
		      $q->end_div(), bcfooter();
	    }
	    elsif($dest eq "epl2824")
	    {
	        #Case 2b
		print makeepllink(),
		      $q->end_div(), bcfooter();
	    }
	    else
	    {
		die "Internal error: invalid dest $dest\n";
	    }
	}
	#Don't print the form if that worked.
	and return;
    }

    if(my $error = $@)
    {
	#Presumably a validation error.
	$error =~ s/\n/<br \/>\n/g;
	print $q->p({-class=>"errorbox"},
                "The following error occured:\n<br /><br />$error");
    }
    
    #Case 1 or an error
    print reqform(),
          $q->end_div(),bcfooter();
};

sub validateinput
{
    #Validate $fromcode, $tocode.  Check they are all in the same block.
    #Set $user appropriately
    $fromcode and $tocode ||= $fromcode
	    or die "Please give a range of codes to be printed.\n";
    
    my @info = bcgetinfofornumber($fromcode);
    
    my $rangebase = $info[4];

    @info = bcgetinfofornumber($tocode);
		
    $rangebase == $info[4] 
	    or die "Codes ", bcquote($fromcode), " and ", 
		   bcquote($tocode), " are not part of the same allocation block.\n";
    
    
    $username = $info[0];

    #Fix params
    $q->param(username => $username);
    $q->param(fromcode => bcquote($fromcode));
    $q->param(tocode => bcquote($tocode));
    
    #Son't worry about size and dest; these will be dealt with elsewhere
    
    #Save the @info so we can peek at it later
    $lastinfo = \@info; 
}

sub mailoutform
{
my $ios = new IO::String;

    #Grab the registered name from the DB
    my $userdata = bcgetalluserdata()->{$username};
    my $dbrealname = $userdata->{realname};
    my $dbaddress = $userdata->{institute};
    my $dbemail = $userdata->{email};
    my $bw = 38;

    print $ios
	  $q->h2("Request printed barcodes by mail"),
	  $q->p("You have opted to contact $MAILRECIPIENT to request printed barcode labels.
		 This form will generate the request e-mail for you, and forward copies to both
		 <b>$MAILADDR</b> and the address you supply."),
	  $q->p("Please fill in all relevant details and hit <b>Submit</b>."),
	  $q->start_form({-name=>"mailoutform", -method=>"POST"}),
	  $q->hidden("dest"),
	  $q->table( {-class => "formtable"},
	      $q->Tr($q->td( ["Range ", "From: " . $q->textfield({-name=>"fromcode",
								  -size=>12,
								  -id=>"fromcode"}) .
					"To: " .   $q->textfield({-name=>"tocode", 
								  -size=>12,
								  -id=>"tocode"})] )),
	      $q->Tr($q->td( ["Label size ", $q->textfield({-name=>"sizetext",
							    -default=>$labelsize{$size},
							    -size=>$bw})])),
	      $q->Tr($q->td( ["Your full name ", $q->textfield({-name=>"realname",
								-default=>$dbrealname,
							        -size=>$bw})])),
	      $q->Tr($q->td( ["Your e-mail ", $q->textfield({-name=>"email",
							     -default=>$dbemail,
							     -size=>$bw})])),
	      $q->Tr($q->td( ["Mailing address ", $q->textarea({-rows=>6, 
								-columns=>$bw,
								-default=>$dbaddress,
								-name=>"mailingaddress"})])),
	      $q->Tr($q->td( ["Telephone ", $q->textfield({-name=>"telephone",
							   -size=>$bw})])),
	      $q->Tr($q->td( ["Head of Lab ", $q->textfield({-name=>"headoflab",
							     -size=>$bw})])),
	      $q->Tr($q->td( {-align=>"right"},
			     ["", $q->submit( -name=>"mailnebc", -label=>"Submit")] )),
	  ),
	  $q->end_form,
	  ;

$ios->str();
}

sub makeepllink
{
my $ios = new IO::String;

    #Fix params
    $q->param(getepl=>1);
    $q->delete("username");
    $q->delete("reqprint");
    $q->delete("blocklist");

    my $qfromcode = bcquote($fromcode);
    my $qtocode = bcquote($tocode);
    my $count = $tocode - $fromcode + 1;

    my $url = $q->url(-relative=>1, -query=>1);
    
    print $ios
	  $q->p("You opted to print out <b>$count</b> barcodes from <b>$qfromcode</b> to 
		 <b>$qtocode</b>.
		 An EPL file will be generated with the printer commands in it.  If you
		 have already set up your printer on your machine then just click the link 
		 below, choose \"Open with\" and select the application 
		 /usr/local/bin/zebraprint on Linux or zebraprint.bat on Windows.  
		 See <a href='$WIKIHARDWAREURL'>the Wiki page</a>
		 for instructions on setting up and troubleshooting the printers.
	  "),
	  $q->p("You have chosen to print labels of size <b>$labelsize{$size}</b>.  Please ensure 
		 that labels of this size are loaded into the printer.  If you have changed the 
		 labels in the printer then you may need to recalibrate the unit to the new label size.  
		 Again, see the Wiki page for instructions."),
	  $q->p($q->a({-href=>$url}, "Download EPL file"));

$ios->str();
}

sub mailnebc
{
#This routine should die on error - it will be trapped
my $ios = new IO::String;

    my $url = $q->url();
    my $count = $tocode - $fromcode + 1;
    
    my @mailargs;
    if($SMTP_SERVER)
    {
	@mailargs = ('smtp', Server => $SMTP_SERVER);
    }

    #At this point the codes should be validated and the username should
    #be correct.  Just need to check the E-Mail

    my $mailingaddress = $q->param("mailingaddress");
    my $telephone = $q->param("telephone");
    my $headoflab = $q->param("headoflab");
    my $realname = $q->param("realname") || "Anonymous";
    my $email = $q->param("email");
    my $sizetext = $q->param("sizetext");

    $email or die "Please supply your e-mail address.\n";

    #Format the mailing address because I can
    $mailingaddress =~ s/\n/\n   /gs;
    
    #Generate a mail to the helpdesk with details in it
    my $mailtext = 
"This mail was generated by the barcode request form at $url
    
 Please print out and mail me $count barcodes.
 Starting from: " . bcquote($fromcode) . "
 Up to:         " . bcquote($tocode) . "
 Owned by user: $username
 On label size: $sizetext
 
 Send to:
   $realname
   $mailingaddress

 Telephone  : $telephone
 Head of Lab: $headoflab

 Thanks,

 $realname
 ";
    #send the thing!
    my $mailer;
    $mailer = Mail::Mailer->new(@mailargs);
    $mailer->open({ To => $MAILADDR,
		    From => $email,
		    Subject => "Request for $count barcodes from $realname" });
    print $mailer $mailtext;
    $mailer->close();
    
    #and a copy to the requestor.
    $mailer = Mail::Mailer->new(@mailargs);
    $mailer->open({ To => $email,
		    From => $MAILADDR,
		    Subject => "FWD: Request for $count barcodes from $realname" });
    print $mailer "This is a copy of the e-mail you sent to $CENTRE.\n",
		  $mailtext;
    $mailer->close();
    
    #Then return a report in HTML, or an error report.    
    print $ios
	  $q->h2("Mail was sent to $MAILRECIPIENT"),
	  $q->pre("To: $MAILADDR\n\n$mailtext"),
	  $q->p("A copy was also forwarded to you at $email.");
    
$ios->str();
}

#Convenience conversion of \n to <br />\n
sub nl2br
{
    s/\n/<br \/>\n/g for @_;
    join("<br \/>\n", @_);
}

sub reqform
{
my $ios = new IO::String;
    #This is the main request form

    #When a user name is given, a list of codes comes up and you can
    #click one to auto-fill the from and to boxes
    my $userlist;
    if($username)
    {
	my $blocksforuser = bcgetblocksforuser($username);

	if($blocksforuser->active_blocks())
	{
	    $userlist = $blocksforuser->render_scrolling_list({
			      -onChange=> "javascript:setfromto(this[this.selectedIndex].text)"
			      }),
	}
	else
	{
	    $userlist = $q->escapeHTML("No active barcode blocks owned by user $username.");
	}
    }

    #The JavaScript fragment.  Now I need to get both codes in the range
    #so I'm fishing it out of the label.
    my $jssetfromto = qq|
	<script type="text/javascript">
	function setfromto(barcode_range){
	    var firstbit = barcode_range.split(": ")[0];
	    var newfrom = firstbit.split(" to ")[0];
	    var newto = firstbit.split(" to ")[1];
	    
	    document.getElementById("fromcode").value = newfrom;
	    document.getElementById("tocode").value = newto;
	}
	</script>
    |;

    print $ios
	  $q->start_form(-name=>"reqform", -method=>"POST"),
	  $q->h2("What do you want to print?"),
	  $q->p("This form will help you to print barcodes on your local printer, or
	  to request a batch of barcodes to be printed by $CENTRE and mailed out.
	  In either case, fill in the details below and click <b>Next</b>. Note
	  that at present you can only print codes from one allocation block at a time.
	  <br /><br />
	  Also, please try to use the larger labels if possible, as these are cheaper and will
	  also scan more reliably."),
	  $q->table( {-class => "formtable"},
	      $q->Tr($q->td( ["Printer ", $q->scrolling_list(
					    -name=> "dest",
					    -values=> ["epl2824", "mailout"],
					    -multiple=> 0,
					    -size=> 2,
					    -labels=> \%printers)			
			     ] )),
	      $q->Tr($q->td( ["Label size ", $q->scrolling_list(
					    -name=> "size",
					    -values=> ["25x10", "47x13"],
					    -multiple=> 0,
					    -size=> 2,
					    -labels=> \%labelsize,
					    -default=> "47x13")
			    ] )),				    
	      $q->Tr($q->td( ["Range ", "From: " . $q->textfield({-name=>"fromcode",
								  -size=>12,
								  -id=>"fromcode"}) .
					" To: " .  $q->textfield({-name=>"tocode",
								  -size=>12,
								  -id=>"tocode"})] )),
	      $q->Tr($q->td( {-align=>"right"},
			     ["", $q->submit( -name=>"reqprint", -label=>"Next")] )),
	      $q->Tr($q->td({-colspan=>"2"}, "<i>or else enter your user name to see a list of your codes</i>")),
	      $q->Tr($q->td( ["Username ", $q->textfield("username") . 
					   $q->submit(-name=>"list", -label=>"List")] )),
	      $q->Tr($q->td({-colspan=>"2"}, $userlist)),
	  ),
	  $q->end_form,
	  $jssetfromto;
$ios->str();
}

sub get_printable_column
{
    my ($itemtype, $fromcode, $tocode) = @_;

    #Either return the names of all printable columns in order or return
    #a hash of the actual printable data for the first column.

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
    my (@demoted, @undemoted, @printable);
    for(@headings)
    {
	my $flags = bcgetflagsforfield($itemtype, $_);
	if($flags->{print})
	{
	    $flags->{demote} ? push(@demoted, $_) : push(@undemoted, $_);
	}
    }
    @printable = ( @undemoted, @demoted );

    #Right, if no codes were specified we are done.
    if(!$fromcode)
    {
	return @printable;
    }

    #In most cases nothing to print.
    @printable or return undef;

    #Else assume the codes are sensible and get the data for printing
    #Note that the quoting in the following is not robust or protable, but never mind.
    my $sth2 = bcprepare(qq{
	    SELECT barcode, "$printable[0]" FROM
	    } . bctypetotable($itemtype) . qq{
	    WHERE barcode >= $fromcode AND barcode <= $tocode
	    });
    $sth2->execute();

    my %printvalues;
    while( my ($key, $val) = $sth2->fetchrow_array() )
    {
	$printvalues{$key} = $val if defined $val;
    }
    \%printvalues;
}

sub makeepl
{
    #Turn off auto linefeeds for this bit, and abolish fractions
    local $\ = undef;
    use bytes;
    use integer;

    #Revalidate in case of internal errors, or someone playing
    #silly beggars with the URL.
    validateinput();
    my $codecount = $tocode - $fromcode + 1;

    #Used to define the code layout here but now done in bcquote
    # ...snip

    my @cmds;

    if($size eq "25x10")
    {
	my $labelwidth = 25;
	my $labelheight = 10;
	my $dotspermm = 8;

	my $ro = 12;
	my $to = 0;
	my $bto = $to + 12;
	my $bro = 16;

	#Set the settings
	push @cmds, 'US1',     #Error reports on
		    'D13',     #Force darker printing - seems everyone needs it.
	            'q' . ($labelwidth * $dotspermm),
	            ;

	for($fromcode..$tocode)
	{
	 #In this case, just pad out the code to 8 chars
	 #This is hard-coded due to label size
	 my $number = sprintf("%08d", $_);

	 push @cmds, 'N',       #Begin label description

		     #The label (xoff,yoff,rot,font,hmul,vmul,N/R)
		     qq{A$ro,$to,0,1,1,1,N,"$topmessage"},

		     #The code (xoff,yoff,rot,type,nwidth,wwidth,height,B/N)
		     qq{B$bro,$bto,0,2,2,4,30,B,"$number"},
		     ;

	 push @cmds, 'P1';
	}
    }
    elsif($size eq "47x13")
    {
# 	die "I haven't finished programming this bit yet!\n";
	
	my $labelwidth = 47; #45mm allowing for margin
	my $labelheight = 13;
	my $dotspermm = 8;

	my $ro = 2 * $dotspermm;
 	my $to = 0; # (1 * $dotspermm) / 2;
	my $bto = $to + 16;
	my $bro = $ro + 16;
	my $gto = $bto + 4;
	my $gro = ($labelwidth - 6) * $dotspermm;

	my $etmaxlen = 12; #Room for how much extra text with the print flag?
	my $etro = $bro + (20 * $dotspermm);
	my $etto = $bto + (6 * $dotspermm) + 8;

	my $topmessagel = "$topmessage ";

	#Load the picture (eg. NERC logo) if possible
	my $gfx;
	eval{
	    local $/;
	    open my $fh, "labellogo40.pcx" or die;
	    $gfx = <$fh>;
	    close $fh;

	    push @cmds, 'GK"gfx1"',
	                'GM"gfx1"' . length($gfx),
			$gfx;
	};

	#Insert the type into the top message - or should that
	#be the username, or the date?
	my $topmessager = substr($lastinfo->[1], 0, 
				 $topmessagemaxlen - length($topmessagel) - 1);

	my $pad = $topmessagemaxlen - length($topmessagel) - length($topmessager);

	my $topmessage_all = $topmessagel . (' ' x $pad) . $topmessager;

	push @cmds, 'US1',     #Error reports on
		    'D13',     #Force darker printing - seems everyone needs it.
	            'q' . ($labelwidth * $dotspermm)
		    ;

	#I now support an optional printable field via the 'print' flag, which hints this
	#script to add the text to the label.
	#Get all values for the printable field into a hash
	my $printable_fields = get_printable_column($lastinfo->[1], $fromcode, $tocode);

	for($fromcode..$tocode)
	{
	     #Format the code with prefix and postfix
	     my $thiscode = $_;
	     my $quotedcode = bcquote($thiscode);
	     
	     push @cmds, 'N',       #Begin label description
			 #The label (xoff,yoff,rot,font,hmul,vmul,N/R)
			 qq{A$ro,$to,0,1,1,1,N,"$topmessage_all"},
			 #The code (xoff,yoff,rot,type,nwidth,wwidth,height,B/N)
			 qq{B$bro,$bto,0,1,2,6,50,B,"$quotedcode"};

	     if($gfx){
		push @cmds, qq{GG$gro,$gto,"gfx1"};
	     }

	     #The extra text
	     my $extratext;
	     if($printable_fields && ($extratext = $printable_fields->{$thiscode}))
	     {
		$extratext = substr($extratext, 0, $etmaxlen);

		push @cmds, qq{A$etro,$etto,0,3,1,1,R,"$extratext"};
	     }

	     push @cmds, 'P1';
	}
    }
    else
    {
	die "Internal error: bad size specification $size\n";
    }

    #Output commands as file
    print eplheader($codecount);
    print "$_\n" for @cmds;
}

sub eplheader
{
    #Print header for EPL file
    my $codecount = shift;
    bcheader(-type=>"application/x-epl",
             -content_disposition=>"attachment;filename=make${codecount}labels.epl");
}

main();
bcdisconnect();
