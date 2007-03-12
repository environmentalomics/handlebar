#!/usr/bin/perl
use strict; use warnings;

#All the standard CGI stuff...
use lib "..";
use barcodeUtil;
#use Mail::Mailer;
#No - that module is lame - use MIME::Lite instead!
use MIME::Lite;

our %CONFIG = %{bcgetconfig()};
our $MAILADDR = $CONFIG{MAILADDR};
our $SMTP_SERVER = $CONFIG{SMTP_SERVER};

my $q = bcgetqueryobj;

#User wil be prompted for name, e-mail address and comments
my $result = "";
my $title = "Submit a Handlebar type template";

#Has the user submitted the form?
for($q)
{
	$q->param('submit') or last;

	#Has the user admitted who they are?
	if(!$q->param('email'))
	{
		$result = gen_error("Please give a valid e-mail address.  This will be used only to contact you 
							 regarding this submission and will not be published, added to mailing
			                 lists or otherwise disseminated.");	
		last;
	}
	
	#Has the user attached a file?
	if(!$q->param('sqlfile'))
	{
		$result = gen_error("Error - No file was uploaded.");
		last;
	}

	#Mail it, then.
	if(mail_it_then($q->param('realname'), $q->param('email'), $q->param('comment'), $q->upload('sqlfile'), $q->param('sqlfile')))
	{
		$title = "You have submitted a Handlebar type template";
		$result = "Thanks - a message has been sent and your template will be uploaded to
		           the repository shortly.";
	}
	else
	{
		$result = gen_error("Sorry - there was an internal error and the submission failed.  If you wish,
							 you can simply send the template by e-mail to $MAILADDR.");
	}
}

#Print top stuff - TODO simulate the nav banner with links to the main site
print bcheader(), bcstarthtml($title), 
	  $q->div({-id=>"topbanner"}, bch1($title)), 
	  $q->start_div({-id=>"mainsection"}),
	  $result, "\n";

#Now the actual form for them to fill in:
print $q->h2("Submit a template as a .sql file."),
      $q->start_multipart_form(-name=>"impform", -method=>"POST"),
	  $q->p("
You can use this form to send a type description to the Handlebar project maintainers.
To export a file in the correct format use the export feature on the Extra Admin tab.
The files you submit will be e-mailed to $MAILADDR."
	  ),
	  $q->table( {-class=>"formtable"},
        $q->Tr($q->td( ["Your name ", $q->textfield(-size=>"36",-name=>"realname")] )), 
        $q->Tr($q->td( ["Your e-mail ", $q->textfield(-size=>"36",-name=>"email")] )), 
	    $q->Tr($q->td({-colspan=>2}, "
Any additional comments relating to the type definition?  This is in addition to the existing
comments recorded within the definition."
	    )),
        $q->Tr($q->td( ["Comments ", $q->textarea(-columns=>"36",-name=>"comment")] )), 
		$q->Tr($q->td( ["File to upload ", $q->filefield(-name=>"sqlfile")] )),
		$q->Tr($q->td( ["", $q->submit(-name=>"submit",-label=>"Submit")] )),
	  ),
	  bcfooter();

#DONE

sub mail_it_then
{
	my($realname, $email, $comment, $sqlfile, $sqlfilename) = @_;

	my $user = `whoami` || "www-data";
	my $host = `hostname -a` || "envgen.nox.ac.uk";

	my @mailargs;

    if($SMTP_SERVER) {
		MIME::Lite->send('smtp', $SMTP_SERVER, Timeout=>60);
	}
	my $msg = MIME::Lite->new(
			To => $MAILADDR,
            From => "$user@$host",
			Subject => "A barcode template submission from $realname",
			Type    => 'multipart/mixed',
	);

	$msg->attach( Type => "TEXT",
				  Data => join('', 
					  "Mail generated at ", scalar(localtime()), ".\n",
					  "From $realname ($email) on ", $q->http('remote_host'), ".\n",
					  "Filename is $sqlfilename.\n\n",
					  "BYE.\n" )
				);
	
	$msg->attach( Type     => 'text/plain',
				  Disposition => 'attachment',
				  Filename => ($sqlfilename =~ /([^\\\/]+$)/)[0],
				  FH => $sqlfile );

	$msg->send();
}

sub gen_error
{
	"\n" .
      $q->div({-class=>"errorbox", -style=>"margin-top:1em"}, "<p><b>Error:</b></p>" . join("<br />\n", @_));
}

