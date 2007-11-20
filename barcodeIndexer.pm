#
#===============================================================================
#
#         FILE:  barcodeIndexer.pm
#
#  DESCRIPTION:  Maintains indices so that I can find children of a given
#				 barcode.
#
#        FILES:  ---
#         BUGS:  ---
#        NOTES:  ---
#       AUTHOR:  Tim Booth (TB), <tbooth@ceh.ac.uk>
#      COMPANY:  NEBC
#      VERSION:  1.0
#      CREATED:  12/11/07 17:02:31 GMT
#     REVISION:  ---
#===============================================================================
package barcodeIndexer;

require barcodeUtil;
import barcodeUtil;

use strict;
use warnings;

#On a system where the table is not in place, I probably just want to silently
#continue.
our $IGNORE_ERRORS = 1;
our $INDEX_TABLE = 'barcode_link_index';

#-- SQL for barcode_link_index
#    CREATE TABLE barcode_link_index
#    (
#      childtype varchar(30) NOT NULL,
#      childcode int8 NOT NULL,
#      columnname varchar(30) NOT NULL,
#      parentcode int8 NOT NULL,
#      external_id int8,
#      CONSTRAINT pk_link_index PRIMARY KEY (childcode, columnname)
#    ) 
#    WITHOUT OIDS;
#
#    CREATE INDEX idx_link_index_childcode ON barcode_link_index(childcode);
#    CREATE INDEX idx_link_index_parentcode ON barcode_link_index(parentcode);
#--END


# The index table has childtype, childcode, columnname, parentcode, external_id
# Ie for barcode 'childcode' of type 'childtype' the column 'columnname' links back to 'parentcode'
# I don't record the type of the parent - it may not even be inserted yet.  Recording the type
# of the child is useful for housekeeping.
# 'external_id' allows me to link across databases (eg. at PML).  I'd need a script that looked in
# one database for any links to a foreign parent and pumped them into the relevant database.  For the
# purposes of this module I'll not touch any row where the external_id is non-null and leave actually
# making it work as a future project.

use Exporter;
our @ISA = qw(Exporter);
our @EXPORT = qw(indexcodes);
our @EXPORT_OK = qw(indexrange rebuildindex);

sub rebuildindex
{
    my @typenames = @_;
    my $indexall = 0; #Flag to say when this is a full re-index
    my $sth;

    if(!@typenames)
    {
	@typenames = @{bcgetbctypes()};
	$indexall = 1;

	#Clear everything.  This covers the case where a type is renamed and all the stuff
	#referring to the old name needs to be flushed.
	#Don't ignore errors here - if someone asked for a full rebuild they probably expect
	#it to work!
	$sth = bcprepare("DELETE FROM $INDEX_TABLE WHERE external_id IS NULL");
	$sth->execute();
	undef($sth);
    }

    for (@typenames)
    {
	my $type = bczapspaces($_);

	unless($indexall)
	{
	    $sth = bcprepare("DELETE FROM $INDEX_TABLE WHERE childtype = ? AND external_id IS NULL");
	    $sth->execute($type);
	    undef($sth);
	}

	my @bccols = find_columns_with_barcodes($type) or next;
	my $typequoted = quote($type);
	my $typetable = bctypetotable($type);

	for my $colname (@bccols)
	{
	    my $colnamequoted = quote($colname);

	    $sth = bcprepare(
	    "INSERT INTO $INDEX_TABLE (childtype, childcode, columnname, parentcode)
	     SELECT $typequoted, barcode, $colnamequoted, $colname
	     FROM $typetable
	     WHERE $colname IS NOT NULL");

	    $sth->execute();
	 }

	 #Don't commit anything - leave that to the caller!
     }
}

sub indexcodes
{
    #The primary function to be called when anything is updated.  Takes a list of codes to index.
    #Caller must de-quote them.
    my ($sth, $code);

    #Now for maximum efficiency of database access I want to group all codes of the same type
    #together and furthermore if there is more than one column to index I want to do each column in
    #a batch.  Normally all the codes will be of the same type, but there is no guarantee of this.
    #Therefore examine the codes and build a hash:
    #	{ type1 => [ @codes ],
    #	  type2 => [ @codes ]  }
    #Note that due to Pg limitations I can only have one prepared statement on the go at a time, so calling 
    #stuff like bcgetinfofornumber in between updates is a no-no.

    my %hashbytype = ();
    for $code (@_)
    {
	#The following will die if the code is unallocated, but it is perfectly
	#legal for the code to be allocated but not in use.
	my (undef, $type) = bcgetinfofornumber($code);
	
	$hashbytype{$type} ||= [];
	push(@{$hashbytype{$type}}, $code);
    }

    for my $type(keys %hashbytype)
    {
	my $typequoted = quote($type);
	my $typetable = bctypetotable($type);
	my $codelist = join(',', @{$hashbytype{$type}});

	eval {
	    $sth = bcprepare("DELETE FROM $INDEX_TABLE WHERE external_id IS NULL
			      AND childcode IN ($codelist)");
	    $sth->execute();
	    undef($sth);
	};
	if($@)
	{
	    #Looks like I can't write to the table, quietly give up or maybe die...
	    if($IGNORE_ERRORS) { return 0 } else { die $@ };
	}

	for my $colname(find_columns_with_barcodes($type))
	{
	    my $colnamequoted = quote($colname);

	    $sth = bcprepare(
		"INSERT INTO $INDEX_TABLE (childtype, childcode, columnname, parentcode)
		 SELECT $typequoted, barcode, $colnamequoted, $colname
		 FROM $typetable
		 WHERE $colname IS NOT NULL
		 AND barcode IN ($codelist)");
	    $sth->execute();
	    undef($sth);
	}

	#Don't commit anything - leave that to the caller
    }
}

sub indexrange
{
    my ($from, $to) = $_;
    my $sth;

    if ($from > $to)
    {
	($from, $to) = ($to, $from);
    }

    my (undef, $type, undef, undef, $fromcode) = bcgetinfofornumber($from);
    my $typequoted = quote($type);
    my $typetable = bctypetotable($type);
    
    [bcgetinfofornumber($to)]->[4] == $fromcode or die "Codes for indexrange must be in the same allocation block.";

    eval{
	$sth = bcprepare("DELETE FROM $INDEX_TABLE WHERE external_id IS NULL
			  AND childcode >= ?
			  AND childcode <= ?");
	$sth->execute($from, $to);
	undef($sth);
    };
    if($@)
    {
	#Looks like I can't write to the table, quietly give up or maybe die...
	if($IGNORE_ERRORS) { return 0 } else { die $@ };
    }

    for my $colname(find_columns_with_barcodes($type))
    {
	my $colnamequoted = quote($colname);

	$sth = bcprepare(
	    "INSERT INTO $INDEX_TABLE (childtype, childcode, columnname, parentcode)
	     SELECT $typequoted, barcode, $colnamequoted, $colname
	     FROM $typetable
	     WHERE $colname IS NOT NULL
	     AND barcode >= $from AND barcode <= $to");
	$sth->execute();
	undef($sth);
    }

    #Don't commit anything - leave that to the caller.
} 

sub quote
{
    bcgetdbobj()->get_handle()->quote($_[0]);
}

sub find_columns_with_barcodes
{
    my $table = shift;
    my @columns_to_process = ();

    my @colinfo;
    bcgetcolumninfo($table, {}, \@colinfo);
    for my $column(map {$_->{COLUMN_NAME}} @colinfo)
    {
	next if $column eq 'barcode';

	my $flags = bcgetflagsforfield($table, $column);
	push (@columns_to_process, $column) if $flags->{bc};
    }
    @columns_to_process;
}
	    
