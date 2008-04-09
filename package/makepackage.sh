#!/bin/bash

#Script to build all the packages etc. in one go.

echo Generating dump file... ; ./makesql.sh

#This only works on my machine.  If you don't have the macro/script set up
#then the PDFs need to be made manually.
echo "Building PDF help files in ./doc"
if [ -x /home/tbooth/perl/ooo2pdf.sh ] ; then
    rm doc/*.pdf
    /home/tbooth/perl/ooo2pdf.sh doc/user_guide.odt || exit 1
    /home/tbooth/perl/ooo2pdf.sh doc/deployer_guide.odt || exit 1 
fi

#Now go to the fakeroot bit
exec /usr/bin/fakeroot /bin/bash ./makepackage2.sh
