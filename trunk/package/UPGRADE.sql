-- UPGRADE_SQL, 4/6/2008, Tim Booth
--
-- Between Handlebar 1 and Handlebar 2.2, various modifications have entailed updates to the SQL
-- schema.  Some are due to Handlebar itself and others to the GenQuery system.
-- In chronological order, they were:
--
-- * Addition of query_def and query_param tables (for report maker to work)
-- * Addition of export_formats to query_def
-- * Addition of suppress_all to query_param
-- (The report system will not work without these fixes - in addition new reports have
-- been added which are needed by the collection system)
-- * Addition of barcode_link_index
-- (Without this, derived items will not show up in the query pages and
--  the public_query.cgi script will not work)
-- * Addition of barcode_collection and barcode_collection_item
-- (Needed for the new collection feature)
--
-- This script may be run to upgrade the database.  
--
-- Notes:
--
-- * If the database has been partially or fully upgraded already then it is still safe to run this 
--   script, and just the missing parts will be added.
-- * I'm assuming you already have the query_def and query_param tables.  If not, the SQL
--   to create them from scratch and add the default reports is found in handlebar.sql.  If you have not
--   added any custom reports I would suggest dropping the genquery schema entirely and re-creating it with 
--   that version.  Note that GenQuery now provides the gq_edit tool for manipulating the report queries loaded
--   into the system if you want to back things up.
-- * The barcode_link_index needs to be populated after it has been created.  This can be done from the Extra Admin
--   tab.  It is safe to recreate the index at any time but this should not be necessary after the first time.
-- * If you see a query_linkout table this is an artifact of an old GenQuery release and can be safely dropped.

SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = genquery, pg_catalog;

-- GenQuery fixes:

ALTER TABLE query_def ADD COLUMN export_formats text;

ALTER TABLE query_param ADD COLUMN suppress_all boolean;

-- New handy queries:

DELETE FROM query_param WHERE query_id IN
(SELECT query_id FROM query_def WHERE title IN (
    'Data Summary', 'Show Allocations', 'Show Collections'
));

DELETE FROM query_def WHERE title IN (
    'Data Summary', 'Show Allocations', 'Show Collections'
);

INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url, export_formats) 
VALUES (40, 'Data Summary', 'Show Data', 'Shows basic data entered about a range of codes', false, NULL, 
'Barcode;<linknoterms;<checkbox;Storage Location;Creation Date;Storage Date;Created By', 'select to_char(g.barcode, ''FM00-000000'') as bc
,''query_barcodes.cgi?bc='' || to_char(g.barcode, ''FM00-000000'') as link
        ,null as checkbox
,storage_location
,creation_date
,storage_date
,created_by
,g.comments
,d.datestamp as disposed
from generic g
left outer join barcode_deletion d on g.barcode = d.barcode
where true
$?FROMCODE{{ and
  $?TOCODE{{ g.barcode >= replace($FROMCODE, ''-'','''')::int8
  and g.barcode <= replace($TOCODE, ''-'','''')::int8 }}
  $!TOCODE{{ g.barcode = replace($FROMCODE, ''-'','''')::int8 }}
}}
$?FROMDATE{{ and
  $?TODATE{{ g.creation_date >= $FROMDATE::date
  and g.creation_date <= $TODATE::date }}
  $!TODATE{{ g.creation_date = $FROMDATE::date }}
}}
order by g.barcode', '://collect_barcodes.cgi?rm=pfc Create collection from selection', NULL);

INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url, export_formats) 
VALUES (20, 'Show Allocations', 'General Reports', 'Shows the blocks of codes allocated to users', false, NULL, 
'Username;<pivotquery;Item Type;<pivotquery;<hide;Size;Range;Used;Active;Disposed;Free;<hide;<hide;Comments;Date;Show Data;<pivotquery;Make Collection;<linknoterms', 
'select ba.username, ''Show Users'' as pivot,
replace( ba.typename, ''_'', '' '') as typename,
''Show Item Types'' as pivot2, 1 as showdisabled,
ba.tocode - ba.fromcode + 1 as size,
to_char(ba.fromcode, ''FM00-000000'') || '':'' ||
 to_char(ba.tocode, ''FM00-000000'') as range,
used,active, disposed,
(ba.tocode - ba.fromcode + 1 - active - disposed) as free,
ba.fromcode,
ba.tocode,
ba.comments, ba.datestamp,
case when used > 0 then ''View'' else '''' end as viewactive,
''Data Summary'' as pivot2,
''Collect'' as collect,
''collect_barcodes.cgi?rm=pfc;bc='' || to_char(ba.fromcode, ''FM00-000000'') || '':'' || to_char(ba.tocode, ''FM00-000000'') as link1
from barcode_allocation ba
inner join count_used_by_block us on us.fromcode = ba.fromcode
inner join count_active_by_block act on act.fromcode = ba.fromcode
inner join count_disposals_by_block dis on dis.fromcode = ba.fromcode
where true
$?USERNAME{{ and ba.username = $USERNAME }}
$?USER{{ and ba.username in (select username from barcode_user
         where realname = $USER ) }}
$?INST{{ and ba.username in (select username from barcode_user
         where institute = $INST ) }}
$?TYPE{{ and replace(ba.typename, ''_'', '' '') in ( $TYPE ) }}
$?CODE{{ and ba.fromcode <= replace($CODE, ''-'', '''')::int8
          and ba.tocode >= replace($CODE, ''-'', '''')::int8 }}
order by datestamp
$?MRF{{ desc }}', NULL, NULL);

INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url, export_formats) VALUES (80, 'Show Collections', 'Collections', 'Find barcode collections', false, NULL, 'Identifier;<linknoterms;Owner;Nickname;Created;Updated;Comments;Codes', 'select prefix || ''.'' || id,
        ''collect_barcodes.cgi?rm=edit;c='' || id,
        username, nickname, to_char(creation_timestamp, ''FMDDth Mon YYYY, HH24:MI'') as creation,
         to_char(modification_timestamp, ''FMDDth Mon YYYY, HH24:MI'') as modification,
         comments, count (i.*),
         case when publish_codes then ''P'' else '''' end ||
         case when publish_ancestors then ''+A'' else '''' end ||
         case when publish_descendants then ''+D'' else '''' end as publish
         from barcode_collection c left outer join barcode_collection_item i
         on i.collection_id = c.id
         where true
         $?USER{{ AND c.username = $USER }}
         $?CODE{{ AND c.id in
                        ( select collection_id from barcode_collection_item where barcode = replace($CODE,''-'','''')::int8 ) }}
         group by prefix, id, username, nickname, creation_timestamp, modification_timestamp, comments,
                  publish_codes, publish_ancestors, publish_descendants
         order by id', NULL, NULL);

INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 10, 'DROPDOWN', 'USER', 'Owner Real Name', '
select realname from barcode_user order by realname;
', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 20, 'DROPDOWN', 'INST', 'Institute', '
select distinct institute from barcode_user order by institute
', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 30, 'MULTI', 'TYPE', 'Item type', '
select distinct replace(typename, ''_'', '' '') as tn from barcode_allocation
', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 40, 'TEXT', 'CODE', 'A barcode within block', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 5, 'DROPDOWN', 'USERNAME', 'Owner Username', '
select username from barcode_user order by username;
', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 50, 'YESNO', 'MRF', 'Most recent first', NULL, NULL);

INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 10, 'TEXT', 'FROMCODE', 'Lowest c
ode', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 20, 'TEXT', 'TOCODE', 'Highest co
de', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 30, 'DATE', 'FROMDATE', 'From dat
e', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 40, 'DATE', 'TODATE', 'To date',
NULL, NULL);

INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (80, 1, 'DROPDOWN', 'USER', 'Username', 'select username from barcode_user order by username', false);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (80, 2, 'TEXT', 'CODE', 'Containing code', NULL, false);

SET search_path = public, pg_catalog;
SET search_path = handlebar_sys, public, pg_catalog;

-- '
-- New index table:

--
-- Name: barcode_link_index; Type: TABLE; Schema: handlebar_sys; Owner: postgres; Tablespace:
--

CREATE TABLE barcode_link_index (
    childtype character varying(30) NOT NULL,
    childcode bigint NOT NULL,
    columnname character varying(30) NOT NULL,
    parentcode bigint NOT NULL,
    external_id bigint
);


ALTER TABLE handlebar_sys.barcode_link_index OWNER TO postgres;


ALTER TABLE ONLY barcode_link_index
    ADD CONSTRAINT pk_link_index PRIMARY KEY (childcode, columnname);
CREATE INDEX idx_link_index_childcode ON barcode_link_index USING btree (childcode);
CREATE INDEX idx_link_index_parentcode ON barcode_link_index USING btree (parentcode);

REVOKE ALL ON TABLE barcode_link_index FROM PUBLIC;
REVOKE ALL ON TABLE barcode_link_index FROM postgres;
GRANT ALL ON TABLE barcode_link_index TO postgres;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE barcode_link_index TO "www-data";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE barcode_link_index TO "webuser";

-- New collections tables:

--
-- Name: barcode_collection; Type: TABLE; Schema: handlebar_sys; Owner: postgres; Tablespace:
--

CREATE TABLE barcode_collection (
    prefix character varying(20) NOT NULL,
    id integer NOT NULL,
    nickname character varying(20),
    username character varying(20) NOT NULL,
    comments text,
    creation_timestamp timestamp with time zone DEFAULT now() NOT NULL,
    modification_timestamp timestamp with time zone DEFAULT now() NOT NULL,
    publish_codes boolean DEFAULT false NOT NULL,
    publish_ancestors boolean DEFAULT false NOT NULL,
    publish_descendants boolean DEFAULT false NOT NULL
);

ALTER TABLE handlebar_sys.barcode_collection OWNER TO postgres;

--
-- Name: barcode_collection_item; Type: TABLE; Schema: handlebar_sys; Owner: postgres; Tablespace:
--

CREATE TABLE barcode_collection_item (
    collection_id integer NOT NULL,
    barcode bigint NOT NULL,
    rank bigint NOT NULL
);


ALTER TABLE handlebar_sys.barcode_collection_item OWNER TO postgres;

ALTER TABLE ONLY barcode_collection
    ADD CONSTRAINT barcode_collection_nickname_key UNIQUE (nickname);
ALTER TABLE ONLY barcode_collection
    ADD CONSTRAINT barcode_collection_pkey PRIMARY KEY (id);
ALTER TABLE ONLY barcode_collection_item
    ADD CONSTRAINT pk_barcode_collection_item PRIMARY KEY (collection_id, barcode);

CREATE INDEX idx_collection_item_barcode ON barcode_collection_item USING btree (barcode);
CREATE INDEX idx_collection_item_id ON barcode_collection_item USING btree (collection_id);

REVOKE ALL ON TABLE barcode_collection FROM PUBLIC;
REVOKE ALL ON TABLE barcode_collection FROM postgres;
GRANT ALL ON TABLE barcode_collection TO postgres;
GRANT ALL ON TABLE barcode_collection TO "www-data";
GRANT ALL ON TABLE barcode_collection TO "webuser";
REVOKE ALL ON TABLE barcode_collection_item FROM PUBLIC;
REVOKE ALL ON TABLE barcode_collection_item FROM postgres;
GRANT ALL ON TABLE barcode_collection_item TO postgres;
GRANT ALL ON TABLE barcode_collection_item TO "www-data";
GRANT ALL ON TABLE barcode_collection_item TO "webuser";

-- Et voila!
