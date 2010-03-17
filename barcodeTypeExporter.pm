#!perl
use strict; use warnings;

# This is the code to export barcode types (ie. database tables).  It is used
# both from the admin_barcodes.cgi and from utility scripts, hence split
# out into an extra file.

package barcodeTypeExporter;
use barcodeUtil;
require Exporter;

#This is not a general purpose module - export everything!
our @ISA = qw(Exporter);
our @EXPORT = qw(dump_sql dump_desc);

our $PG_DUMP = $ENV{PG_DUMP} || "pg_dump";

sub dump_sql
{
    my ($typename) = @_;

    #Ensure the typname is valid
    bcchkbctype($typename) or die "$typename is not a known barcode type\n";

    #Now the SQL needs several elements
    # 1- Comment
    # 2- Change to DATA schema
    # 3- Rename old table in case it has data
    # 4- Rename old comments and flags
    # 5- Create table definition
    # 6- Dump description data
    # 7- Warning comment
    # 8- Drop backup table and cleanup

    my $now = time();
    my $newtablename = substr($typename,0,3) . "_old_$now";
    my $conn_params = bcgetdbobj()->grab_connection_params();
    my $sysschema = $conn_params->{sysschema} || "public";

    #First do the fiddly bit calling pg_dump
    my ($tabledump, $descdump);
    { local $ENV{PGDATABASE} = $conn_params->{dbname};
      local $ENV{PGUSER} = $conn_params->{dbuser};
      local $ENV{PGHOST} = $conn_params->{dbhost} if $conn_params->{dbhost};
      local $ENV{PGPORT} = $conn_params->{dbport} if $conn_params->{dbport};

      #Next bit is undocumented and insecure, as any local user on the server could
      #snoop the password using 'ps euww' - ye be warned!
      local $ENV{PGPASSWORD} = $conn_params->{dbpass};
      
      my $command = "$PG_DUMP -sO -t '$conn_params->{dbschema}.$typename'";
      $tabledump = `$command` or die diagnose('pg_dump of table', $command);

      my $command2 = "$PG_DUMP -aO -t '$conn_params->{sysschema}.barcode_description'";
      $descdump = `$command2` or die diagnose('pg_dump of description data', $command2);

    }; #End block for local environment
    
    my $res = '';

    # 1
    $res .= "-- DO NOT HAND EDIT THIS FILE if you want to use it with the typeio loader tool.\n--
-- Barcode type $typename
-- Exported from $conn_params->{dbname} on " . ($conn_params->{dbhost} || "local server") . "
-- At time " . localtime($now) . "
--
-- Commands to recreate this type definition follow.  The first few commands will rename
-- the old version of the table, if it exists.  This gives you a final opportunity to retrieve
-- data from the old table.
-- Once you are happy that the new type is installed the old table and annotations can be dropped.
--
";
    # 2
    $res .= "
SET search_path = $conn_params->{dbschema}, $sysschema, pg_catalog;
";

    # 3
    # I originally did this with a "ALTER TABLE ... RENAME TO ..." but the problem with that
    # is that all the constraints are kept and you get naming conflicts when you try to
    # recreate the new table with the same named constraints like "pk_my_primary_key"
    # Fortunately there is a trick to copy tables with no constraints.
    $res .= "
CREATE TABLE \"$newtablename\" AS SELECT * FROM \"$typename\";
DROP TABLE \"$typename\";
";

    # 4
    $res .= "
UPDATE barcode_description SET typename = '$newtablename'
    WHERE typename = '$typename';

";

    # 5
    for(split("\n", $tabledump))
    {
	#Skip unwanted lines
	#This is not foolproof but you would have to contrive to break it.
	$res .= "$_\n" unless !/./ || /^--/ || /^set/i;
    }
    $res .= "\n";

    # 6
    for(split("\n", $descdump))
    {
	#Extract relevant lines from the description table
	#This is not foolproof but you would have to contrive to break it.
	$res .= "$_\n" if /^$typename\t/ || /^COPY / || /^\\/;
    }

    # 7
    $res .= "
-- The last commands clean out the old tables.  If you are updating a type definition be
-- sure you are not losing any important data.  If the type definition is new then simply
-- ignore these lines.
";

    # 8
    $res .= "
DROP TABLE \"$newtablename\";
DELETE FROM barcode_description WHERE typename = '$newtablename';
";

    $res;
}

sub dump_desc
{
    my ($typename) = @_;

    #This already exists in barcodeUtil...
    bcdescribetype($typename);
}

sub diagnose
{
    #If I want to report the error from pg_dump I need to run the
    #command again and cature stderr.
	#Put in eval so this only gets compiled if needed.
    my ($taskname, $command) = @_;

    my $errorbuf = '';
    eval '
    use IPC::Open3;
    use File::Spec;
    use Symbol qw(gensym);
    open(NULL, ">", File::Spec->devnull);
    my $pid = open3(gensym, ">&NULL", \*PH, "$command");
    while( <PH> ) { $errorbuf .= $_ }
    waitpid($pid, 0);
    ';

    $@ ? "$taskname failed - unable to diagnose as EVAL returned:\n$@\n"
       : $errorbuf;
}

