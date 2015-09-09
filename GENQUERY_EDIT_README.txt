Since I always forget how to do this, here's a note on editing the queries using
gq_edit.

See the various files in /home/tbooth/sandbox/genquery/new, and try:

export GENQUERY_CONF=/home/tbooth/sandbox/genquery/new/genquery_conf_somelocaldb.xml
export gq_0_db_name=nanofate_barcode

gq_edit list
