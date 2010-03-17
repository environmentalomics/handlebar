#!perl
use strict; use warnings;

# CVS $Revision: 1.6 $ committed on $Date: 2006/09/15 13:40:00 $ by $Author: tbooth $

#If I ever fully rationalise the code, this will be an API for interacting with the DB.
#If I ever add support for MySQL then all the database dependent stuff (eg locking a table,
#interpreting error codes, complex queries...) will end up in here where it is out of the 
#way.
#But for now it is basically a stub
package barcodeDB;

use DBI;
require DBD::Pg;

sub new
{
    my $class = shift();
    my $self = {};
    bless $self, $class;

    my $conf = shift();
    #Shunted connection params into barcodes.conf
    $self->{s} = {
	dbhost => $conf->{DATABASE_HOST} || "",
	dbname => $conf->{DATABASE_NAME},
	dbuser => $conf->{DATABASE_USER},
	dbpass => $conf->{DATABASE_PASS} || "",
	dbport => $conf->{DATABASE_PORT} || "",
	sysschema => $conf->{SYSTEM_SCHEMA} || "",
	dbschema => $conf->{DATA_SCHEMA} || "data",
    };
    $self->{dbh} = $self->dbconnect();

    return $self;
}

sub disconnect
{
    shift()->{dbh}->disconnect();
}

sub autocommit
{
    my $dbh = shift()->{dbh};
    my $newval = shift;

    my $ac = $dbh->{AutoCommit};
    $dbh->{AutoCommit} = $newval if defined $newval;
    $ac;
}

sub get_handle
{
    shift()->{dbh};
}

sub get_data_schema
{
    shift()->{s}->{dbschema};
}

#This kludge is needed to feed the connection params to the admin tool, which
#uses them to invoke pg_dump when a table is being exported.
sub grab_connection_params
{
    shift()->{s};
}

#Private sub
sub dbconnect
{
    my $s = shift()->{s};

    #Check that we have all four.
    scalar(grep {defined($_)} values(%$s)) == 7 
	or die "Missing some database connection parameters in barcodes.conf\n";

    my $dbh = eval{
	      DBI->connect("DBI:Pg:dbname=$s->{dbname}" . 
				($s->{dbhost} ? ";host=$s->{dbhost}" : "") .
				($s->{dbport} ? ";port=$s->{dbport}" : "") ,
			   "$s->{dbuser}", "$s->{dbpass}",
			   {RaiseError=>1, AutoCommit=>0, Taint=>1})
    };
 
    $dbh or die "Failed to connect to the barcode database - unable to continue.\n",
		( $DBI::errstr ?
		  "The database server said: $DBI::errstr\n" :
		  "There was an internal error: $@\n" );

    #Now using ISO-8859-15 for all I/O, because of unicode woes:
    $dbh->do(qq{SET client_encoding="ISO_8859_15"});

    if($s->{sysschema})
    {
	$dbh->do(qq|SET search_path="$s->{sysschema}"|);
	$dbh->commit();
    }
    $dbh;
}

1;
