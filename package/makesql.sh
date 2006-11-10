#!/bin/sh
# This script updates barcodebase.sql by reading the schema from the development
# database.  barcodebase.sql should contain the definitive SQL script to go in the package, ie.
# with the public user as www-data and the administrator as PostgreSQL, but this does not
# quite match my development setup, hence a bit of sed munging to do.
#
# If you are not Tim Booth and are trying to make the package building work, you
# are going to have to modify this script as it is not generic.  Good luck!
#
# If you are Tim Booth then Hi! You sure are one handsome and brainy dude!

# Passowrd hack if you need it.
# if [[ "x$PGPASSWORD" == 'x' ]] ; then
#     read -ers -p "Postgres password for "`whoami`":" PGPASSWORD
#     export PGPASSWORD
# fi

#Override apparent username of 'root' set by fakeroot
export PGUSER=$USER

set -e
set -u
OUTFILE=handlebar.sql

cat > $OUTFILE <<MSG
--
-- These are the SQL commands needed to setup the initial Barcodebase database.
-- This file will be loaded by the installation script if you opt for automatic
-- configuration, otherwise see the WIKI for details of configuration.
--
--  http://darwin.nerc-oxford.ac.uk/pgp-wiki/index.php/Barcode_deployer_guide
--

CREATE USER "www-data";
MSG
pg_dump -C --schema-only test_barcode \
    | sed -e 's/tbooth/postgres/;s/test_barcode/handlebar/' \
    >> $OUTFILE
pg_dump -R -dD --data-only -t barcode_description test_barcode \
    | sed -e 's/tbooth/postgres/' \
    >> $OUTFILE

pg_dump -R -dD --data-only -t query_def test_barcode \
    | sed -e 's/tbooth/postgres/' \
    >> $OUTFILE
pg_dump -R -dD --data-only -t query_param test_barcode \
    | sed -e 's/tbooth/postgres/' \
    >> $OUTFILE

# sed -i 's/\\connect - postgres/CREATE USER "www-data";/' $OUTFILE

echo DONE
