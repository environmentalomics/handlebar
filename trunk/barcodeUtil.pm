#!perl
use strict; use warnings;

# CVS $Revision: 1.18 $ committed on $Date: 2006/09/22 13:21:18 $ by $Author: tbooth $

#This module collects all the utility routines used by the
#barcode database interface.  It depends on barcode_db.
#It could be done in an OOP style, but since there is only one
#connection per invocation of the script this seems overkill.  Maybe
#if I try to use this with mod_perl I will come unstuck?  
# -- Yes, totally!  See the notes in request_barcodes.cgi

# Note to future developers:  I apologise for the messyness of this code and for request_barcodes.cgi.
# Reasons for this include:
#  Most of this module was ripped out of request_barcodes.cgi in order to make the functions available 
# for use in the other CGI scripts.  This module was never designed - it was extracted.
#  I have eschewed OOP and explicit importing of functions due to laziness - the hack to export all 
# functions beginning bc* is a convenient shortcut.
#  I was supposed to split lots of the database code down into barcodeDB but I didn't.  This will need to
# be done if you ever want to make the thing work on MySQL (but why on Earth would you want that??)
#  There isn't a logging module either, logging was plumbed in after the code was finished and lives here.
#  I'm jumping through hoops to please CGI::Carp (which is clever but suffers from vagiaries in Perl's
# die/warn mechanism) and Config::Simple (which is just a crock!).
#  I'm tring to generate dynamic HTML without stepping on the callers toes or generating junk. Also I'm 
# trying to send warnings to the right place and give the user as much info as possible at all times - this
# leads to spaghetti.
#  I'm not using HTML templates.  These would make the code vastly more elegant but unfortunately no more
# comprehensible (or maybe it would be??) - see GenQuery for some hardcore template action.
# 
# On the plus side the import/export is fully modularised.  Ie. you should be able to write an import/export
# plugin for your favoured spreadsheet format without touching this code.  The workings of the TableIO are
# described in the POD embedded in TableIO::base.

package barcodeUtil;
require Exporter;
require barcodeDB;

#Other modules we use:
use Carp;
use Config::Simple;
use CGI qw(Vars http escapeHTML);
use DBI;
use Data::Dumper; #For teh debugging
use Fcntl qw(:DEFAULT :flock); #File locking
use IO::File;
use IO::String;
{ package IO::String; sub str{${shift()->string_ref }} }

#CGI stuff - use CGI::Carp only if called via a browser.
our ($q, $conf);
BEGIN { if($ENV{GATEWAY_INTERFACE}){
    
    #I previously used "if(http())" to test if the script was actually running under CGI but this
    #upsets the Vim Perl checker and maybe other things.

    require CGI::Carp; import CGI::Carp qw(fatalsToBrowser);

    #Linking to my mail address is great for debugging on our internal systems, but when external users are
    #running barcodebase do I really want all their bug reports which are probably out of
    #date?  Nope!
    
    my $carper = sub{
	    my $err = shift(); 

	    #Have to tread very carefully to avoid messing up Config::Simple.  Try to
	    #find the correct e-mail address in the config file.
	    our $conf;
	    unless($conf)
	    {
		    eval{
		    Config::Simple->import_from('barcodes.conf', $conf);
		    };
		    $conf = {} if $@;
	    }
	    my $contact = $conf->{PAGE_MAINTAINER} || "the website maintainer";
	    
	    print "
	    <h1>Software error:</h1>
	    Sorry.  There was an error processing your request.  There is either a bug in the 
	    code running on the website or something has been misconfigured.  Please help
	    to debug the system by reporting the problem.  Save this entire page and mail it to 
	    $contact.
	    <p>Time: ", scalar(gmtime), " UTC.</p>
	    <p>Error message: <pre>", $err, "</pre></p>
	    <p>Param dump: <pre>",
	    escapeHTML(Dumper({$q->Vars()})), "</pre>";
    };		    
    CGI::Carp::set_message($carper);
} };
#This is not a general purpose module - export everything!
our @ISA = qw(Exporter);
our @EXPORT = qw(int_nowarn nsort);

#Also import all functions in the namespace beginning 'bc...'
{ no strict;
  bless local $x = \$x;
  push @EXPORT, grep {/^bc/ && $x->can($_)} keys %{__PACKAGE__.::}
};

#Eek - a big nasty list of globals :-(
our( $MAX_CODES, $CODE_BLOCK_SIZE, $MIN_BAR_CODE, $PREFIX_LENGTH, $POSTFIX_LENGTH, $SPACER_CHAR,
	 $STYLESHEET, $CUSTOM_FOOTER, $HELP_LINK, $ENABLE_PRINTING, $ENABLE_ADMIN, $ENABLE_REPORTS,
	 $STRICT_USER_NAMES, $LOG_DIRECTORY, $DATA_SCHEMA, $divs_open,
	);

sub _setup
{
	return if $q;  #Only setup once!  Oh dear, this is messy :-(
	$q = new CGI;
	$conf = {};

	Config::Simple->import_from('barcodes.conf', $conf);
	#Compensate for broken Config::Simple
	for(keys %$conf)
	{
		undef($conf->{$_}) if (ref($conf->{$_}) eq 'ARRAY' && @{$conf->{$_}} == 0 );
	}

	$MAX_CODES = $conf->{MAX_CODES} || 1000;
	$CODE_BLOCK_SIZE = $conf->{CODE_BLOCK_SIZE} || 100;
	$MIN_BAR_CODE = bcdequote($conf->{MIN_BAR_CODE});
	$PREFIX_LENGTH = $conf->{PREFIX_LENGTH} || 0;
	$POSTFIX_LENGTH = $conf->{POSTFIX_LENGTH} || 0;
	$SPACER_CHAR = $conf->{SPACER_CHAR} || '';
	$STYLESHEET = $conf->{STYLESHEET} || 'bcstyle.css';
	$CUSTOM_FOOTER = $conf->{CUSTOM_FOOTER} || 'barcodes.footer.html';
	$HELP_LINK = $conf->{HELP_LINK} || '../../handlebar/user_guide.pdf';
	$ENABLE_PRINTING = $conf->{ENABLE_PRINTING} ? 1 : 0;
	$ENABLE_ADMIN = $conf->{ENABLE_ADMIN} ? 1 : 0;
	$ENABLE_REPORTS = $conf->{ENABLE_REPORTS} ? 1 : 0;
	$STRICT_USER_NAMES = $conf->{STRICT_USER_NAMES} ? 1 : 0;
	$LOG_DIRECTORY = $conf->{LOG_DIRECTORY};

	$divs_open = 0;
}

#Rather than attempt to prise out all the database interaction into
#yet another layer, for now this module will mostly access the database handle directly.
my ($dbobj, $dbh);

sub connectnow
{
    #Check we have some config, make the connection, and maybe override some config.
    my $newconf = shift;
    my $actualconf = $newconf || $conf;

    %$actualconf or die "Problem reading config file. Configuration is empty!\n";

    eval{
		$dbobj = barcodeDB->new($actualconf);
		$dbh = $dbobj->get_handle();
		$DATA_SCHEMA = $dbobj->get_data_schema();
    };
    #Now if the connection fails, die immediately if under CGI
    $@ and http() ? die $@ : warn $@;

    #This cruft is so that I can determine the connection settings at the
    #last minute when running the master query.
    if($newconf)
    {
	$PREFIX_LENGTH = $newconf->{PREFIX_LENGTH} || 0;
	$POSTFIX_LENGTH = $newconf->{POSTFIX_LENGTH} || 0;
	$SPACER_CHAR = $newconf->{SPACER_CHAR} || '';
	$STYLESHEET = $newconf->{STYLESHEET} || 'bcstyle.css';
    }
}

#The logging is a bit fiddly.  If no log dir is set then this will just return.
sub bclogevent
{
    #Event type can be alloc/disp/upload/error/admin
    my $event_type = shift;
    my $user_name = shift;
    my $base_code = shift; #optional
    my $file_extension = shift;
    my $data = shift;

    local $\;
    my $log_counter;
    if($LOG_DIRECTORY)
    { 
	my $seqfilename = "$LOG_DIRECTORY/sequence.number";
	#Get an event number from the sequence file and update it synchronously.
	#Thanks to the old Perl Cookbook for this one	
	#http://www.unix.org.ua/orelly/perl/cookbook/ch07_12.htm

	eval{
	    sysopen(FH, $seqfilename, O_RDWR|O_CREAT)
						or die "can't open log sequence $seqfilename: $!";
	    flock(FH, LOCK_EX)                  or die "can't write-lock log sequence: $!";
	    # Now we have acquired the lock, it's safe for I/O
	    $log_counter = (<FH> || 1);         # Default start is 1
	    seek(FH, 0, 0)                      or die "can't rewind log sequence: $!";
	    truncate(FH, 0)                     or die "can't truncate log sequence: $!";
	    print FH $log_counter + 1, 
		     "\nThe prefix for the next log file is stored in here",
		     "\nso you probably DON'T want to mess with this file.\n"
						or die "can't write log sequence: $!";
	    close(FH)                           or die "can't close log sequence: $!";
	};
	if($@)
	{
	    #Should this be fatal, as we can't log the change?
	    # die $@;

	    #Or should it just be a warning?
	    warn $@;
	    $log_counter = 0;
	}
    }

    if($log_counter)
    {
	my $logfile = "$LOG_DIRECTORY/";
	$logfile .= sprintf('%06d_%s_%s' , $log_counter, $event_type, $user_name);
	$logfile .= "_$base_code" if $base_code;
	$logfile .= ($file_extension ? ".$file_extension" : ".log");

	eval{
	    #Flags needed to create file, fail if it existed already and to write to it.
	    my $lfh = new IO::File $logfile, O_CREAT | O_EXCL | O_WRONLY or die "Cannot create file $logfile";
	
	    #If data is a string just write it.
	    if(ref($data) eq '')
	    {
		print $lfh $data;
		$data =~ /\n$/ or print $lfh "\n";
	    }
	    elsif(ref($data) eq 'Fh')
	    {
		#I hope all file handles give a ref of 'Fh'!
		seek($data, 0, 0) or die "Cannot seek in uploaded file.  Will not try to copy.";

		print $lfh $_ for <$data>;
	
		seek($data, 0, 0) or die "Cannot seek in uploaded file after reading.  Oh no!";
	    }
	    else
	    {
		print $lfh Dumper($data), "\n";
	    }
	};
	if($@)
	{
	    #Oh well...
	    warn $@;
	}
    }
}

sub import
{
    _setup();

    #Connect to DB if -connect argument given.
    my @args;
    for(@_)
    {
	/-connect/ ? connectnow() : push(@args, $_);
    }

    barcodeUtil->export_to_level(1, @args);
}

sub bcgetconfig {$conf}

sub bcgetqueryobj {$q}

sub bcgetdbobj {$dbobj}
    
#Due to my spaghetti-coding, I am ending up with
#missing headers and doubled headers.  I want a CGI header that
#will only ever print once.
our ($headerprinted, $starthtmlprinted) = (0,0);
sub bcheader
{
    #This turns out to be a bad idea, since DBD::Pg unicode support is flaky
    #and Excel doesn't use unicode anyway, at least not the standard version.
#     if($q->http('HTTP_ACCEPT_CHARSET') =~ /utf-8/)
#     {
# 	$q->charset("utf-8");
# 	binmode STDOUT, ":utf8";
#     }
    $headerprinted++ ?
    "\n"	     :
    $q->header(@_)   ;
}

sub bcstarthtml
{
my $ios = new IO::String;
    my $title = shift;
    unless($starthtmlprinted++)
    {
	print $ios
	$q->start_html( -style=>{'src'=>$STYLESHEET},
			-title=>$title,
			@_);
    }

$ios->str;
}

sub bcfooter
{
my $ios = new IO::String;

    #Close the main section div
    #No, do this somewhere more sensible!
#     print $ios $q->end_div();

    #If there is a custom footer print it.
    if(my $cf = new IO::File($CUSTOM_FOOTER, "r"))
    {
	print $ios (<$cf>);
    }

$ios->str;
}

#Passthrough for database
sub bccommit { $dbh->commit() }
sub bcrollback { $dbh->rollback() }
sub bcdisconnect { $dbobj->disconnect() }

#The real utility functions
sub bch1
{
my $ios = new IO::String;
    #The top part of the page is division "topbanner", so immediately after
    #printing the h1, close the topbanner div tag and start the mainsection div
    print $ios  '<div id="logodiv_top"><!--Container for logo - see CSS--></div>',
		$q->h1(@_);

    if($divs_open)
    {
	$divs_open--;
	print $ios $q->end_div(), $q->start_div({-id=>"mainsection"});
    }
$ios->str;
}

sub bcnavbanner
{
my $ios = new IO::String;
    #Show the various components.  Mark out the current page.
    my @sections = (
	    { href=>"request_barcodes.cgi", label=>"Main request interface page" },
	    { href=>"query_barcodes.cgi",   label=>"Quick query" },
    );

    #If GenQuery is running then we want to link straight to the report interface.
    if($ENABLE_REPORTS)
    {
	push @sections, { href=>"report_barcodes.cgi", label=>"Report maker" };
    }

    #Printing is offered by default but can be suppressed
    if($ENABLE_PRINTING)
    {
		push @sections, { href=>"print_barcodes.cgi",   label=>"Barcode printing" };
    }

    #Admin is offered by default but can be suppressed
    if($ENABLE_ADMIN)
    {
        push @sections, { href=>"admin_barcodes.cgi",   label=>"Extra admin" };
    }
	
    if($HELP_LINK)
    {
		push @sections, { href=>$HELP_LINK, label=>"Help", target=>"_blank" };
    }

    #See what page we are on, only if there were no params:
    unless($q->param())
    {
		my $url = $q->url(-relative=>1);
		
		for(@sections)
		{
			$_->{current} = 1 if ($_->{href} eq $url);
		}
    }
    
    my $nbsp = sub{
		(my $foo = "@_") =~ s/ /&nbsp;/g;
		$foo;
    };

    unless($divs_open)
    {	
		$divs_open++;
		print $ios $q->start_div({-id=>"topbanner"});
    }
    print $ios	
      $q->div( {-class=>'navbanner_outer'},
		  $q->span( {-id=>'navbanner', -class=>'navbanner'},
	  "Main menu:", join("  ", map { $q->span(
					    $_->{current} ?
					      { -class=>"navbanner_current" } : (),
					    $q->a({-href=>$_->{href}, -target=>$_->{target}}, 
						   $nbsp->($_->{label})))
					 } @sections
			    )
			  )
      );
$ios->str;
}

#Loads column_info into an array and a hash for a named table
#This only makes any sense in terms of what the next function requires.
sub bcgetcolumninfo
{
    my $atype = shift();
    my $descidx = shift();
    my $descdata = shift();
    my $row;

    #Grab the column names and data types from the database
    my $sth = $dbh->column_info( undef, $DATA_SCHEMA, $atype, undef);
    while($row = $sth->fetchrow_hashref())
    {
	$descidx->{$row->{COLUMN_NAME}} = @$descdata;
	push (@$descdata, $row);

	#Remove any undefined remarks to allow defaults to be added.
	delete $row->{REMARKS} unless defined $row->{REMARKS};
    }
}

#Return a type description in HTML, given a type name
sub bcdescribetype
{
    my $ios = new IO::String;
    my $atype = shift();
    my($typenotes, $sth, @row, $row, $fieldname);
    my(%descidx, @descdata); #This will be a pseudo-pseudohash

    bcgetcolumninfo($atype, \%descidx, \@descdata);

    #Sanity check that something came back - the caller should make sure the name is valid.
    @descdata or confess "bcdescribetype was unable to get any info about '$atype'";

    eval{
	#See if we can read a table comment for this table
	$sth = $dbh->table_info( undef, $DATA_SCHEMA, $atype, undef);
	$typenotes = $sth->fetchrow_hashref()->$_->{REMARKS}; 
	$sth->finish();
    };
   
    eval{
    #Grab the description notes from the database and add them in.
    #The description table overrides any remarks found above.
    $sth = $dbh->prepare_cached("
	    SELECT columnname, notes 
	    FROM barcode_description
	    WHERE typename = ?
	    ");
    $sth->execute($atype);
    
    while(@row = $sth->fetchrow_array)
    {
	$fieldname = $row[0];
	if($fieldname eq '-')
	{
	    $typenotes = $row[1];
	    next;
	}
	#Ignore orphan comments, flags etc.
	next unless defined $descidx{$fieldname};

	$descdata[$descidx{$fieldname}]->{REMARKS} = $row[1];
    }

    #Now I am also supporting default remarks, where the typename in the
    #barcode_description table is set to '-'.  These will only apply if there
    #is no remark at all set, not even a null one.
    $sth->execute('-');
    while(@row = $sth->fetchrow_array)
    {
	$fieldname = $row[0];
	
	next unless defined $descidx{$fieldname};
	next if exists $descdata[$descidx{$fieldname}]->{REMARKS};

	$descdata[$descidx{$fieldname}]->{REMARKS} = $row[1];
    }
    
    #If the eval fails just ignore it - maybe there is no description table.
    #Maybe the notes have been added using the native COMMENT ON TABLE
    #facility, which we are already picking up.
    };

    #See if this is a hidden table.
    my $hidden = bcgetflagsforfield($atype)->{hide};

    #Print the description lines.
    print $ios $q->h4(bczapunderscores($atype)),
	       $hidden ? $q->p(
	         "This type has been disabled - you may not allocate new codes of this type"
	       ) : "",
	       $typenotes ? $q->p($q->escapeHTML($typenotes)) : "",
	       "\n",
	       $q->p("Fields in <b>bold</b> are mandatory.");

    #Begin the table
    print $ios $q->start_table({-class=>"neat1"}),
	       $q->Tr( $q->th( ["Field", "DataType", "Length", "Remarks"]) );

    my $printrowsub = sub
    {
		my $row = shift;
		my $flags = shift;
		#So $row now references a hash of properties for
		#the table column in question
		
		#First skip the 'barcode' field
		return if $row->{COLUMN_NAME} eq 'barcode';

		#Remove unsightly underscores
		$row->{COLUMN_NAME} = bczapunderscores($row->{COLUMN_NAME});

		if($flags->{bc})
		{
			#This is a barcode, then
			$row->{TYPE_NAME} = 'barcode';
			$row->{COLUMN_SIZE} = '';
		}
		else
		{
			#Make the types more legible
			($row->{TYPE_NAME}, $row->{COLUMN_SIZE}) =
			bcsqltypedemystify($row->{TYPE_NAME}, $row->{COLUMN_SIZE});
		}

		#Anyone for Curry today?
		my $formatter = sub{@_};
		if( $flags->{noexport} )
		{
			my $of = $formatter;
	# 	    $formatter = sub{ $q->span({-style => 'text-decoration: line-through;'}, 
	# 				       $of->(@_)) };
			#noeport is there to be used for timestamps where the database will auto-fill
			#the field.  Strikethrough looks wrong for that.
			$formatter = sub{ my $x = join('',$of->(@_)); $x eq '' ? '' : "($x)" };
		}
		if(! $row->{NULLABLE})
		{
			my $of = $formatter;
			$formatter = sub{ $q->b($of->(@_)) };
		}
		if( $flags->{bc})
		{
			my $of = $formatter;
			$formatter = sub{ $q->span({-style => 'color: navy;'}, 
						   $of->(@_)) };
		}

		print $ios $q->Tr(
			   $q->td( [ map $formatter->($_),
					($row->{COLUMN_NAME},
					 $row->{TYPE_NAME},
					 $row->{COLUMN_SIZE},
					 $q->escapeHTML($row->{REMARKS})) ] ));	
    };

    #Now the final complication is that I am supporting the 'demote'
    #flag, which causes the field to go to the end of the list.  Maybe
    #there should be a 'promote' flag too? (argh - NO! - too coplicated)
    my @demoted;
    for $row (@descdata)
    {
	my $flags = bcgetflagsforfield($atype, $row->{COLUMN_NAME});
	if($flags->{demote})
	{
	    push @demoted, [$row, $flags];
	}
	else
	{
	    &$printrowsub($row, $flags);
	}
    }
    
    #Sweep up the demoted stuff
    for $row (@demoted)
    {
	&$printrowsub(@$row);
    }
													  
    print $ios $q->end_table;

$ios->str;
}

sub bcgetflagsforfield
{
    #The original problem here was how to mark out a field which contained a barcode.
    #Such fields should show up as a hyperlink in the query interface.
    #General solution was to make use of the description table, where we set flags by
    #shoving a comma-separated list of keywords in the notes field and setting the
    #columnname to "*columnname"
    
    #Hacky?  Maybe, but it should be easy to maintain
    #We should be able to assume that all data in this table is non-tainted, as only
    #the administrator can set up type definitions, so minimal paranoia is needed.

    my $typename = shift; #Compulsory
    my $column = shift || '-'; #We can set flags on the entire table
    my %flags = ();

    $column = "*$column";
    my $sth = $dbh->prepare_cached("
		    SELECT notes FROM barcode_description
		    WHERE typename = ?
		    AND columnname = ?");

    $sth->execute($typename, $column);
    if( my $res = $sth->fetchrow_arrayref() )
    {
	#Yes there is an entry in the table, but is there anything in it?
	my $flagstring = $res->[0];

	if($flagstring)
	{
	    map {$flags{$_}++} split(',', $flagstring);
	}
    }
    
    #Originally the specific flags overrode the defaults, but thinking about it
    #it seemed more logical that the two are additive.  Would I ever need to cancel out
    #a default flag?
    #Pull in deafults...
    $sth->execute('-', $column);

    if( my $res2 = $sth->fetchrow_arrayref() )
    {
	my $flagstring2 = $res2->[0];

	if($flagstring2)
	{
	    map {$flags{$_}++} split(',', $flagstring2);
	}
    }

    #Needed because I don't fetch past the end of the resultset.
    $sth->finish();
    
    return \%flags;
}

sub bcgetalluserdata
{
    $dbh->selectall_hashref(
	"SELECT username, realname, institute, email FROM barcode_user",
	"username" );
}

sub bcuserreport
{
my $ios = new IO::String;

    #Summarise the users in the system
    my $userdata = bcgetalluserdata(); 

    #The original version did not spot deletions
#    my $sth = $dbh->prepare("
#	    SELECT SUM(tocode - fromcode + 1) AS codecount
#	    FROM barcode_allocation WHERE username = ?
#	    ");

    #But the new version may well be too slow when there are lots of deletions
    my $sth = $dbh->prepare("
	SELECT SUM(a1.tocode - a1.fromcode + 1 - coalesce(a2.count,0)) AS codes FROM
	barcode_allocation a1 LEFT OUTER JOIN
	(SELECT fromcode, tocode, count(*) FROM barcode_allocation a
	INNER JOIN barcode_deletion d ON
	(d.barcode >= a.fromcode AND d.barcode <= a.tocode)
	GROUP BY fromcode, tocode) a2 ON a1.fromcode = a2.fromcode
	WHERE username = ?
	");

    if(keys (%$userdata))
    {
	print $ios 
		   $q->start_table({-class=>"neat1"}),
		   $q->Tr( $q->th( ["Username", "Full Name", "E-Mail", "Institute", "Barcodes Owned"]) );
	for(sort keys(%$userdata))
	{
	    #Find out how many codes this user owns
	    my ($codetally) = $dbh->selectrow_array($sth, undef, $_);
	
	    my $row = $userdata->{$_};
	    print $ios $q->Tr(
		       $q->td( [ $q->escapeHTML($row->{username}),
				 $q->escapeHTML($row->{realname}),
				 $q->escapeHTML($row->{email}),
				 $q->escapeHTML($row->{institute}),
				 $codetally         ] )
		       );
	}
	print $ios $q->end_table;
    }
    else
    {
	print $ios  $q->p($q->b("No users have been registered on the system."));
    }

$ios->str;
}

sub bcchkuser
{
    my $suspect_user = shift() or return 0;

    #Does the username occur in the hash?
    bcgetalluserdata()->{$suspect_user};
}

sub bcchkbctype
{
    my $suspect_type = shift();

    #Could do a binary search or hash, but for length<50 it is a waste of space.
    for(@{bcgetbctypes()}){ return 1 if $_ eq $suspect_type };
    0;
}


sub bctypereport
{
my $ios = new IO::String;

    #Now there may be a typelist, but it is tainted so we shall
    #avoid feeding it directly to the database.
    my $typelist_wanted = shift();

#     print $ios $q->start_ul;
    my $typesindb = bcgetbctypes();

    if($typelist_wanted)
    {
	#Take note, I want a copy of the list, not just the reference,
	#since the copy gets modified.
	my @typelist = @$typelist_wanted;
	for my $atype (@typelist)
	{
	    #Knock out spaces
	    $atype =~ tr/ /_/;
	 
	    #Is that a real type?
	    if(grep {$_ eq $atype} @$typesindb)
	    {
		print $ios $q->a({-name=>$atype}, ""), bcdescribetype($atype);
	    }
	    else
	    {
		print $ios $q->a({-name=>$atype}, ""), 
			   $q->h4('The type "' . bczapunderscores($atype) . 
				  '" was not found in the database.');
	    }
	}
    }
    else
    {
	#Print everything
	for(@$typesindb)
	{
	    print $ios $q->a({-name=>$_}, ""), bcdescribetype($_);
	}
    }
#     print $ios $q->end_ul;

$ios->str;
}

sub int_nowarn
{
    #int("foo") returns zero, but also emits a warning.
    #so here is a wrapper function to suppress the warning.
    no warnings;
    int(shift);
}

#The standard numerical sort routine
sub nsort
{
    sort {$a <=> $b} @_;
}

#Given the base code of a range, get the range
sub bccodetorange
{
    $dbh->selectrow_array("
	SELECT tocode, username, typename FROM barcode_allocation
	WHERE fromcode = ?", undef, shift());
}

#Strictly, all the database stuff should be done here or in the
#DB module, but the rearrangement just gets too much.
#Therefore, permit a prepare on the underlying DB.
sub bcprepare
{
    eval{
	$dbh->prepare(@_);
    } 
    || confess($@);
}

{
my @barcode_allocation_cache;
sub bcgetinfofornumber
{
    my $bcode = shift();

    #Given a number, determine owner/type/date/comments or die with an error
    #We could do an SQL query but we want some more speed than that.
    #Cache the last barcode allocation table result

    if(@barcode_allocation_cache &&
       $barcode_allocation_cache[4] <= $bcode &&
       $barcode_allocation_cache[5] >= $bcode)
    {
	return @barcode_allocation_cache;
    }
    
    @barcode_allocation_cache = $dbh->selectrow_array("
	    SELECT username, typename, datestamp, comments, fromcode, tocode
	    FROM barcode_allocation
	    WHERE fromcode <= $bcode AND tocode >= $bcode
	    ") or die "The barcode $bcode is invalid - it has not been allocated.\n";
    return @barcode_allocation_cache;
}
}

sub bcexpungerecords
{
    my $bcodes = shift();
    my $type = shift();
    my $table = "$DATA_SCHEMA.$type";
    #Erase all the given codes and return a hashref of what was removed
    my %deletedhash;

    #How many numbers do you think I can use in one IN statement
    my $numbersperchunk = 100;
    for(my $nn = 0; $nn < @$bcodes; $nn += $numbersperchunk)
    {
	my $max = $nn + $numbersperchunk;
	$max = @$bcodes if @$bcodes < $max;
	$max--;
	my $bcstring = join(',', @$bcodes[$nn..$max]);

	$deletedhash{$_}++
	for( @{$dbh->selectcol_arrayref("
	    SELECT barcode FROM $table 
	    WHERE barcode IN ($bcstring)
	    ")} );	
	
	$dbh->do("
	    DELETE FROM $table 
	    WHERE barcode IN ($bcstring)
	    ");
    }
    return \%deletedhash;	
}

sub bcrangemembertobase
{
    #Given a barcode find the base of the range or else return undef
    my $bcode = shift(); #Assume this has gone through int() already
    my $user = shift();  #Assume this passes chkuser or is undef

    $dbh->selectrow_array("
		SELECT fromcode FROM barcode_allocation
		WHERE fromcode <= $bcode AND tocode >= $bcode " .
		($user ? "AND username = " . $dbh->quote($user) : "")
	  );
}

sub bcallocate
{
    #Allocate a block of codes and return the base index
    my ($quantity, $username, $bctype, $comments) = @_;
    $comments ||= "";

    #We have a potential race condition in that two invocations of this script
    #could both run at once, get the same value for the $lastbase and
    #thus attempt to allocate conflicting ranges.  The PostgreSQL specific
    #fix is to grab a write-lock before we do anything else
	#(note - exclusive mode really is a write lock, despite the name):
    $dbh->do("LOCK barcode_allocation IN EXCLUSIVE MODE");
    
    #Determine next starting base
    my ($lastbase) = $dbh->selectrow_array("
	    SELECT max(tocode) FROM barcode_allocation
	    ");

    #There will be no zero barcode, so the very first allocation
    #returns CODEBLOCKSIZE, or MINBARCODE if set.
    if(! $lastbase){ 
		$lastbase = $MIN_BAR_CODE || $CODE_BLOCK_SIZE; 
    }
    else
    {
		#Remember that the last returned value is already allocated.
		$lastbase++;

		if($lastbase % $CODE_BLOCK_SIZE)
		{
			#Round-up needed
			$lastbase += $CODE_BLOCK_SIZE - ($lastbase % $CODE_BLOCK_SIZE);
		}
    }

    #Log the allocation in the database
    $dbh->do("INSERT INTO barcode_allocation
              (username, typename, fromcode, tocode, comments)
	      values
	      (?,?,?,?,?)", undef,
	      $username, $bctype, $lastbase, $lastbase + $quantity - 1, $comments);
    $dbh->commit();

    #Log the allocation
    bclogevent( 'alloc', $username, $lastbase, undef,
		"Allocated $quantity codes of type $bctype to $username beginning with $lastbase."
	      );
    
    return $lastbase;
}

sub bcdodisposal
{
    #This should return three lists: $displist, $nodatalist, $alreadydisplist
    #$dispcount will not include the stuff in $nodatacount
    
    my $codes = shift;
    my $comments = shift || undef;
    my $sth = $dbh->prepare("INSERT INTO barcode_deletion (barcode, comments) VALUES (?, ?)"); 

    my (@displist, @nodatalist, @alreadydisplist);
    
    for my $acode (@$codes)
    {
	if(bcdisposedateandcomments($acode))
	{
	    push @alreadydisplist, $acode;
	}
	else
	{
	    $sth->execute($acode, $comments);

	    my $typename = [bcgetinfofornumber($acode)]->[1];
	    my $qtable = bctypetotable($typename);

	    #We have a valid allocated bc, but it may or may not have
	    #info associated with it. 
	    my $csth = $dbh->prepare_cached("SELECT barcode FROM $qtable WHERE barcode = ?");
	    $csth->execute($acode);

	    if($csth->fetchrow_array())
	    {
		push @displist, $acode;
	    }
	    else
	    {
		push @nodatalist, $acode;
	    }
	}
    }

    return(\@displist, \@nodatalist, \@alreadydisplist);
}

#Convert a type name to a tablename.
sub bctypetotable
{
    "$DATA_SCHEMA." . shift();
}

sub bcgetbctypes
{
    #A DBI constant.  This is redundant as so many features of the system assume
    #use of PG, plus it should be in barcodeDB, but it is nonetheless the correct way to do things.
    my $SQL_IDENTIFIER_QUOTE_CHAR = 29;

    #Support filtering of types with the hide flag set
    my $showhidden = 1;
    if(my $opts = shift)
    {
	$showhidden = $opts->{showhidden} if exists($opts->{showhidden});
    }

    #Summarise the tables in data schema
    my @types = $dbh->tables( undef, $DATA_SCHEMA, undef, undef);

    #We can chop quoting and sort the list.
    #Also we only want the name after the last period.
    if(my $qc = $dbh->get_info($SQL_IDENTIFIER_QUOTE_CHAR))
    {
	map((s/$qc//o, s/$DATA_SCHEMA\.//o), @types);
    }

    if(!$showhidden)
    {
	@types = grep {!bcgetflagsforfield($_)->{hide}} @types;
    }
    
    [sort(@types)];
};

sub bcgetusers
{
    #return a reference to an array of all user names.
    $dbh->selectcol_arrayref(
            "SELECT username FROM barcode_user ORDER BY username"
	  );
}

sub bcgethighestbc
{
    #Find out the highest barcode allocated.
    #made this separate from do_allocate so as not to tangle up the 
    #locking issues.
    my ($lastbase) = $dbh->selectrow_array("
                SELECT max(tocode) FROM barcode_allocation
		");
    $lastbase;	    
}

sub bcdisposedateandcomments
{
    #If this was disposed, grab date and comments.
    my $code = shift;

    my $csth = $dbh->prepare_cached("
	SELECT datestamp, comments FROM barcode_deletion
	WHERE barcode = ?" );

    $dbh->selectrow_array($csth, undef, $code);
}

#When table or column name is shown on screen, underscores
#are converted to spaces.  It seems to make sense to have a
#function rather than an explicit conversion every time.
sub bczapunderscores
{
    map {tr/_/ /} (my @foo = @_);
    wantarray ? @foo : $foo[0];
}

sub bczapspaces
{
    map {tr/ /_/} (my @foo = @_);
    wantarray ? @foo : $foo[0];
}

#A barcode is viewed in the form 00-000000
#As controlled by PREFIX_LENGTH, POSTFIX_LENGTH and SPACER_CHAR
{
my $spftemplate;
sub bcquote
{
    $spftemplate ||= "%0" . ($PREFIX_LENGTH + $POSTFIX_LENGTH) . "d";

    #Assume we do have a number, time for sprintf
    substr((my $number = sprintf($spftemplate, shift)),
	   -$POSTFIX_LENGTH, 0, $SPACER_CHAR);
    $number;
}
}

sub bcquote_js
{
    #Emits a version of the bcquote function is JavaScript.
    #Tasty...
    qq|
	function bcquote(number){
	    var bc = '' + number;
	    var wantedlen = $PREFIX_LENGTH + $POSTFIX_LENGTH;
	    while(bc.length<wantedlen) bc = '0' + bc;
	    bc = bc.substring(0, bc.length - $POSTFIX_LENGTH)
	         + '$SPACER_CHAR'
		 + bc.substring(bc.length - $POSTFIX_LENGTH);
	    return bc;
	}
    |;
}

sub bczapspaces_js
{
    #Needed when we want to generate a link into the types popup and we
    #need to turn a typename into a label with underscores in.
    qq|
	function zapspaces(stringtozap){
	    var str = stringtozap;
	    var str2 = "";
	    while(str2 != str)
	    {
	      str2 = str;
	      str = str.replace(/ /,"_");
	    }
	    return str;
	}
    |;
}

sub bcdequote
{
    #This is easy - remove all but digits
    my $code = shift || return undef;
    $code =~ s/\D//g;
    #But I also need to remove leading zeros, or my hash-based detection of
    #matches between input and database screws up!
    $code =~ s/^0+//;
    $code;
}

#Rather than keep explaining what the SQL types mean, convert
#them on the sly to something a biologist is more likely to understand.
sub bcsqltypedemystify
{
    my $typename = shift;
    my $typelength = shift;

    #Ignore size of dates:
    $typelength = '' if ($typename eq 'date' || $typename =~ /timestamp/);

    #Text fields are unlimited size
    $typelength = "unlimited" if ($typename eq 'text');

    #"Character varying" means nothing to the user
    $typename = "text" if ($typename eq 'character varying');

    #And neither does "double precision"
    $typename = "real" if ($typename eq 'double precision');

    $typename = "timestamp" if $typename =~ /timestamp/;

    ($typename, $typelength);
}

#Get a summary of codes allocate dby a user.  For the sake of simplicity in the
#calling script, I'm making this work in an OO-type way.
sub bcgetblocksforuser
{
    #No checking of the user - if the user is invalid you just get nothing back
    my $username = shift;

    my $self = {active_blocks=>[], disp_blocks=>[], blocks=>{}};
    bless $self, "barcodeUtil::BlockList";

    #Hash will hold : blocks maps base to description
    #		      disp_blocks, active_blocks
    #		      defaultbase is highest active base
    
    my $sth = bcprepare("
                SELECT fromcode, tocode, typename, datestamp, comments
                FROM barcode_allocation WHERE username = ?
		ORDER BY fromcode ASC");
    $sth->execute($username);
    my $codesforuser = $sth->fetchall_arrayref();

    #Now we need to be able to count disposals
    $sth = bcprepare("
                SELECT count(*) FROM barcode_deletion WHERE
                barcode >= ? and barcode <= ?");
    for(@$codesforuser)
    {
        my @row = @$_;
	#Note - no need to escape HTML in a form.
	my $label = bcquote($row[0]) . " to " . bcquote($row[1]) .
		    ": " . bczapunderscores($row[2]) . " : allocated on $row[3]" .
                    ($row[4] ? " : $row[4]" : "");
	$self->{blocks}->{$row[0]} = $label;

        #Now just check that this block was not completely disposed
        $sth->execute($row[0], $row[1]);
        my ($count) = $sth->fetchrow_array();
        if($count == $row[1] - $row[0] + 1)
	{
	    #Yes it was.
	    push @{$self->{disp_blocks}}, $row[0];
	}
	else
	{
	    push @{$self->{active_blocks}}, $row[0];
	    #Default if not supplied in $base is last from db:
	    $self->{defaultbase} = $row[0];
	}
    }
    $self;
}
 
{
package barcodeUtil::BlockList;

sub all_blocks
{
    #Returns a list of base codes for all owned blocks, in numerical order
    #In scalar context returns the size of the list.
    my $self = shift;
    if(wantarray)
    {
	return nsort(@{$self->{disp_blocks}}, @{$self->{active_blocks}});
    }
    else
    {
	return @{$self->{disp_blocks}} + @{$self->{active_blocks}}
    }
}

sub active_blocks
{
    #Returns same as all blocks but excluding any where all the codes have 
    #been disposed
    my $self = shift;
    if(wantarray)
    {
	return @{$self->{active_blocks}};
    }
    else
    {
	return scalar(@{$self->{active_blocks}})
    }
}

sub render_scrolling_list
{
    #Makes a scrolling list suitable for inclusion in an HTML form
    #Takes a hashref of additional arguments to be passed to CGI.pm when the
    #list is rendered.
    my $self = shift;
    my $params = shift || {};
    
    $q->scrolling_list( -name => "blocklist",
			-values=> [reverse(@{$self->{active_blocks}})],
			-labels=> $self->{blocks},
			-multiple=> 0,
			-size=> 10,
			%$params);
}

sub highest_active_base
{
    shift()->{defaultbase};
}

}
 
1;
