#!/usr/bin/fakeroot /bin/bash

# Constructs the Debian package.  Saves me faffing about with working out which files
# were modified.

#This is a good idea unless restoring your hosed system is your idea of fun.
set -u
#And this will pick up runtime problems
#set -e

#Although of course being real root is a silly idea and what I really want to do is
#just run this script under fakeroot.  TODO!

#Subroutine to collect all the files up
scrubfiles ()
{
    echo "Clearing out $WWWDIR and $CGIDIR"
    rm -rv $WWWDIR/* $CGIDIR/*

    echo "Clearing out $SHAREDDIR and $DOCDIR"
    rm -rv $SHAREDDIR/* $DOCDIR/*

}

#Run the file collector for the Deb package
CGIDIR=bio-linux-handlebar/usr/lib/cgi-bin/handlebar/
WWWDIR=bio-linux-handlebar/var/www/handlebar/
SHAREDDIR=bio-linux-handlebar/usr/share/handlebar/
DOCDIR=bio-linux-handlebar/usr/share/doc/handlebar/
scrubfiles

#And again for the regular tarball
CGIDIR=handlebar-src/cgi-bin/
WWWDIR=handlebar-src/www/
SHAREDDIR=handlebar-src/share/
DOCDIR=handlebar-src/doc/
scrubfiles

echo "Removing old .deb and tarball"
rm bio-linux-handlebar*.deb
rm handlebar.tar.gz bio-linux-handlebar.tar.gz

echo "All Doneski!"
