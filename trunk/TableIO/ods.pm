#!perl
use strict; use warnings;

package TableIO::ods;
use base "TableIO::base";
(our $VERSION = '2.$Revision$') =~ y/[0-9.]//cd;

#Get reader and writer from the base package
sub reader {goto &TableIO::base::reader};
sub writer {goto &TableIO::base::writer};

#This class implements the reader and writer for OpenDocument spreadsheets
#it should also be able to read old style .sxc files, but there is not much
#point in writing them

use constant mime_type => "application/vnd.oasis.opendocument.spreadsheet";
use constant file_extension => "ods";

# As per the Excel module, this one will
# It will also add the extra info as per CSV as follows:
# Header line at the top which will be prefixed with a > in the FASTA-stylee
# Data type info in the line below the headers (suggested by Milo)

# It will add formatting, colouring and fix the date format to the reccommended
# yyyy-mm-dd.

# When importing, ignore any line beginning with #hash ,comma or >gt - that
# probably covers most eventualities.
# Should still permit rearrangement of columns.

use OpenOffice::OODoc;
use IO::Handle;
use IO::File;

use Data::Dumper;

sub _fix_fh
{
    #OODoc depends on Archive::Zip which needs proper modern filehandles
    #to read from, but CGI serves up some broken old school ones.
    #Putting the workaround in this module, on the basis that it doesn't seem to
    #fit anywhere else, though it is really a CGI problem.
    my ($fh) = @_;
    if(ref $fh eq 'Fh')
    {
	return ((new IO::File)->fdopen(fileno($fh), 'r'));
    }
    $fh;

}

#Reader bits...
#Do all the hard stuff at the start.
sub start_read
{
    reader(my $this = shift);

    # Grab the filehandle and read in the file..
    my $fh = _fix_fh($this->{fh});
    #die Dumper($fh);
    #binmode $fh, ":utf8";'
    my $oofile = ooFile('/dev/null', source_filehandle => $fh) or die "Failed to read file.\n";
    my $document = ooDocument(file => $oofile);

# DEBUG
#     die $document->getTableList();

    # We always want the first sheet.
    my @fhrows;
    my ($sheet) = $document->getTableList();
    # Get all the data, but the table has not been normalized so duplicate
    # columns will only show up as one item.  Therefore scan this data until I find the
    # colnames row (where all columns should be unique) and use that to determine how
    # large a table area to normalize.
    my @tabletext = $document->getTableText($sheet);
# DEBUG
#    die @{$tabletext[1]};

    # scan for colnames
    ROW: for my $arow (@tabletext)
    {
	my $firstcell = $arow->[0];
    
	# skip, eg. the line that has the cell format types in it and any other gunk
	if (!$firstcell or $firstcell =~ /^["]?[>#,]/)
	{
	    next ROW;
	}

	#This should be the colnames row - grab it and stop
	#??do I need to copy the array or is this reference safe??
	$this->{names} = $arow;
	last ROW; 
    }

    #normalize and re-extract
    $document->normalizeSheet($sheet,scalar(@tabletext),scalar(@{$this->{names}})-1);
    @tabletext = $document->getTableText($sheet);

    #Scan again - this time tidying up (apologies for grep abuse and "{;{")
    @fhrows = grep
    {;{
	my $arow = $_;
	my $firstcell = $arow->[0];
    
	# if the header has not been defined and the first cell matches it,
	# grab the header line
	if (!defined $this->{header} and $firstcell =~ /^[>#]/) 
	{ 
	    $this->{header} = $firstcell; 
	    0, next;
	}

	# trim off rows with a blank first cell so long as there are no codes yet seen
	# (though we may have seen the header line)
	0, next if (!$firstcell && @fhrows <= 1);

	# trim off any other commented lines
	0, next if ($firstcell =~ /^[>#]/);

	# With Excel, and CSV import, I know that all rows will be the same length and I catch
	# out-of-bounds data later by looking for blanks appearing on the end of the header
	# row.  Therefore achieve the equivalent effect here by pushing a blank onto the header 
	# if I find a longer row.
	push @{$this->{names}}, '' if (@{$this->{names}} < @$arow);

	# Now, the last item in the list will be empty, so trim it (can I really assume this?)
#	die Dumper($arow) if  (@$arow)
	pop @$arow; 

	#Fix any empty cells to be undefined
	for(@$arow) 
	{
	    $_ = undef unless /\S/;
	}
	1;
    }} @tabletext;

    # chuck the sheet if it has no data
    unless (@fhrows)
    {
	# some sort of appropriate error
	die "No data found in imported ", file_extension, " file:\n$@";
    }

    #Dont' need that file handle any more
    delete $this->{fh};

    # The first row of the array will have the colnames, but we have already grabbed them,
    # and maybe added some spaces to the end, so throw away the first line and trim the names
    shift @fhrows;
    pop @{$this->{names}};

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
	    push( @formats, {-num_format => 0});
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
    die "Writing of OpenDocument not yet implemented! D'oh!\n";

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
    #Notes for 'barcode' need to be blank, or else begin with a '>'
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
