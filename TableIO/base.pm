#!perl
use strict; use warnings;
package TableIO::base;
$VERSION = '$Revision$';

# CVS $Revision: 1.8 $ committed on $Date: 2006/04/24 17:34:40 $ by $Author: tbooth $
use Carp;

# CGI::Carp is stealing my errors :-(
sub abstract
{
    my @caller = caller(1);
    croak("Please implement this abstract method: ", $caller[3] );
}

#This is the base package for all the TableIO stuff.  It does all the boring OO housekeeping
#and has some default methods.
#Also the place to put your POD.

#Define some static variables - subclasses should override these.
use constant mime_type => "text/unknown";
use constant file_extension => "dat";

=head1 NAME

TableIO::base - abstract superclass for all TableIO enactors

=head1 SYNOPSIS

See TableIO for sysnopsis.  You should not use this class directly.

=head1 AUTHOR

Tim Booth, NEBC

=head1 METHODS

=over 4

=item * B<new()>

Constructor called via TableIO

=item * B<mime_type, file_extension>

Constants defined by the implementing class.  Needed to construct the http header.

=item * B<read_file($fh)>

Starts reading from a file handle - normally set up in constructor.

=item * B<flush()>

Cleans up the object and completes any reading or writing operations.

=cut

sub new
{
    #Should be called by TableIO.pm.
    my $this = {};
    my $invocant = shift();
    my $class = ref($invocant) || $invocant;

    if($class eq __PACKAGE__)
    {
	die "$class is an abstract class.  You may not instantiate it.  Got that?\n";
    }
    
    bless $this => $class;
    
    if(@_)
    {
	#Reader mode
	$this->{reader} = 1;	
	$this->{fh} = shift() and $this->start_read();
    }
    else
    {
	#Writer mode
	$this->{reader} = 0;
	$this->start_write();
    }
    $this;
}

sub read_file
{
    my $this = shift;
    $this->flush();
    $this->{reader} = 1;
    $this->{fh} = shift() or die "Need a file handle to read from!";
    $this->start_read();
}

sub flush
{
    my $this = shift();
    #Flush writer - generic version removes contents of hash
    %$this = ();
}

=item * B<reader() writer()>

Two assertions that let you check if the object is in read or write mode.

=cut

#These make it more succinct to see if I am a reader or writer.
sub writer
{
    my $this = shift();
    my @caller = caller;
    $caller[0] =~ /^TableIO::/ or die "Do you mind! This is a private method!";
    !$this->{reader} or croak "You cannot call the method $caller[3] on a reader object.";
}

sub reader
{
    my $this = shift();
    my @caller = caller;
    $caller[0] =~ /^TableIO::/ or die "Do you mind! This is a private method!";
    $this->{reader} or croak "You cannot call the method $caller[3] on a writer object.";
}

=back

=head2 Methods for Writer

=over 4

=item * B<start_write()>

This is a hook that subclasses can use for initialisation code.  Called just after the object is created
if it is a writer object.

=item * B<set_header($text)>

Set an optional header for the file.

=item * B<set_column_names(@names)>

Set the names of the columns in the file.
Names should include the first column, which should be "barcode"

=item * B<< set_attr($colnum, {attr=>val, ...})

Set one or more attributes on a column.  Attributes not mentioned will not be cleared.

Column attributes which it makes sense to set are:

 Type name/description { type => 'text(10)' }
 barcode flag or date or number+dp { format => 'bc', format => 'date', format => 2 }
 compulsory { compulsory => 1 }

The type is what will be displayed for the user.  The format will determine how the
cells in the column are formatted (not for CSV).

=cut

#Methods for the writer (the easy bit first)
sub start_write
{
    writer(my $this = shift);
    1;
}

sub set_header
{
    writer(my $this = shift);

    $this->{header} = shift;
}

sub set_column_names
{
    writer(my $this = shift);

    $this->{names} = \@_;
    $this->{attrs} = [];
}

sub set_attr
{
    #This generic version collects the attributes in a hash, but this may not be the best approach.

    writer(my $this = shift);

    my $colnum = shift; #Column number starting 0 (barcode column)
    my $attrs = shift;

    $this->{attrs}->[$colnum]->{$_} = $attrs->{$_} for keys %$attrs;
}

=item * B<add_row(@data)>

Add a row of data to the output.  Once rows start to be added the set_ methods should no longer be
called.  The result of doing so is undefined.

=item * B<add_empty($code)>

Add an empty row.  Basically equivalent to add_row($code, undef, undef, ...).

=item * B<add_masked_disposed($code, $mask)>

This will only be used when disposed codes are masked out.

=item * B<add_disposed(@data) add_empty_disposed($code)>

For CSV this will just call add_row/add_empty, but for Excel it could grey out the line
or something.

=cut

sub add_row
{
    writer(my $this = shift);
    abstract;
}

sub add_empty
{
    writer(my $this = shift);
    abstract;
}

sub add_masked_disposed
{
    writer(my $this = shift);
    abstract;
}

sub add_disposed
{
    #Defults to just adding the row as normal.
    shift()->add_row(@_);
}

sub add_empty_disposed
{
    #Likewise for add_disposed
    shift()->add_empty(@_);
}

=item * B<clear_attrs()>

Clears the attributes.  May not bother with this as you can just create a
new object.

=item * B<print_out($fh)>

Dump the file to the supplied open file handle or to STDOUT.

=item * B<as_string()>

Obtain the whole output as a scalar.  By default this and as_string
are mutually recursive, so you only need to override one.

=cut

sub clear_attrs
{
    writer(my $this = shift);
    #If it is inconvenient to enable this then override it
    #with something which dies with an error.

    my $colnum = shift;
    $this->{attrs}->[$colnum] = {};
}

sub print_out
{
    writer(my $this = shift);

    abstract;

    #How it should work
#     my $fh = shift || \*STDOUT;
# 
#     print $fh $this->as_string(); 
}

sub as_string
{

    writer(my $this = shift);

    abstract;

    #How it could work if you already had print_out sorted
#     my $buf;
#     my $fh = new IO::String($buf);
# 
#     $this->print_out($fh); 
#     $buf;
}

=back

=head2 Methods for Reader

=over 4

=item * B<start_read()>

This is simply a hook which subclasses can use for initialisation code.
It will be called right after the file for reading has been aquired.

=item * B<get_header()>

Return a header if one was found at the top of the file.
If you stored the header in the hash you don't need to override this.

=item * B<get_column_names()>

Return an arrayref to a list of the column names.
If you stored the column names in the hash you don't need to override this.

=item * B<find_barcode_column()>

Determine which column is the barcode.  You should not need to override this.

=item * B<get_all_barcodes()>

Returns an arrayref of all the barcodes in the file.  This is called before
the actual rows are read but should work at any time.

=item * B<get_column_attrs()>

I'm not implementing this!

=item * B<get_next_row()>

Returns an arrayref for the next row, or false for no row left.
Corresponds quite nicely with DBD::AnyData functionality.

=cut

#Methods for reader.  Assume that the file is being read already.
sub start_read
{
    reader(my $this = shift);

    #This is a hook for subclasses to start examining the file and do what they need to do.
    #Do not call directly!
    #Default null implementation.
    1;
}

sub get_header
{
    reader(my $this = shift);

    $this->{header};
}

sub get_column_names
{
    reader(my $this = shift);

    $this->{names};
}

sub find_barcode_column
{
    #Utility job - seems to belong here.
    reader(my $this = shift);
    
    my $headings = $this->get_column_names();
    my $bcfound;
    for(my $nn = 0; $nn < @$headings; $nn++)
    {
	if($headings->[$nn] eq 'barcode')
	{
	    $bcfound = $nn;
	    last;
	}
    }
    return "$bcfound";
}

sub get_all_barcodes
{
    reader(my $this = shift);

    abstract;
}

#There should be no "get_column_attrs" because we let the database
#do all the validation, right?
sub get_column_attrs
{
    reader(my $this = shift);

    croak "You have been naughty.";
}

sub get_next_row
{
    #Returns the next row as an array. The TableIO will clip all headers,
    #but otherwise it is up to the caller to work out what the data means.
    #Returns false of some sort for no more rows left.
    reader(my $this = shift);

#     die "Please implement this abstract method!";
    abstract;
}

=back

=cut

#That should do it.
0!=1;
