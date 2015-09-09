#!perl
use strict; use warnings;

# CVS $Revision: 27 $ committed on $Date: 2006/09/15 13:40:00 $ by $Author: tbooth $

package TableIO;
our $TableIO = "TableIO";
(our $VERSION = '2.$Revision: 27 $') =~ y/[0-9.]//cd;

=head1 NAME

TableIO - The import/export wrapper for the barcode database.

=head1 AUTHOR

Tim Booth (tbooth@ceh.ac.uk)

=head1 SYNOPSIS

 my $io = new TableIO();
 my $formats = $io->get_format_names();
 my $writer = $io->get_writer($formats->[0]);

 my $reader = $io->get_reader($fh, "file.csv");

=head1 SUMMARY

Unlike most of the barcode code, this bit is written properly(ish).  The reasons for taking care are:

1) So that Milo can implement the alternative exporters.

2) So that other developers can do their own exporters when this goes OSS.

3) It was about time I wrote some neater code.

See the TableIO::base module for info on how to use the TableIO, and more importantly how
to go about writing a new wrapper.  This class will provide the static factory methods to 
determine the correct loader and generate table IO objects of the supported
types.  The core code need know nothing about the formats, and the IO modules should be 
insulated against the core code (ie no CGI ops).
The main advantage of having this factory class is that we do not need to load all the
file importers and exporters at once.  That would be a lot of dependency modules and
would slow down the system considerably - this way they are loaded on demand.

The initial type to be supported is CSV, with OOo and Excel following rapidly.

=head1 FUNCTIONS ETC.

=over 4

=item * B<@FORMATS>

The FORMATS array contains information about the supported file types.
If a new format is to be supported it must be added to the list here - 
picking up the types by scanning the available modules is possible
but overkill.

=cut

#Supported formats:
#Name, Extn, Notes (module name same as extn)

my @FORMATS = (
    ["Comma Separated Values", "csv", "Comma-separated values flat text file", 1 ],
    ["OpenDocument",  "ods", "Native format for OpenOffice 2.0 spreadsheets", 0 ],
    ["OpenOffice-1 Calc",  "sxc", "Legacy format for OpenOffice spreadsheets (read only)", 0 ],
    ["Excel", "xls", "Microsoft Excel format", 1 ],
);

=item * B<get_formats()>

Returns the supported formats in a hash of hashes.

    $excel_notes = $io->get_formats()->{Excel}->{notes};

=item * B<get_format_names()>

Returns an array of format names in the order they appear in @FORMATS

    $third_format = $io->get_format_names()->[2]; #Currently "Excel"

=cut

sub get_formats
{
    my %ret;

    for(@FORMATS)
    {
	$ret{$_->[0]} = {name=>$_->[0], extn=>$_->[1], notes=>$_->[2]};
    }
    \%ret;
}

sub get_format_names
{
    #Returns the names of the active formats in order as an arrayref.
    [map {$_->[3] ? $_->[0] : ()} @FORMATS];
}

=item * B<get_writer($formatname)>

Returns a writer object for the named format.

=cut

sub get_writer
{
    my $self = shift();
    my $wanted = shift();
    my $fmt;

    my $formats = get_formats();
    #Assertion that the caller has not messed up:
    $fmt = $formats->{$wanted} or die "Error - no such format $wanted.";

    #Er, can I do this without an Eval - no?
    eval "
	require ${TableIO}::$fmt->{extn};
	${TableIO}::$fmt->{extn}->new();
    " || die $@;
}

=item * B<get_reader( \*fh, $fname ) get_reader( $typename )>

 get_reader( \*fh, $fname ) # -> Guess correct reader given a name and open file handle and return instantiated.
 get_reader( $typename ) # -> Instantiate by type. You need to then load the file explicitly (do I need this?).
 get_reader() # -> Error!

=item * B<guess_format_for_filename()>

Static method used by get_reader.  In future maybe I should not just rely on the extension?
    
=cut

sub get_reader
{
    my $self = shift();
    my $readerobj;

    if(@_ == 1)
    {
	my $wanted = shift();
	my $fmt;
	my $formats = get_formats();
	$fmt = $formats->{$wanted} or die "Error - no such format $wanted.";

	eval "
	    require ${TableIO}::$fmt->{extn};
	    \$readerobj = ${TableIO}::$fmt->{extn}->new(undef);
	" || die "Cannot load module $fmt->{extn}.pm.\n";
    }
    elsif(@_ == 2)
    {
	my($fh, $fname) = @_;
	my $fmt = guess_format_for_filename($fname);

	#I could do this with a cunning call to `file` but for
	#now just go by extension.
	$fmt or die "Unable to determine a suitable reader for $fname.\n";
	
	eval "
	    require ${TableIO}::$fmt->{extn};
	    \$readerobj = ${TableIO}::$fmt->{extn}->new(\$fh);
	" || die "Failed to use module $fmt->{extn}.pm to load file of type $fmt->{name}.\n$@\n";
    }
    else
    {
	die "Wrong number of args.";
    }
    $readerobj;
}

sub guess_format_for_filename
{
    #Probably most useful for the function above.
    my $fname = shift();
    my $extn = lc( [$fname =~ /.*\.(\w+)/]->[0] );
    my $formats = get_formats();

    my ($fmt) = grep { $_->{extn} eq $extn } values(%$formats);
    $fmt or undef;
}

=item * B<new()>

The new() function simply allows TableIO methods to be called in an OO-style way.

You can say:

 my $io = new TableIO();
 my $formats = $io->get_format_names();

Or you can stick with:

 my $formats = TableIO->get_format_names();

It matters not.

=back

=cut

sub new
{
    my $self;
    bless( ($self = \$self) => shift() ); 
}

1;
