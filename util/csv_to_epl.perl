#!/usr/bin/perl
#csv_to_epl.perl - created Mon Feb 20 17:44:46 2006
 
use strict;
use warnings;
use Text::CSV_XS;
use IO::File;
 
#The purpose of this script is to take a CSV input file, and for each line
#print a label with some info on it.  Quick-and-dirty, it is currently
#hard-coded to the small labels.

#Usage csv_to_epl data.csv col1 [col2 col3...] > out.epl

my $rows_on_label = 5;
my $cols_on_label = 20;

my $label_length = 3;
my $label_sep = ':';
my $val_length = $cols_on_label - $label_length - length($label_sep);
my $empty_val = '-';

my $csv = Text::CSV_XS->new();

#Open the input CSV

my $infile = new IO::File shift(), "r" or die 
		    "Cannot open CSV for input";

my @colstoprint = @ARGV;

if(@colstoprint == 0){ die "Nothing specified to print."}
if(@colstoprint > $rows_on_label){ die "Label to small to print more than $rows_on_label fields."}

#Find the header
my %headings;
my $nn = 0;
while(<$infile>)
{
    next if /^["]?[>#,]/;
    $csv->parse($_) or die "Bad line $_";
    $headings{$_} = $nn++ for($csv->fields());
    last;
}

#Generate the labels
my @cmds;
push @cmds, 'US1', 'q200';

while(<$infile>)
{
    #Skip junk
    next if /^["]?[>#,]/;

    $csv->parse($_) or die "Bad line $_";
    my @thisline = $csv->fields();
    
    #Skip blanks where only the barcode is found
     next if (scalar(grep /./, @thisline) <= 1);
    
    my $ro = 12;
    my $to = 0;
    
    for(@colstoprint)
    {
	my $val = $thisline[$headings{$_}];
	$val = substr($val, 0, $val_length);
	my $label = $_;
	$label =~ s/[_ ]//g;
	$label = substr($label, 0, $label_length);
	
	push @cmds, qq{A$ro,$to,0,1,1,1,N,"${label}${label_sep}${val}"};

	$to += 12;
    }
    push @cmds, 'P1';
}

print "$_\n" for @cmds;

#w00t
