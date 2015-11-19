#!/bin/bash

# Constructs the Debian package.  Saves me faffing about with working out which files
# were modified.
# This bit is called from the makepackage.sh script under fakeroot to enable fixing
# of package file permissions.

#This is a good idea unless restoring your hosed system is your idea of fun.
set -u
#And this will pick up runtime problems
#set -e

#You must be root because we need to fudge permissions on the files
if [[ `id -u` != "0" ]] ; then
    echo "You are not root.  You need to be root or fakeroot."
    exit
fi

#Although of course being real root is a silly idea and what I really want to do is
#just run this script under fakeroot.  DONE!

#Subroutine to collect all the files up
collectfiles ()
{
    echo "Copying template and removing .snv gunk"
    rm -rvf ${BUILDDIR}
    cp -rv ${BUILDDIR}"_template" ${BUILDDIR}
    find ${BUILDDIR} -name '.svn' -print0 | xargs -0 rm -rvf

    mkdir -p $CGIDIR $SHAREDDIR $WWWDIR $DOCDIR

    echo "Putting *cgi *pm TableIO plugin in place"
    install -v -g root -o root -m644 ../*.pm $CGIDIR
    install -v -g root -o root ../*.cgi $CGIDIR
    install -vd -g root -o root $CGIDIR/TableIO
    install -v -g root -o root -m644 ../TableIO/*.pm $CGIDIR/TableIO
    install -vd -g root -o root $CGIDIR/plugin
    install -v -g root -o root -m644 ../plugin/*.pm $CGIDIR/plugin
    install -v -g root -o root -m755 ../plugin/*.cgi $CGIDIR/plugin
    install -v -g root -o root -m644 ../plugin/*.{htm,html,txt} $CGIDIR/plugin

    echo "Putting barcodes.conf master.conf.sample barcodes.footer.html labellogo40.pcx in place"
    install -v -g root -o root -m644 barcodes.footer.html labellogos/labellogo40.pcx $CGIDIR
    install -v -g root -o root -m644 ../barcodes.conf.sample $CGIDIR/barcodes.conf
    install -v -g root -o root -m644 ../master.conf.sample $CGIDIR/master.conf.sample
    echo "Putting alternative label logos in place"
    install -v -g root -o root -m644 labellogos/labellogo40_*.pcx $SHAREDDIR

    echo "Killing off bc.cgi symlink"
    rm $CGIDIR/bc.cgi

    echo "Putting in stylesheets"
    install -v -g root -o root -m644 bcstyle.css bcstyle_basic.css bcstyle_test.css \
	    webgraphics/gqbuttons.css $WWWDIR
    echo "Putting in graphics"
    install -v -g root -o root -m644 webgraphics/*.png webgraphics/*.gif $WWWDIR

    echo "Grabbing handlebar.sql"
#     echo "If you need to update this run makesql.sql"
    install -v -g root -o root -m644 handlebar.sql $SHAREDDIR
    echo "Putting in GenQuery templates"
    install -vd -g root -o root $SHAREDDIR/genquery
    install -v -g root -o root -m644 ../genquery/*.tmpl ../genquery/*.html $SHAREDDIR/genquery
    echo "Putting in template helper"
    install -vd -g root -o root $SHAREDDIR/typeio
    install -v -g root -o root -m755 ../type_repository/typeio.perl $SHAREDDIR/typeio

    echo "Putting in LICENSE, README, INSTALL, UPGRADE"
    install -v -g root -o root -m644 LICENSE* README* INSTALL* UPGRADE* $DOCDIR

    install -v -g root -o root -m644 doc/*.pdf $WWWDIR
    install -v -g root -o root -m644 doc/*.odt $DOCDIR

    echo "Renaming LICENSE to copyright as per Debian spec"
    mv $DOCDIR/LICENSE $DOCDIR/copyright
}

#Run the file collector for the Deb package
BUILDDIR=bio-linux-handlebar
CGIDIR=$BUILDDIR/usr/lib/cgi-bin/handlebar/
WWWDIR=$BUILDDIR/var/www/html/handlebar/
SHAREDDIR=$BUILDDIR/usr/share/handlebar/
DOCDIR=$BUILDDIR/usr/share/doc/handlebar/
collectfiles

#And again for the regular tarball
BUILDDIR=handlebar-src
CGIDIR=$BUILDDIR/cgi-bin/
WWWDIR=$BUILDDIR/www/
SHAREDDIR=$BUILDDIR/share/
DOCDIR=$BUILDDIR/doc/
collectfiles
ln -s request_barcodes.cgi $CGIDIR/bc.cgi

echo "Removing old .deb and tarball"
rm bio-linux-handlebar*.deb
rm handlebar.tar.gz bio-linux-handlebar.tar.gz

echo "Building .deb"
#TODO - why not just:
dpkg -b bio-linux-handlebar .
#vers=`perl -l -ne '/^Version: (.+)/ && print $1' bio-linux-handlebar/DEBIAN/control`
#dpkg -b bio-linux-handlebar "bio-linux-handlebar_${vers}_i386.deb"

echo "Setting ownership on .deb"
chown --reference=$0 bio-linux-handlebar*.deb

echo "Packing up tarball to go on Envgen for packaging"
tar --owner root --group root -cvzf bio-linux-handlebar.tar.gz bio-linux-handlebar
chown --reference=$0 bio-linux-handlebar.tar.gz

echo "Packing up tarball to go on Envgen for release"
tar --owner root --group root -cvzf handlebar.tar.gz handlebar-src
chown --reference=$0 bio-linux-handlebar.tar.gz
