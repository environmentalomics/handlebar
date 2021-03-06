#!perl

use strict; use warnings;

package TableIO::xls;
use base "TableIO::base";
(our $VERSION = '2.$Revision: 43 $') =~ y/[0-9.]//cd;

#Get reader and writer from the base package
sub reader {goto &TableIO::base::reader};
sub writer {goto &TableIO::base::writer};

#Move to use Unicode throughout the application,
#but unfortunately the stuff I extract from the Excel files is not utf-8.
# use Encode;

use constant mime_type => "application/xls";
use constant file_extension => "xls";

#This module will import Excel files.

# It will also add the extra info as per CSV as follows:
# Header line at the top which will be prefixed with a > in the FASTA-stylee
# Data type info in the line below the headers (suggested by Milo)

# It will add formatting, colouring and fix the date format to the reccommended
# yyyy-mm-dd.  It will import from OpenOffice Excel files, despite the hurdles
# involved.

# When importing, ignore any line beginning with #hash ,comma or >gt - that
# probably covers most eventualities.
# Should still permit rearrangement of columns, though.

use Spreadsheet::WriteExcel;
use Spreadsheet::ParseExcel;

use Data::Dumper;
use IO::String;

#Reader bits...

#OK, first off we have the dates problem.  Dates in Excel are like some kind of
#freakish nightmare.  I don't even want to go into them.  Generally the ParseExcel
#module is able to sort out the dates correctly, but for any Excel file saved
#in OpenOffice it was returning integers.  So, how does it tell the difference
#between an integer and a date?  It guesses!  But it guesses a bit wrong. Here
#is the fix.
{ 
    package TableIO::xls::myformatter;
    require Spreadsheet::ParseExcel::FmtDefault;
    
    our @ISA = qw(Spreadsheet::ParseExcel::FmtDefault);

    sub new {
	bless {} => shift;
    }

    sub ChkType($$$) {
	my $this = shift;
	my ($iNumeric, $iFmtIdx) = @_;

	my $typename = $this->SUPER::ChkType(@_);

	#I know that these classes should be dates.
	if ($typename eq "Numeric") {
	    if( ($iFmtIdx >= 0xA5) && ($iFmtIdx <= 0xAA) )
	    {
		$typename = "Date";
	    }
	}
	return $typename;
    }

    sub FmtStringDef($$$;$) {
	my $this = shift;
	my ($iFmtIdx, $oBook, $rhFmt) = @_;

	my $sFmtStr = $this->SUPER::FmtStringDef(@_);

	#Force dates to something useful for me
	if($sFmtStr =~ /^[dDmMyY]/)
	{
	    $sFmtStr = 'd-mmm-yyyy';
	}
	
	return $sFmtStr;
    }
}

sub start_read
{
    reader(my $this = shift);

    # Grab the filehandle and read in the file..
    my $fh = $this->{fh};
    #binmode $fh, ":utf8";
    my $xls = new Spreadsheet::ParseExcel;
    my $obook = $xls->Parse($fh, new TableIO::xls::myformatter);

    # We always want the first sheet.
    my $sheet = $obook->{Worksheet}[0];
    my @fhrows;

    # read each cell on the worksheet by iterating over them
    ROW: for(my $iR = $sheet->{MinRow} ; defined $sheet->{MaxRow} && $iR <= $sheet->{MaxRow} ; $iR++)
    {
	my $firstcell = $sheet->{Cells}[$iR][0];
    
	# if the header has not been defined and the first cell matches it,
	# set the headers and skip to the next row
	if (!defined $this->{header} and $firstcell->{Val} =~ /^[>#]/) 
	{ 
	    $this->{header} = $firstcell->{Val}; 
	    next ROW;
	}
	
	# trim off rows with a blank first cell so long as there are no codes yet seen
	# (though we may have seen the header line)
	(!$firstcell->{Val} && @fhrows <= 1) and next ROW;

	# trim off any other gunk
	($firstcell->{Val} =~ /^[>#]/) and next ROW;

	push @fhrows, [];
	    
	for(my $iC = 0 ; defined $sheet->{MaxCol} && $iC <= $sheet->{MaxCol} ; $iC++) 
	{
	    my $cell = $sheet->{Cells}[$iR][$iC];
	    
	    # the previous code had an array of arrays containing each of the lines of
	    # the original excel sheet. This line should re-create that, allowing the
	    # rest of the code to work as before.
  	    $fhrows[-1][$iC] = $cell->Value() if $cell;
	    
	    #Note that an empty cells wants to become undef.
		next unless defined $fhrows[-1][$iC]; #Suppress undef warning
	    $fhrows[-1][$iC] = undef unless $fhrows[-1][$iC] =~ /\S/;
	}
    }

    # chuck the sheet if it has no data
    unless (@fhrows)
    {
    # some sort of appropriate error
	die "No data found in imported xls file:\n$@";
    }

    # Dispose the sheet - we don't need to keep it.
    undef $sheet;
    
    # if the above has worked, the 0th row 
    # should now be the headings. It is 
    # purged to save mucking about when
    # getting all bar codes, later
    $this->{names} = shift @fhrows;

    # save link to array of values
    $this->{allrows} = \@fhrows;

}

#get_header and get_columns just use the default implementations

sub get_next_row
{
    reader(my $this = shift);
    my $allrows = $this->{allrows};

    shift @$allrows; 
}

sub get_all_barcodes
{
    reader(my $this = shift);
    my $allrows = $this->{allrows};
    
    my $bcfound = $this->find_barcode_column();

    my @barcodes = map { $_->[$bcfound] } @{$allrows};
    return \@barcodes;
}

sub flush
{
    my $this = shift();

    $this->SUPER::flush();
}

#Writer bits...
 
#set_header and set_attr defer to superclass
#I'll print the whole header when the first row gets added.

#Slightly modified version to support
#Milo's implementation of private_add_row
sub set_column_names
{
    writer(my $this = shift);

    $this->{names} = \@_;
    $this->{attrs} = [];
    $this->{nulls} = [(undef) x (scalar(@_) - 1)];
}

#The meat of the row adding logic is in here.
sub private_add_row
{
    my $this = shift;
    my $addrow = $this->{addrow} || 3;

    # get data that's passed in
    my @data = @{shift()};
    my $maskdisp = shift || '';

    # strike out if disposed, turn black if masked
    my $strike = ($maskdisp eq "disposed" ? 1 : 0);

    # print the header if no rows have been added yet
    my $ws = $this->{ws};
    my $excel = $this->{excel};
    $this->print_header_stuff() unless $this->{header_printed};

    #The appropriate formats will be precalculated and available in the formats array.
    my $formats = $this->{formats};

    for (my $i = 0; $i < @data; $i++)
    {
	$ws->write($addrow,
		   $i,
		   $data[$i], 
		   $formats->[$i]->[$strike]);
    }

    $this->{addrow} = $addrow + 1;
}
    
sub precalculate_formats
{
    my $this = shift;
    
    # set formats for this worksheet for each column, whilst
    # filling cells in individually
    my $excel = $this->{excel};
    my @formats;

    my $column_count = scalar(@{$this->{names}});
    for (my $i = 0; $i < $column_count; $i++)
    {
    	my $format = $this->{attrs}->[$i]->{format};
	defined($format) or $format = ''; #Just to avoid warnings.

	# do "on the fly" formatting based on the format string
	if ($format eq "bc" || $i == 0)
	{
	    # this should turn the barcode to blue text
	    push( @formats, {-color => 'blue'});
	}
	elsif ($format eq "date")
	{
	    push( @formats, {-num_format => "yyyy-mm-dd", -align => "left"});
	}
	elsif ($format eq "0")
	{
	    push( @formats, {-num_format => "0"});
	}
	elsif ($format =~ /\d+/)
	{
	    # Currently all floats default to 4dp, but this needs to be fixed in the
	    # calling code.  The number in brackets in the description gives
	    # the number of bytes of storage so that is no use.
	    my $dp = "0" x $format;
	    push( @formats, {-num_format => "0.$dp"});
	}
	else
	{
	    #Force to straight text to stop Excel from faffing with the value
	    push( @formats, {-num_format => "@", -align => "left"});
	}
    }

    #Now run through the formats and make strikeout and normal versions
    for(@formats)
    {
	$_ = [ $excel->add_format(%$_),
	       $excel->add_format(%$_, -font_strikeout => 1),
	     ];
    }

    $this->{formats} = \@formats;
}

sub add_row
{
    writer(my $this = shift);

    $this->private_add_row(\@_);
}

sub add_disposed
{
    writer(my $this = shift);

    $this->private_add_row(\@_, "disposed");
}

sub add_masked_disposed
{
    writer(my $this = shift);

    my($code, $mask) = @_;
    
    my @row = ($mask) x scalar(@{$this->{names}});
    $row[0] = $code;
	
    $this->private_add_row(\@row, "disposed");
}

sub add_empty
{
    writer(my $this = shift);

    $this->private_add_row([@_, @{$this->{nulls}}]);
}

sub add_empty_disposed
{
    writer(my $this = shift);

    $this->private_add_row([@_, @{$this->{nulls}}], "disposed");
}

sub as_string
{
    writer(my $this = shift);
    my $ios = $this->{ios} or die "Assertion failed - \$ios is undefined.";

    #Allow empty output
    $this->print_header_stuff() unless $this->{header_printed};

    #Need this to actually flush the data into the string!
    $this->{excel}->close();

    ${$ios->string_ref()};
}

sub print_out
{
    #Generic implementation.
    writer(my $this = shift);

    my $fh = shift || \*STDOUT;

#     my $ios = $this->{ios};
#     print $ios "How rude";
#     die $ios->str();

    #File handle should apparently be set to binary mode.
    binmode($fh);
    print $fh $this->as_string();
}


sub start_write
{
    writer(my $this = shift);

    # create the excel object and then a worksheet
    # the worksheet is the bit to be passed around,
    # written to, &c. except for adding formats
    my $ios = IO::String->new;
    my $excel = Spreadsheet::WriteExcel->new($ios);

    # store worksheet
    $this->{ios} = $ios;
    $this->{excel} = $excel;
    $this->{ws} = $excel->add_worksheet();
}

sub print_header_stuff
{
    writer(my $this = shift);
    my $ws = $this->{ws};
    my $excel = $this->{excel};

    #First thing to do is widen all columns to 18 chars
    $ws->set_column(0, 0, 10);
    $ws->set_column(1, scalar(@{$this->{names}}) - 1, 18);

    my $bold = $excel->add_format(-bold => 1);
    my $ital = $excel->add_format(-italic => 1);

    $ws->write(0,0,">$this->{header}", $bold);

    #And the column heads
    my $col = 0;
    foreach my $name (@{$this->{names}})
    {
	# add set format here...
	$ws->write(1,
		   $col,
		   $name,
		   !$col || $this->{attrs}->[$col]->{compulsory} ? $bold : $ital);
	$col++;
    }

    #And notes on the attibutes
    #Notes for 'barcode' need to be blank, or else begin with a '>' or '#'
    #my @attrs = ('');

    #Run through columns and get params.
    for(my $nn = 1; $nn < @{$this->{names}} ; $nn++)
    {
	my $attrs_for_col = $this->{attrs}->[$nn];
	my $attr_string = $attrs_for_col->{compulsory} ? '*' : '';
	$attr_string .= $attrs_for_col->{type} || '';
	    
	$ws->write(2,$nn,$attr_string,$attrs_for_col->{compulsory} ? $bold : $ital);
    }

    #Final job is to precalculate the formats to output
    $this->precalculate_formats();

    $this->{header_printed} = 1;
}



q:-)+<:  ||0;
