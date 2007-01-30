#!perl
use strict; use warnings;

package TableIO::sxc;
use base "TableIO::ods";
(our $VERSION = '2.$Revision$') =~ y/[0-9.]//cd;

#Get reader and writer from the base package
sub reader {goto &TableIO::base::reader};
sub writer {die "This class only reads.\n"};

use constant mime_type => "application/vnd.sun.xml.calc";
use constant file_extension => "sxc";

#First off, this package won't do writing, so fail immediately if we try any
#of that shenanigans.
sub start_write
{
    die "This class only reads.  Writing .sxc files is currently unsupported.\n";
}

#For the reader, defer everything to the base class, TableIO::ods
#And we're done!
