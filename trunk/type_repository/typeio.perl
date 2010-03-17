#!/usr/bin/perl
#type_repository/dumptypes.perl - created Sat Feb 17 18:12:37 2007
#renamed as typeio.perl on 8/3/10, now supporting saving and loading
 
use strict; 
use warnings;
use Data::Dumper;
use Getopt::Std;

# Iterate over all types in the database, and dump them out into specified dir.

my $usage = "  
  typeio.perl [options] -DD <targetdir>
  typeio.perl [options] [-k] -L <template.sql>
	options: -DD(ump)             = dump all templates
		 -D <type>[,type],... = dump only named types
		 -f(force)            = overwrite existing files when dumping
		 -h(idden)            = include hidden types
		 -S <type>, -H <type> = dump only SQL/HTML to STDOUT
		 -L <file>            = load SQL file into DB
		 -k                   = always keep old table definition
		 -H <file>            = convert SQL to HTML (requires DB connection)
		 -F <backupname>      = flush backup copies of template

 For Dump operations the login credentials from barcodes.conf will be used.
 For Load operations the default user name will be used (setenv \$PGUSER to override),
 and psql may prompt for a password.
";

#Add flag to include/exclude hidden types.
#Need optarg to do that properly
our ($opt_k, $opt_f, $opt_h, $opt_S, $opt_H, $opt_L, $opt_D, $opt_F);
getopts('kfhD:S:H:L:F:');

use lib ".."; #Hack
use barcodeUtil;
use barcodeTypeExporter;

my $mode = '';
my $types_filter = undef;
my $template_file = undef;
my $force = $opt_f;
my $PSQL = $ENV{PSQL} || 'psql';
if($opt_D)
{
    $mode = 'dump';
    if($opt_D && $opt_D ne 'D')
    {
	$types_filter = [split /,/, $opt_D];
    }
}
if($opt_S)
{
    !$mode or die "Usage: $usage";
    $mode = 'sqlout';
    $types_filter = [split /,/, $opt_S];
}
if($opt_H)
{
    !$mode or die "Usage: $usage";
    $mode = 'htmlout';

    #Heuristics - anything with an odd char [^a-zA-Z_,] must be a filename, and
    #anything else is a database table or list threreof.  If you want to convert a file called
    #foo_sql then load './foo_sql' or rename it to foo.sql
    if($opt_H =~ /[^a-zA-Z_,]/)
    {
	$template_file = $opt_H;
	$mode = 'htmlout_file';
    }
    else
    {
	$types_filter = [split /,/, $opt_H];
    }
}
if($opt_L)
{
    !$mode or die "Usage: $usage";
    $mode = 'load';
    $template_file = $opt_L;
}
if($opt_F)
{
    !$mode or die "Usage: $usage";
    $mode = 'flush';
    $types_filter = [split /,/, $opt_F];
}

$mode or die "Usage: $usage";

our %SUBS;
#First deal with dump mode
$SUBS{dump} = sub {
    my $target_dir = shift(@_) or die "Usage: $usage";
    if(! -d $target_dir)
    {
	if(!$force)
	{
	    ask("Directory $target_dir does not exist.  Create it?") or exit 0;
	}
	mkdir $target_dir or die "Could not make directory $target_dir";
    }

    barcodeUtil::connectnow();

    #get types
    #sort list (no need - already sorted)
    my @alltypes = @{bcgetbctypes()};

    #Find types by filter - intersection with all types
    if($types_filter)
    {
	for my $t (@$types_filter)
	{
	    grep {$_ eq $t} @alltypes or die "Unknown type $t.\n";
	}
	@alltypes = @$types_filter;

    } else {
	#Find hidden/non-hidden
	unless($opt_h)
	{
	    @alltypes = grep {!bcgetflagsforfield($_)->{hide}} @alltypes;
	}
    }

    #for each
    for my $atype (@alltypes)
    {
	#check .sql
	#check .desc
	for my $targetfile ( "$target_dir/$atype.sql",  "$target_dir/$atype.html" )
	{
	    if( -e $targetfile )
	    {
		if($force)
		{
		    unlink($targetfile) or die "unlink error on $targetfile";
		}
		else
		{
		    die "Will not overwrite existing file $targetfile.\n";
		}
	    }
	}

	my $outfh;
	#dump .sql
	open $outfh, ">$target_dir/$atype.sql" or die "!";
	print $outfh dump_sql($atype);
	close $outfh;

	#dump .desc
	open $outfh, ">$target_dir/$atype.html" or die "!!";
	print $outfh dump_desc($atype);
	close $outfh;
	
	#report dumped type
	print "Exported SQL and description for $atype.\n";
    }
    #report nn types dumped to dir
    print "DONE - Total of ". scalar(@alltypes) ." tables exported.\n";
}; #end dump mode

#This one is easy
$SUBS{sqlout} = sub{
    
    barcodeUtil::connectnow();

    #get types
    #sort list (no need - already sorted)
    my @alltypes = @{bcgetbctypes()};

    #I'd expect there to be only one, but you can have more.
    for my $type(@$types_filter)
    {
	#Check this is real
	grep {$_ eq $type} @alltypes or die "Unknown type $type.\n";
    
	#print "Dumping SQL for $type\n";
	print dump_sql($type);
    }
};

$SUBS{htmlout} = sub{

    #The easy version, virtually identical to above.
    barcodeUtil::connectnow();

    #get types
    #sort list (no need - already sorted)
    my @alltypes = @{bcgetbctypes()};

    #I'd expect there to be only one, but you can have more.
    for my $type(@$types_filter)
    {
	#Check this is real
	grep {$_ eq $type} @alltypes or die "Unknown type $type.\n";

	print dump_desc($type);
    }
};

$SUBS{htmlout_file} = sub{

    #The hard version.
    
    # In fact, it's so hard I'm not going to do it.  Maybe later.
    # When and if I do put this in, how do I avoid cut-and-paste?  Because if I
    # can't then I may as well just process the SQL directly.

    die "Sorry, direct conversion of type SQL to HTML is not yet implemented\n";

    #Connect to DB as usual, and check file is readable.

    -r $template_file or die "Cannot open $template_file for reading";

    #connect with default params
    barcodeUtil::connectnow();

    #load into temporary table
    #create temporary barcode_description and load descriptions
    #export to stdout
    #drop table
    
};

$SUBS{load} = sub{

    #Load a file - see design notes in README
    #Allow loading of a whole directory of files.
    my @files_to_load;
    if(-d $template_file)
    {
	@files_to_load = grep {/\.sql$/i} glob("$template_file/*");
    }
    else
    {
	@files_to_load = ($template_file, @_);
    }
    @files_to_load or die "Nothing to do!\n";

    #I need to connect to extract the connection parameters, and I'll
    #use the connection to see if there is any existing data for a type.
    barcodeUtil::connectnow();
    my $conn_params = bcgetdbobj()->grab_connection_params();
    my $dbh =  bcgetdbobj()->get_handle();
    $dbh->{PrintError} = $dbh->{PrintWarn} = 0;

    { local $ENV{PGHOST} = $conn_params->{dbhost} if $conn_params->{dbhost};
      local $ENV{PGPORT} = $conn_params->{dbport} if $conn_params->{dbport};
      local $ENV{PGDATABASE} = $conn_params->{dbname};

      my $search_path = "\"$conn_params->{dbschema}\"";
      $search_path .= ", \"$conn_params->{sysschema}\"" if $conn_params->{sysschema};
      $search_path .= ", pg_catalog";
      my $user_account =  $conn_params->{dbuser}; #Needed to grant permissions

        #PGUSER set by user, PGPASSWORD may be prompted for
	my @allcommands;
	for my $afile (@files_to_load)
	{
	    my $keep = $opt_k;
	    my $table_exists = 1;
	    my $existing_rows = 0;

	    #Load file into memory
	    my @commands = slurp($afile);

	    #Extract $typetable, $oldbackupname.  Make new $backupname.
	    my($typetable, $fulltypetable, $typename, $oldbackupname, $backupname);
	    for(@commands) { /^-- Barcode type (\w+)/ and ($typetable = $1, last) };
	    for(@commands) { /^CREATE TABLE "(\w+)" AS SELECT \*/ and ($oldbackupname = $1, last) }; 

	    unless($typetable && $oldbackupname)
	    {
		if(grep {/^</} @commands)
		{
		    die "$afile does not appear to be a valid exported template in SQL format.\n",
		        "It may be an HTML representation, which is for viewing only and cannot be loaded by this script.\n";
		}
		else
		{
		    die "$afile does not appear to be a valid exported template in SQL format.\n",
			"The file should not be hand-edited at all, including the comments at the top.\n";
		}
	    }

	    $typename = $typetable;
	    $typename =~ s/.*\.//;
	    $typename =~ tr/_/ /;
	    $fulltypetable = bctypetotable(bczapspaces($typename)); #Adds the right schema.
	    #Make a new backup name, because this should not be hard-coded based on the template.
	    ($backupname = $oldbackupname) =~ s/\d*$/scalar(time())/e;

	    #connect and see if there is any data in existing table
# 	    my $res = `$PSQL -t -c 'SELECT count(*) FROM $fulltypetable'`;
# 	    if($? == -1) { die "Unable to run $PSQL, cannot continue.\n" }
# 	    elsif($? >> 8 == 2) { die "Unable to query database with $PSQL,cannot continue.\n" }
# 	    elsif($? & 127) { die "$PSQL died with signal " . ($? & 127) . ".\n"; }
# 	    elsif($? >> 8 == 1) { $table_exists = 0 ; $keep = 0 } #No table found, no problem
# 	    elsif($? == 0) { $existing_rows = $res + 0 }
# 	    else{ die "Unexpected result running $PSQL, quitting.\n" }

	    #Easier to do it using the connection I have
	    my $res;
	    if(! eval {
		($res) = $dbh->selectrow_array("SELECT count(*) FROM $fulltypetable");
		1;
	    }) {
		$@ =~ /does not exist/ or die "$@\nUnable to check existing table.\n"; #Re-throw unexpected error.
	       	$table_exists = $keep = 0;
	    }	
	    $existing_rows = $res || 0;
	    $dbh->do("ROLLBACK TRANSACTION"); #Needed due to no auto-commit

	    if($existing_rows)
	    {
		print "Type $typename already exists in the database, and data has been uploaded.\n",
		      "The old table will be renamed but not erased.  You must copy the data manually,\n",
		      "then run \"typeio -F $backupname\" to remove the backup copy.\n";
		$keep = 1;
	    }

	    #Now modify the file to be loadable
	    for(@commands)
	    {
		#Inheritance check
		if(/^INHERITS \(("?.*?"?)\);/)
		{
		    eval { $dbh->do("SET search_path = $search_path;");
			   ($res) = $dbh->selectrow_array("SELECT count(*) FROM $1");
		           defined($res); 
		    }  
		    or die "$@\nThis template inherits from type $1 - you must load that first.\n";
		    $dbh->do("ROLLBACK TRANSACTION"); #Needed due to no auto-commit
		}

		if($table_exists)
		{
		    s/^(CREATE TABLE )"?$oldbackupname"?( AS SELECT \*)/${1}"${backupname}"${2}/;
		}
		else
		{
		    s/^(CREATE TABLE "?$oldbackupname"? AS SELECT \*.*)/-- $1/;
		    s/^(DROP TABLE "?$typetable"?;.*)/-- $1/;
		}

		s/^(SET search_path = ).*/${1}${search_path};/;
		#Backup is redundant if !$table_exists, but harmless.
		s/^(UPDATE "?barcode_description"? SET typename = ')$oldbackupname(')/${1}${backupname}$2/;
		s/^(GRANT ALL ON TABLE "?$typetable"? TO ).*/${1}"${user_account}";/;

		if($keep || !$table_exists)
		{
		    s/^(DROP TABLE "?)$oldbackupname("?;)/-- ${1}$backupname${2}/;
		    s/^(DELETE FROM "?barcode_description"? WHERE typename = ')$oldbackupname(';)/-- ${1}$backupname${2}/;
		}
		else
		{
		    s/^(DROP TABLE "?)$oldbackupname("?;)/${1}$backupname${2}/;
		    s/^(DELETE FROM "?barcode_description"? WHERE typename = ')$oldbackupname(';)/${1}$backupname${2}/;
		}
	    }

	    print "Loading \"$typename\" into $conn_params->{dbname}.$conn_params->{dbschema} using psql.\n";
	    print $table_exists ? "This replaces the old definition, " .
				  ( $keep ? "which will be kept as $backupname.\n" : "which will be removed.\n" )
				: "This is a new template type.\n";
	    print "\n";

	    #That should do it - fire it in.
 	    push @allcommands, @commands;
	}
	
	if(@allcommands)
	{
	    do_load(@allcommands);
	}
	else
	{
	    print "Nothing to do.\n";
	}

    }; #End block for local environment.

};

$SUBS{flush} = sub{

    #Remove references to a backup of an old table.
    #Need admin access ot the database, like for loading
    #connection not actually used -  we'll invoke psql directly.
    barcodeUtil::connectnow();
    my $conn_params = bcgetdbobj()->grab_connection_params();

    { local $ENV{PGHOST} = $conn_params->{dbhost} if $conn_params->{dbhost};
      local $ENV{PGPORT} = $conn_params->{dbport} if $conn_params->{dbport};
      local $ENV{PGDATABASE} = $conn_params->{dbname};

      my $search_path = "$conn_params->{dbschema}";
      $search_path .= ", $conn_params->{sysschema}" if $conn_params->{sysschema};
      $search_path .= ", pg_catalog";

      my @commands = ("SET search_path = $search_path;");

      for my $oldtype (@$types_filter)
      {
	  $oldtype =~ /^..._old_\d{10}$/ or die "$oldtype does not look like a backup table name.\n";

	  print "Flushing old table for $oldtype\n";

	  push @commands, "DROP TABLE \"$oldtype\";\n";
	  push @commands, "DELETE FROM barcode_description WHERE typename = '$oldtype';\n";
      }

      do_load(@commands);

    }; #End block for local variables
};

sub do_load
{
    #Login set by environmental variables, so we just need the text to feed
    #to psql
    my @data = @_;

    #DEBUG MODE - just print it
    #print @data, "\n";
    #return 1;

    print "You may be prompted for your database password by psql.\n";

    #feed the SQL to psql
    open(my $psql, "| $PSQL") || die "Unable to run psql";

    print $psql @data;

    close $psql;

    print "Finished.\n";
}

sub ask
{
    my $question = shift;
    my $answer = '';

    while(1)
    {
	print $question . ' ';
	$answer = <STDIN>;

	if($answer =~ /[yYnN]/) { last }
	else { print "Answer yes or no, you crazy fool!\n" }
    }
    $answer !~ /[nN]/; #This means that yn comes out as false
}

sub slurp
{
    my($fh, @res);
    for(@_) {
	open $fh, $_ or die "Cannot slurp $_ : $!\n";
	push @res, <$fh>;
	close $fh;
    }
    wantarray ? @res : \@res;
}

#main code
&{$SUBS{$mode}}(@ARGV);
