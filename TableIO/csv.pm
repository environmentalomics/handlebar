#!perl
use strict; use warnings;

# CVS $Revision: 25 $ committed on $Date: 2006/02/27 14:11:01 $ by $Author: milo $

package TableIO::csv;
use base "TableIO::base";
(our $VERSION = '2.$Revision: 25 $') =~ y/[0-9.]//cd;

#Get reader and writer from the base package
sub reader {goto &TableIO::base::reader};
sub writer {goto &TableIO::base::writer};

use constant mime_type => "text/csv";
use constant file_extension => "csv";

#This module will import the original CSV.
#It will also import and export the improved CSV which has the following features:

# Header line at the top which will be prefixed with a > in the FASTA-stylee
# Data type info in the line below the headers (suggested by Milo)

# When importing, ignore any line beginning with #hash ,comma or >gt - that
# probably covers most eventualities.
# Should still permit rearrangement of columns, though.

use DBI;
require DBD::AnyData;
use Text::CSV;
use IO::String;
{ package IO::String; sub str{${shift()->string_ref }} }

#Massive kludge for DBD::AnyData
if(DBD::AnyData->VERSION eq '0.08')
{ eval
  '
    package DBD::AnyData::st;
    no warnings;

    sub DESTROY ($) { $_[0]->SUPER::DESTROY(@_) }
    sub finish ($) { $_[0]->SUPER::finish(@_) }
  ';
}

{ my $csv=Text::CSV->new( {binary=>0,eol=>"\n"} );
sub combine
{
    #Wraps the combine() from Text::CSV
    for(@_)
    {
	#Scrub newlines, tabs
	s/\n/\t/g;
	s/\t/   /g;
    }
    $csv->combine(@_) ? $csv->string() :
            confess("Invalid argument ", $csv->error_input());
}};

#Reader bits...

sub start_read
{
    reader(my $this = shift);

    #Slurp up the file.
    my $fh = $this->{fh};
    my @fhrows = <$fh>;

    #Remove junk at the top
    for(@fhrows)
    {
	my $datafound = 0;
	#See if this row is the header
	if( /^["]?[>#]/ )
	{
	    $this->{header} = $_ unless $this->{header};
	}
	elsif(/^,/)	   { s/^/#/; }
	elsif(!$datafound) { $datafound++; }
	else		   { last; }
    }

    #Remove anything which begins with comment markers
    @fhrows = grep {$_ && !/^["]?[>#]/} @fhrows;

    #Load the thing into DBD::AnyData
    my $addbh = DBI->connect('dbi:AnyData(RaiseError=>1):');
    $addbh->{Taint} = 1;

    eval{$addbh->func('csvimport', 'CSV',  \@fhrows, 'ad_import')};
    	$@ and die "DBD::AnyData was unable to load the file:\n$@";
    #Do not call the table 'import' or it will magically fail!

    #Determine the headings:
    my $sth = $addbh->prepare("SELECT * FROM csvimport LIMIT 1");
    $sth->execute();
    $this->{names} = $sth->{NAME};
    $sth->finish();

    #Save the dbh for later
    $this->{addbh} = $addbh;

    #Open the main reader statement handle.
    $this->{sth} = $addbh->prepare("SELECT * FROM csvimport");
    $this->{sth}->execute();
}

#get_header and get_columns just use the default implementations

sub get_next_row
{
    reader(my $this = shift);

    my $sth = $this->{sth};

    $this->{sth}->fetchrow_arrayref();
}

sub get_all_barcodes
{
    reader(my $this = shift);

    my $addbh = $this->{addbh};
    $addbh->selectcol_arrayref("SELECT barcode FROM csvimport");
}

sub flush
{
    my $this = shift();

    #Close $this->{sth} if it is open
    if($this->{sth})
    {
	$this->{sth}->finish();
    }
    
    $this->SUPER::flush();
}

#Writer bits...
 
#set_header, set_column_names and set_attr defer to superclass
#I'll print the whole header when the first row gets added.

sub add_row
{
    writer(my $this = shift);

    my $ios = $this->{ios};
    #If nothing has been written yet, create the output string and
    #output the header.
    $ios ||= $this->print_header_stuff();

    #Right, now actually print the row:
    print $ios combine(@_); 
}

sub add_empty
{
    writer(my $this = shift);
    my $code = shift();

    my @row = ('') x scalar(@{$this->{names}});
    $row[0] = $code;

    $this->add_row(@row);
}

sub add_masked_disposed
{
    writer(my $this = shift);
    my $code = shift();
    my $mask = shift();

    my @row = ($mask) x scalar(@{$this->{names}});
    $row[0] = $code;

    $this->add_row(@row);
}

sub as_string
{
    writer(my $this = shift);
    my $ios = $this->{ios};

    #Allow empty output
    $ios ||= $this->print_header_stuff();

    $ios->str();
}

sub print_out
{
    #Generic implementation.
    writer(my $this = shift);

    my $fh = shift || \*STDOUT;
    print $fh $this->as_string();
}

sub print_header_stuff
{
	writer(my $this = shift);
	my $ios;

	#Output the column headings, notes and header, not forgetting to escape it.
	$this->{ios} = $ios = new IO::String;

	print $ios combine(">$this->{header}");

	#And the column heads
	print $ios combine(@{$this->{names}});

	#And notes on the attibutes
	#Notes for 'barcode' need to be blank or '>' to skip the line
	my @attrs = ('');

	#Run through columns and get params.
	for(my $nn = 1; $nn < @{$this->{names}} ; $nn++)
	{
	    my $attrs_for_col = $this->{attrs}->[$nn];
	    my $attr_string = $attrs_for_col->{compulsory} ? '*' : '';
	    $attr_string .= $attrs_for_col->{type} || '';
	    
	    push @attrs, $attr_string;
	}
	print $ios combine(@attrs);

	$ios;
}

q:-)+<:  ||0;
