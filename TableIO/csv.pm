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
use Data::Dumper;
use Text::CSV;
use IO::String;
use IO::Wrap;
{ package IO::String; sub str{${shift()->string_ref }} }


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

    #Slurp up the file using Text::CSV
    my $csv_r = Text::CSV->new ({ binary => 1 }) or die "Cannot use CSV: ".Text::CSV->error_diag();
    my @allrows = ();

    #Start silly trickery, not needed with CGI > 4.05
    my $fh_orig_type = ref($this->{fh});
    my $wrapped_fh = bless $this->{fh}, "FileHandle";
    $wrapped_fh = wraphandle($wrapped_fh);
    bless $this->{fh}, $fh_orig_type;
    #End silliness

    while ( my $row = $csv_r->getline( $wrapped_fh ) ) {
	    push @allrows, $row;
    }
    $this->{allrows} = \@allrows;

    #Remove junk at the top
    for(@allrows)
    {
	#See if this row is the header
	if( $_->[0] =~ /^[>#]/ )
	{
	    $this->{header} = combine($_);
	    last;
	}
    }

    #Remove anything which begins with comment markers
    @allrows = grep {$_->[0] && $_->[0] !~ /^["]?[>#]/} @allrows;

    #Stash the headings from the first row:
    $this->{names} = shift(@allrows);
    #Now we can start reading values from row 0
    $this->{row_cursor} = 0;
}

#get_header and get_columns just use the default implementations

sub get_next_row
{
    reader(my $this = shift);

    #It's all pre-parsed so just spit out the next row.
    $this->{allrows}->[$this->{row_cursor}++];
}

sub get_all_barcodes
{
    reader(my $this = shift);

    #This was significantly easier with DBD::AnyData
    #For completeness, deal with the case where barcodes are not on col 0
    my $barcode_col = -1;
    my @names = @{$this->{names}};
    for(my $nn = 0; $nn < @names; $nn++)
    {
	if(lc($names[$nn]) eq 'barcode')
	{
	    $barcode_col = $nn;
	    last;
	}
    }

    if($barcode_col < 0)
    {
	die "No barcode column in the uploaded file.\n";
    }

    [ map {$_->[$barcode_col]} @{$this->{allrows}} ];
}

sub flush
{
    my $this = shift();

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
