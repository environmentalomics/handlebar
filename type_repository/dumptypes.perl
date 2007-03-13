#!/usr/bin/perl
#type_repository/dumptypes.perl - created Sat Feb 17 18:12:37 2007
 
use strict; 
use warnings;
use Data::Dumper;
use Getopt::Std;

# Iterate over all types in the database, and dump them out into specified dir.

my $usage = 
"dumptypes.perl [options] <target dir>
	options: -f(orce) = overwrite without prompt
			 -h(idden) = dump all the hidden types\n";

#Add flag to include/exclude hidden types.
#Need optarg to do that properly
our ($opt_f, $opt_h);
getopts('fh');

use lib "..";
use barcodeUtil;
use barcodeTypeExporter;

my $force = $opt_f;
$opt_h = $opt_h;

my $target_dir = shift(@ARGV) or die "Usage: $usage";
if(! -d $target_dir)
{
    if(!$force)
    {
		ask("Directory $target_dir does not exist.  Create it?") or exit 0;
    }
    mkdir $target_dir or die "Could not make directory $target_dir";
}

barcodeUtil::connectnow();

#get types
#sort list (no need - already sorted)
my @alltypes = @{bcgetbctypes()};

#Find hidden/non-hidden
@alltypes = grep {!$opt_h xor bcgetflagsforfield($_)->{hide}} @alltypes;

#for each
for my $atype (@alltypes)
{
	#check .sql
	#check .desc
	for my $targetfile ( "$target_dir/$atype.sql",  "$target_dir/$atype.html" )
	{
		if( -e $targetfile )
		{
			if($force)
			{
				unlink($targetfile) or die "unlink error on $targetfile";
			}
			else
			{
				die "Will not overwrite existing file $targetfile.\n";
			}
		}
	}

	my $outfh;
	#dump .sql
	open $outfh, ">$target_dir/$atype.sql" or die "!";
	print $outfh dump_sql($atype);
	close $outfh;

	#dump .desc
	open $outfh, ">$target_dir/$atype.html" or die "!!";
	print $outfh dump_desc($atype);
	close $outfh;
	
	#report dumped type
	print "Exported SQL and description for $atype.\n";
}
#report nn types dumped to dir
print "DONE - Total of ". scalar(@alltypes) ." tables exported.\n";

sub ask
{
    my $question = shift;
    my $answer = '';

    while(1)
    {
	print $question . ' ';
	$answer = <STDIN>;

	if($answer =~ /[yYnN]/) { last }
	else { print "Answer yes or no, you crazy fool!\n" }
    }
    $answer !~ /[nN]/; #This means that yn comes out as false
}
