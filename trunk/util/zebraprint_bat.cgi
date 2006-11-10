#!/usr/bin/perl
use strict; use warnings;

# CVS $Revision: 1.2 $ committed on $Date: 2006/01/23 12:17:23 $ by $Author: tbooth $

# I made this a perl script to avoid worrying about the line endings in the script
# getting stuffed.  When called, this will simply generate the zebraprint.bat
# file, which is equivalent to the zebraprint wrapper for Linux:
# 
# | #!/bin/sh
# | exec lp -d barcoder "$@"

use CGI qw(header);

my $printername = "barcoder";

my $script = '
@echo off
REM ++ Basic batch wrapper to dump EPL to a Zebra printer
REM ++ Author: Tim Booth - tbooth@ceh.ac.uk, Jan 2006
REM ++
REM ++ Ye be warned - This assumes your Zebra is shared
REM ++ with the network name "barcoder".  If this is
REM ++ a problem you may need to for out for FRP ($24)
REM ++ or why not just switch to Linux.
REM ++ If you can find a better way to make this work
REM ++ then please let me know!
@echo on

copy /B %1 \\\\127.0.0.1\\' . "$printername
";

$script =~ s/\n/\015\012/gs;

print header( -type=>"application/x-msdos-program",
	      -content_disposition=>"attachment;filename=zebraprint.bat"),
      $script;
