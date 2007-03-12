#!/usr/bin/perl
use strict; use warnings;

#All the standard CGI stuff...
use lib "..";
use barcodeUtil;

our %CONFIG = %{bcgetconfig()};
our $SVNCLIENT = 'usr/bin/svn';
our $SVNROOT = 'https://svn.sourceforge.net/svnroot/handlebar/trunk/type_repository';

my $q = bcgetqueryobj;

#Heading stuff
print bcheader(), bcstarthtml($title),
      $q->div({-id=>"topbanner"}, bch1($title)),
      $q->start_div({-id=>"mainsection"}),
      $result, "\n";

#get list of all the sql files
open "$SVNCLIENT ls $SVNROOT |";
my @types = sort(grep(/.sql$/, <$svnfiles>));

#compile them with a download link and a browse history link
for(@types)
{
	grab html (or put in an error)
	grab meta-data (who, when, when last, # of revs)

#Consider cache for efficiency.

#add a form to submit types by asking for the .sql file and mailing it to me
link to submit script here
