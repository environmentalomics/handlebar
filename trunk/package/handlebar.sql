--
-- These are the SQL commands needed to setup the initial Barcodebase database.
-- This file will be loaded by the installation script if you opt for automatic
-- configuration, otherwise see the WIKI for details of configuration.
--
--  http://darwin.nerc-oxford.ac.uk/pgp-wiki/index.php/Barcode_deployer_guide
--

CREATE USER "www-data";
--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 2 (OID 0)
-- Name: handlebar; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE handlebar WITH TEMPLATE = template0 ENCODING = 'UNICODE';


\connect handlebar postgres

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET SESSION AUTHORIZATION DEFAULT;

--
-- TOC entry 7 (OID 4560873)
-- Name: handlebar_data; Type: SCHEMA; Schema: -; Owner: 
--

CREATE SCHEMA handlebar_data AUTHORIZATION postgres;


--
-- TOC entry 9 (OID 4560874)
-- Name: handlebar_sys; Type: SCHEMA; Schema: -; Owner: 
--

CREATE SCHEMA handlebar_sys AUTHORIZATION postgres;


--
-- TOC entry 3 (OID 4560875)
-- Name: genquery; Type: SCHEMA; Schema: -; Owner: 
--

CREATE SCHEMA genquery AUTHORIZATION postgres;


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 6 (OID 2200)
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 8 (OID 4560873)
-- Name: handlebar_data; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA handlebar_data FROM PUBLIC;
GRANT USAGE ON SCHEMA handlebar_data TO PUBLIC;


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 10 (OID 4560874)
-- Name: handlebar_sys; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA handlebar_sys FROM PUBLIC;
GRANT USAGE ON SCHEMA handlebar_sys TO PUBLIC;


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 4 (OID 4560875)
-- Name: genquery; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA genquery FROM PUBLIC;
GRANT USAGE ON SCHEMA genquery TO PUBLIC;


SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_sys, pg_catalog;

--
-- TOC entry 11 (OID 4560876)
-- Name: barcode_user; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_user (
    username character varying(20) NOT NULL,
    realname text,
    institute text,
    email text
);


--
-- TOC entry 12 (OID 4560876)
-- Name: barcode_user; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_user FROM PUBLIC;
GRANT INSERT,SELECT,UPDATE ON TABLE barcode_user TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 13 (OID 4560881)
-- Name: barcode_allocation; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_allocation (
    username character varying(20) NOT NULL,
    typename character varying(30) NOT NULL,
    fromcode bigint NOT NULL,
    tocode bigint NOT NULL,
    datestamp date DEFAULT ('now'::text)::date NOT NULL,
    comments text
);


--
-- TOC entry 14 (OID 4560881)
-- Name: barcode_allocation; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_allocation FROM PUBLIC;
GRANT ALL ON TABLE barcode_allocation TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 15 (OID 4560887)
-- Name: barcode_description; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_description (
    typename character varying(30) NOT NULL,
    columnname character varying(30) NOT NULL,
    notes text
);


--
-- TOC entry 16 (OID 4560887)
-- Name: barcode_description; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_description FROM PUBLIC;
GRANT SELECT ON TABLE barcode_description TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 17 (OID 4560892)
-- Name: barcode_deletion; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_deletion (
    barcode bigint NOT NULL,
    datestamp date DEFAULT ('now'::text)::date NOT NULL,
    comments text
) WITHOUT OIDS;


--
-- TOC entry 18 (OID 4560892)
-- Name: barcode_deletion; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_deletion FROM PUBLIC;
GRANT INSERT,SELECT,DELETE ON TABLE barcode_deletion TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_data, pg_catalog;

--
-- TOC entry 19 (OID 4560898)
-- Name: generic; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE generic (
    barcode bigint NOT NULL,
    auto_timestamp timestamp without time zone DEFAULT now() NOT NULL,
    storage_location character varying(128) NOT NULL,
    creation_date date NOT NULL,
    storage_date date,
    created_by character varying(32) NOT NULL,
    comments text
);


--
-- TOC entry 20 (OID 4560898)
-- Name: generic; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE generic FROM PUBLIC;
GRANT ALL ON TABLE generic TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 21 (OID 4560904)
-- Name: pcr_products; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE pcr_products (
    barcode bigint,
    forward_primer character varying(64) NOT NULL,
    reverse_primer character varying(64) NOT NULL,
    source_nucleic_acid character varying(64),
    source_nucleic_acid_barcode bigint,
    target_gene text NOT NULL
)
INHERITS (generic);


--
-- TOC entry 22 (OID 4560904)
-- Name: pcr_products; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE pcr_products FROM PUBLIC;
GRANT ALL ON TABLE pcr_products TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 23 (OID 4560916)
-- Name: biofilm_sample; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE biofilm_sample (
    barcode bigint,
    site_latitude double precision NOT NULL,
    site_longitude double precision NOT NULL,
    substrate character varying(20) NOT NULL,
    sample_site_code character varying(20),
    time_of_day character varying(5),
    CONSTRAINT time_of_day_format CHECK (((time_of_day)::text ~ '^[0-9][0-9]:[0-9][0-9]$'::text))
)
INHERITS (generic);


--
-- TOC entry 24 (OID 4560916)
-- Name: biofilm_sample; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE biofilm_sample FROM PUBLIC;
GRANT ALL ON TABLE biofilm_sample TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 25 (OID 4560922)
-- Name: fish_individual; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE fish_individual (
    barcode bigint,
    storage_location character varying(128),
    creation_date date,
    storage_date date,
    created_by character varying(32),
    comments text,
    fish_id character varying(20) NOT NULL,
    species character varying(64) NOT NULL,
    institute character varying(64),
    location_name character varying(64),
    latitude double precision,
    longitude double precision,
    phase smallint NOT NULL,
    treatment text NOT NULL,
    treatment_duration integer,
    sex character varying(1) NOT NULL,
    CONSTRAINT fish_sex_m_or_f CHECK ((((sex)::text = 'm'::text) OR ((sex)::text = 'f'::text)))
)
INHERITS (generic);


--
-- TOC entry 26 (OID 4560922)
-- Name: fish_individual; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE fish_individual FROM PUBLIC;
GRANT ALL ON TABLE fish_individual TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 27 (OID 4560929)
-- Name: transformation_mix; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE transformation_mix (
    barcode bigint,
    storage_location character varying(128),
    creation_date date,
    storage_date date,
    created_by character varying(32),
    comments text,
    source_dna text,
    source_dna_barcode bigint,
    host_strain character varying(64) NOT NULL,
    vector character varying(64) NOT NULL,
    resistance character varying(64) NOT NULL,
    storage_method character varying(64) NOT NULL
)
INHERITS (generic);


--
-- TOC entry 28 (OID 4560929)
-- Name: transformation_mix; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE transformation_mix FROM PUBLIC;
GRANT ALL ON TABLE transformation_mix TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 29 (OID 4560953)
-- Name: soil_sample; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE soil_sample (
    barcode bigint,
    storage_location character varying(128),
    creation_date date,
    storage_date date,
    created_by character varying(32),
    comments text,
    site_latitude double precision NOT NULL,
    site_longitude double precision NOT NULL,
    depth_in_cm real NOT NULL,
    sample_site_code character varying(20),
    time_of_day character varying(5),
    CONSTRAINT time_of_day_format CHECK (((time_of_day)::text ~ '^[0-9][0-9]:[0-9][0-9]$'::text))
)
INHERITS (generic);


--
-- TOC entry 30 (OID 4560953)
-- Name: soil_sample; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE soil_sample FROM PUBLIC;
GRANT ALL ON TABLE soil_sample TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 31 (OID 4560965)
-- Name: subclone_plate; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE subclone_plate (
    barcode bigint,
    storage_location character varying(128),
    creation_date date,
    storage_date date,
    created_by character varying(32),
    comments text,
    source_plate text,
    source_plate_barcode bigint,
    source_well_number character varying(3),
    host_strain character varying(64) NOT NULL,
    vector character varying(64) NOT NULL,
    resistance character varying(64) NOT NULL,
    storage_method character varying(64) NOT NULL,
    CONSTRAINT foocheck CHECK ((length((vector)::text) < 10))
)
INHERITS (generic);


--
-- TOC entry 32 (OID 4560965)
-- Name: subclone_plate; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE subclone_plate FROM PUBLIC;
GRANT ALL ON TABLE subclone_plate TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 33 (OID 4560971)
-- Name: sediment_sample; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE sediment_sample (
    barcode bigint,
    storage_location character varying(128),
    creation_date date,
    storage_date date,
    created_by character varying(32),
    comments text,
    site_latitude double precision NOT NULL,
    site_longitude double precision NOT NULL,
    substrate character varying(20),
    depth_in_cm real,
    sample_site_code character varying(20),
    time_of_day character varying(5),
    CONSTRAINT time_of_day_format CHECK (((time_of_day)::text ~ '^[0-9][0-9]:[0-9][0-9]$'::text))
)
INHERITS (generic);


--
-- TOC entry 34 (OID 4560971)
-- Name: sediment_sample; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE sediment_sample FROM PUBLIC;
GRANT ALL ON TABLE sediment_sample TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 35 (OID 4560977)
-- Name: library_plate; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE library_plate (
    barcode bigint,
    library character varying(64) NOT NULL,
    library_type character varying(16) NOT NULL,
    host_strain character varying(64) NOT NULL,
    vector character varying(64) NOT NULL,
    resistance character varying(64) NOT NULL,
    source_mix_barcode bigint,
    source_mix text,
    storage_method character varying(64),
    CONSTRAINT check_sane_barcode CHECK ((source_mix_barcode < 2000000))
)
INHERITS (generic);


--
-- TOC entry 36 (OID 4560977)
-- Name: library_plate; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE library_plate FROM PUBLIC;
GRANT ALL ON TABLE library_plate TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

SET search_path = genquery, pg_catalog;

--
-- TOC entry 37 (OID 4560984)
-- Name: query_def; Type: TABLE; Schema: genquery; Owner: postgres
--

CREATE TABLE query_def (
    query_id integer NOT NULL,
    title character varying(80) NOT NULL,
    category character varying(80) NOT NULL,
    long_label text,
    hide boolean DEFAULT false NOT NULL,
    icon_index integer,
    column_head text,
    query_body text,
    query_url text
) WITHOUT OIDS;


--
-- TOC entry 38 (OID 4560984)
-- Name: query_def; Type: ACL; Schema: genquery; Owner: postgres
--

REVOKE ALL ON TABLE query_def FROM PUBLIC;
GRANT SELECT ON TABLE query_def TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 39 (OID 4560990)
-- Name: query_param; Type: TABLE; Schema: genquery; Owner: postgres
--

CREATE TABLE query_param (
    query_id integer NOT NULL,
    param_no integer NOT NULL,
    param_type character varying(10) NOT NULL,
    param_name character varying(20),
    param_text text,
    menu_query text,
    suppress_all boolean
) WITHOUT OIDS;


--
-- TOC entry 40 (OID 4560990)
-- Name: query_param; Type: ACL; Schema: genquery; Owner: postgres
--

REVOKE ALL ON TABLE query_param FROM PUBLIC;
GRANT SELECT ON TABLE query_param TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 41 (OID 4560997)
-- Name: count_used_by_block; Type: VIEW; Schema: genquery; Owner: postgres
--

CREATE VIEW count_used_by_block AS
    SELECT fromcode, count(g.barcode) AS used FROM (handlebar_sys.barcode_allocation ba LEFT JOIN handlebar_data.generic g ON (((g.barcode >= ba.fromcode) AND (g.barcode <= ba.tocode)))) GROUP BY username, fromcode;


--
-- TOC entry 42 (OID 4560997)
-- Name: count_used_by_block; Type: ACL; Schema: genquery; Owner: postgres
--

REVOKE ALL ON TABLE count_used_by_block FROM PUBLIC;
GRANT SELECT ON TABLE count_used_by_block TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 43 (OID 4561000)
-- Name: count_disposals_by_block; Type: VIEW; Schema: genquery; Owner: postgres
--

CREATE VIEW count_disposals_by_block AS
    SELECT fromcode, count(d.barcode) AS disposed FROM (handlebar_sys.barcode_allocation ba LEFT JOIN handlebar_sys.barcode_deletion d ON (((d.barcode >= ba.fromcode) AND (d.barcode <= ba.tocode)))) GROUP BY username, fromcode;


--
-- TOC entry 44 (OID 4561000)
-- Name: count_disposals_by_block; Type: ACL; Schema: genquery; Owner: postgres
--

REVOKE ALL ON TABLE count_disposals_by_block FROM PUBLIC;
GRANT SELECT ON TABLE count_disposals_by_block TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 45 (OID 4561003)
-- Name: count_active_by_block; Type: VIEW; Schema: genquery; Owner: postgres
--

CREATE VIEW count_active_by_block AS
    SELECT fromcode, count(g.barcode) AS active FROM (handlebar_sys.barcode_allocation ba LEFT JOIN handlebar_data.generic g ON ((((g.barcode >= ba.fromcode) AND (g.barcode <= ba.tocode)) AND (NOT (EXISTS (SELECT d.barcode FROM handlebar_sys.barcode_deletion d WHERE (d.barcode = g.barcode))))))) GROUP BY username, fromcode;


--
-- TOC entry 46 (OID 4561003)
-- Name: count_active_by_block; Type: ACL; Schema: genquery; Owner: postgres
--

REVOKE ALL ON TABLE count_active_by_block FROM PUBLIC;
GRANT SELECT ON TABLE count_active_by_block TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_data, pg_catalog;

--
-- TOC entry 47 (OID 4562221)
-- Name: water_sample; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE water_sample (
    barcode bigint,
    volume_filtered real,
    site_latitude double precision NOT NULL,
    site_longitude double precision NOT NULL,
    depth_in_m real NOT NULL,
    filter_type character varying(20) NOT NULL,
    filter_number integer NOT NULL,
    prefilter character varying(20),
    post_filtering_treatment character varying(128),
    sample_site_code character varying(20),
    time_of_day character varying(5),
    CONSTRAINT time_of_day_format CHECK (((time_of_day)::text ~ '^[0-9][0-9]:[0-9][0-9]$'::text))
)
INHERITS (generic);


--
-- TOC entry 48 (OID 4562221)
-- Name: water_sample; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE water_sample FROM PUBLIC;
GRANT INSERT,SELECT,UPDATE,DELETE ON TABLE water_sample TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 49 (OID 4562260)
-- Name: nucleic_acid_extracts; Type: TABLE; Schema: handlebar_data; Owner: postgres
--

CREATE TABLE nucleic_acid_extracts (
    barcode bigint,
    sample_barcode bigint NOT NULL,
    volume real NOT NULL,
    concentration real
)
INHERITS (generic);


--
-- TOC entry 50 (OID 4562260)
-- Name: nucleic_acid_extracts; Type: ACL; Schema: handlebar_data; Owner: postgres
--

REVOKE ALL ON TABLE nucleic_acid_extracts FROM PUBLIC;
GRANT ALL ON TABLE nucleic_acid_extracts TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_sys, pg_catalog;

--
-- TOC entry 51 (OID 4573812)
-- Name: barcode_collection; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_collection (
    prefix character varying(20) NOT NULL,
    id integer NOT NULL,
    nickname character varying(20),
    username character varying(20) NOT NULL,
    comments text,
    creation_datestamp date DEFAULT ('now'::text)::date NOT NULL,
    modification_datestamp date DEFAULT ('now'::text)::date NOT NULL
);


--
-- TOC entry 52 (OID 4573812)
-- Name: barcode_collection; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_collection FROM PUBLIC;
GRANT ALL ON TABLE barcode_collection TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 53 (OID 4573827)
-- Name: barcode_collection_item; Type: TABLE; Schema: handlebar_sys; Owner: postgres
--

CREATE TABLE barcode_collection_item (
    collection_id integer NOT NULL,
    barcode bigint NOT NULL,
    rank bigint NOT NULL
);


--
-- TOC entry 54 (OID 4573827)
-- Name: barcode_collection_item; Type: ACL; Schema: handlebar_sys; Owner: postgres
--

REVOKE ALL ON TABLE barcode_collection_item FROM PUBLIC;
GRANT ALL ON TABLE barcode_collection_item TO "www-data";


SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_data, pg_catalog;

--
-- TOC entry 79 (OID 4574292)
-- Name: array_accum(anyelement); Type: AGGREGATE; Schema: handlebar_data; Owner: postgres
--

CREATE AGGREGATE array_accum (
    BASETYPE = anyelement,
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
);


SET search_path = genquery, pg_catalog;

--
-- TOC entry 55 (OID 4574864)
-- Name: query_linkout; Type: TABLE; Schema: genquery; Owner: postgres
--

CREATE TABLE query_linkout (
    query_id integer NOT NULL,
    url text NOT NULL,
    label text,
    name character varying(20) NOT NULL,
    key_column character varying(20) NOT NULL,
    pack boolean DEFAULT false NOT NULL
) WITHOUT OIDS;


SET search_path = handlebar_sys, pg_catalog;

--
-- TOC entry 57 (OID 4561150)
-- Name: allocation_name_idx; Type: INDEX; Schema: handlebar_sys; Owner: postgres
--

CREATE INDEX allocation_name_idx ON barcode_allocation USING btree (username);


--
-- TOC entry 56 (OID 4561151)
-- Name: barcode_user_pkey; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_user
    ADD CONSTRAINT barcode_user_pkey PRIMARY KEY (username);


--
-- TOC entry 58 (OID 4561153)
-- Name: barcode_allocation_fromcode_key; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_allocation
    ADD CONSTRAINT barcode_allocation_fromcode_key UNIQUE (fromcode);


--
-- TOC entry 59 (OID 4561155)
-- Name: barcode_allocation_tocode_key; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_allocation
    ADD CONSTRAINT barcode_allocation_tocode_key UNIQUE (tocode);


--
-- TOC entry 60 (OID 4561157)
-- Name: pk_barcode_description; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_description
    ADD CONSTRAINT pk_barcode_description PRIMARY KEY (typename, columnname);


--
-- TOC entry 61 (OID 4561159)
-- Name: barcode_deletion_pk; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_deletion
    ADD CONSTRAINT barcode_deletion_pk PRIMARY KEY (barcode);


SET search_path = handlebar_data, pg_catalog;

--
-- TOC entry 62 (OID 4561161)
-- Name: pk_generic; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY generic
    ADD CONSTRAINT pk_generic PRIMARY KEY (barcode);


--
-- TOC entry 63 (OID 4561165)
-- Name: pk_pcr_products; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY pcr_products
    ADD CONSTRAINT pk_pcr_products PRIMARY KEY (barcode);


--
-- TOC entry 64 (OID 4561167)
-- Name: biofilm_sample_pkey; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY biofilm_sample
    ADD CONSTRAINT biofilm_sample_pkey PRIMARY KEY (barcode);


--
-- TOC entry 65 (OID 4561169)
-- Name: fish_sample_pkey; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY fish_individual
    ADD CONSTRAINT fish_sample_pkey PRIMARY KEY (barcode);


--
-- TOC entry 66 (OID 4561171)
-- Name: pk_transformation_mix; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY transformation_mix
    ADD CONSTRAINT pk_transformation_mix PRIMARY KEY (barcode);


--
-- TOC entry 67 (OID 4561179)
-- Name: soil_sample_pkey; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY soil_sample
    ADD CONSTRAINT soil_sample_pkey PRIMARY KEY (barcode);


--
-- TOC entry 68 (OID 4561183)
-- Name: pk_subclone_plate; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY subclone_plate
    ADD CONSTRAINT pk_subclone_plate PRIMARY KEY (barcode);


--
-- TOC entry 69 (OID 4561185)
-- Name: sediment_sample_pkey; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY sediment_sample
    ADD CONSTRAINT sediment_sample_pkey PRIMARY KEY (barcode);


--
-- TOC entry 70 (OID 4561187)
-- Name: pk_library_plate; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY library_plate
    ADD CONSTRAINT pk_library_plate PRIMARY KEY (barcode);


SET search_path = genquery, pg_catalog;

--
-- TOC entry 71 (OID 4561189)
-- Name: pk_query_def; Type: CONSTRAINT; Schema: genquery; Owner: postgres
--

ALTER TABLE ONLY query_def
    ADD CONSTRAINT pk_query_def PRIMARY KEY (query_id);


--
-- TOC entry 72 (OID 4561191)
-- Name: pk_query_param; Type: CONSTRAINT; Schema: genquery; Owner: postgres
--

ALTER TABLE ONLY query_param
    ADD CONSTRAINT pk_query_param PRIMARY KEY (query_id, param_no);


SET search_path = handlebar_data, pg_catalog;

--
-- TOC entry 73 (OID 4562239)
-- Name: pk_water_sample; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY water_sample
    ADD CONSTRAINT pk_water_sample PRIMARY KEY (barcode);


--
-- TOC entry 74 (OID 4562266)
-- Name: pk_nucleic_acid_extracts; Type: CONSTRAINT; Schema: handlebar_data; Owner: postgres
--

ALTER TABLE ONLY nucleic_acid_extracts
    ADD CONSTRAINT pk_nucleic_acid_extracts PRIMARY KEY (barcode);


SET search_path = handlebar_sys, pg_catalog;

--
-- TOC entry 76 (OID 4573819)
-- Name: barcode_collection_pkey; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_collection
    ADD CONSTRAINT barcode_collection_pkey PRIMARY KEY (id);


--
-- TOC entry 75 (OID 4573821)
-- Name: barcode_collection_nickname_key; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_collection
    ADD CONSTRAINT barcode_collection_nickname_key UNIQUE (nickname);


--
-- TOC entry 77 (OID 4573829)
-- Name: pk_barcode_collection_item; Type: CONSTRAINT; Schema: handlebar_sys; Owner: postgres
--

ALTER TABLE ONLY barcode_collection_item
    ADD CONSTRAINT pk_barcode_collection_item PRIMARY KEY (collection_id, barcode);


SET search_path = genquery, pg_catalog;

--
-- TOC entry 78 (OID 4574870)
-- Name: pk_query_linkout; Type: CONSTRAINT; Schema: genquery; Owner: postgres
--

ALTER TABLE ONLY query_linkout
    ADD CONSTRAINT pk_query_linkout PRIMARY KEY (query_id, name);


SET SESSION AUTHORIZATION 'postgres';

--
-- TOC entry 5 (OID 2200)
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'Standard public schema';


--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET SESSION AUTHORIZATION 'postgres';

SET search_path = handlebar_sys, pg_catalog;

--
-- Data for TOC entry 2 (OID 4560887)
-- Name: barcode_description; Type: TABLE DATA; Schema: handlebar_sys; Owner: postgres
--

INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'auto_timestamp', 'Timestamp for last upload of this record');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', '*auto_timestamp', 'noexport');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'created_by', 'Name of person who created this item');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'comments', 'Optional free text for any extra information relating to the item');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', '*comments', 'demote');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('library_plate', '-', 'A 96-well plate comprising part of a clone library.  Each plate links back to a single source transformation mix.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_sample', 'location_name', 'You can give either the name or the latitute/longitude or both');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_sample', '-', 'Fish sample defined by Jon Ball.  There will be multiple samples per fish.  In my notes there is no space for tissue type (fin clipping, liver, etc) - should that be added?');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'storage_location', 'Where the sample is stored');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_sample', 'sex', 'You must enter ''m'' or ''f''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_sample', 'fish_id', 'are these a standard length?  I guessed at allowing up to 20 chars.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('nucleic_acid_extracts', '-', 'Extracts link back to the original sample');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('pcr_products', '*-', NULL);
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('subclone_plate', '*-', NULL);
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('subclone_plate', 'source_well_number', 'The well on the source plate.  Eg "C5"');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('generic', '*-', 'hide');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'storage_date', 'Optional date on which the sample went into storage');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'creation_date', 'Date on which the item was collected or prepared.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'site_latitude', 'In degrees as a decimal fraction');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'site_longitude', 'In degrees as a decimal fraction');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('biofilm_sample', 'substrate', 'Type of material biofilm was attached to when collected: e.g. algae, sand, rock');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('generic', '-', 'This is the base type for all the other barcode types in the system, and encapsulates the minumim information for any stored sample.  
');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'host_strain', 'Bacterial host strain: e.g. ''DH5a'', ''XL1''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'resistance', 'Antibiotic resistance markers present on the vector or host chromosome:
e.g. ampicillin, tetracycline');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'storage_method', 'Method used for storage of cells, including temperature: e.g. ''10%
glycerol at -80C'', ''7% DMSO at -80C''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('pcr_products', 'target_gene', 'Gene to which PCR primers were targeted: e.g. ''16S rDNA'', ''amyA'', ''nifH''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('soil_sample', 'depth_in_cm', 'Depth of soil core from from surface, in centimetres');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'fish_id', NULL);
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('sediment_sample', 'depth_in_cm', 'Depth from sediment/water interface in centimetres.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('biofilm_sample', '-', 'A type suitable for any biofilm - eg. from a coastal environment.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('sediment_sample', 'substrate', 'The main constituent material of the sediment: e.g. sand, clay, loam, peat combined with terms like acidic or alkaline.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', '-', 'A single fish.  There may be multiple tissue samples related to each fish.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'vector', 'Vector containing the insert: e.g. ''pEpiFOS-5'', ''pCC1BAC'', ''pUC18''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'location_name', 'You can give either the name or the latitute/longitude or both');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'sex', 'You must enter ''m'' or ''f''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'latitude', 'In degrees, as a decimal fraction');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'longitude', 'In degrees, as a decimal fraction');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'treatment', 'Treatment to which fish was exposed, or ''none''');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('fish_individual', 'treatment_duration', 'In days, if applicable');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('library_plate', 'library', 'A name used to identify the library to which this plate belongs.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('library_plate', 'library_type', 'The type of the library - eg Fosmid.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('library_plate', '*source_mix_barcode', 'bc');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('library_plate', 'source_mix', 'Used to identify the mix if it is not a barcoded item');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('pcr_products', '*source_nucleic_acid_barcode', 'bc');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('soil_sample', '-', 'Any sample of soil');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('subclone_plate', '*source_plate_barcode', 'bc');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'volume_filtered', 'in litres');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'depth_in_m', 'Sampling depth in metres.  Surface samples should be recorded at 0.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', '-', 'A sample of water which may be stored as liquid or else has been passed through a filter which is then kept.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'filter_number', 'Number of filters or bottles in this set.  If the samples are not identical then they should have separate barcodes');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('transformation_mix', '*-', NULL);
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('transformation_mix', '*source_dna_barcode', 'bc');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'filter_type', 'Collection filter used, with pore size: e.g. Sterivex 0.22m, GF/A 1.6m - or else Bottle if the water was just bottled');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'prefilter', 'If used, the prefilter applied to the sample before filtering proper');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('water_sample', 'post_filtering_treatment', 'Action taken to stabilise or otherwise treat the sample: e.g. Snap frozen,Lugol,RNAlater');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('nucleic_acid_extracts', 'volume', 'in µl');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('nucleic_acid_extracts', 'concentration', 'Spectrophotometric, fluorescence or gel quantitation of nucleic acid
concentration in ng/µl.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('nucleic_acid_extracts', '*sample_barcode', 'bc');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'sample_site_code', 'Identification of the exact sample site.  If the study area has been gridded out, for example, then give the grid location here.');
INSERT INTO barcode_description (typename, columnname, notes) VALUES ('-', 'time_of_day', 'If it is important to identify the time of day as well as the collection date then do so here.  Format must be hh:mm in 24-hour clock');


--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET SESSION AUTHORIZATION 'postgres';

SET search_path = genquery, pg_catalog;

--
-- Data for TOC entry 2 (OID 4560984)
-- Name: query_def; Type: TABLE DATA; Schema: genquery; Owner: postgres
--

INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (40, 'Data Summary', 'Show Data', 'Shows basic data entered about a range of codes', false, NULL, 'Barcode;<linknoterms;Storage Location;Creation Date;Storage Date;Created By', 'select to_char(g.barcode, ''FM00-000000'')
,''query_barcodes.cgi?bc='' || to_char(g.barcode, ''FM00-000000'') as link
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
', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (5, 'Show Database Statistics', 'General Reports', 'Show overall info on the database', false, NULL, '<hide;Stat;Value', 'select 1 as row, ''Registered Users'' as stat, count(*) as val from barcode_user
union
select 2 as row, ''Barcode Types'' as stat, count(*) as val from pg_tables
where schemaname = ''handlebar_data'' and tablename::varchar not in (
 select typename from barcode_description where
 columnname = ''*-'' and notes like ''%hide%'')
union
select 3 as row, ''Total Allocations'' as stat, sum(tocode - fromcode + 1) as val from barcode_allocation
union
select 4 as row, ''Total Used Codes'' as stat, sum(used) as val from count_used_by_block
union
select 5 as row, ''Total Active Codes'' as stat, sum(active) as val from count_active_by_block
union
select 6 as row, ''Items added in last 30 days'' as stat, count(*) from generic
 where coalesce(storage_date, creation_date) >= current_date - interval ''30 days''
order by row', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (150, 'Custom Query', 'Advanced', 'Type any SQL query', false, NULL, NULL, '$_PARAM1', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (15, 'Show Item Types', 'General Reports', 'Summarise the types of thing known to the database', false, NULL, 'Type;Notes;Allocated;Codes in Use;Disabled;Details;<linknoterms', 'select replace(tablename::varchar, ''_'', '' '')
,bd.notes 
,coalesce(sum(ba.tocode - ba.fromcode + 1), 0) as allocated
,coalesce(sum(cab.active), 0) as active
,case when coalesce(bd2.notes like ''%hide%'', false) 
 then ''yes'' else '''' end
as hidden
,''View definition'' as label
,''request_barcodes.cgi?typespopup=1#'' || tablename::varchar
from pg_tables 
left outer join barcode_description bd 
on tablename::varchar = bd.typename 
and bd.columnname = ''-'' 
left outer join barcode_description bd2 
on bd2.columnname = ''*-'' 
and tablename::varchar = bd2.typename
left outer join (barcode_allocation ba 
inner join genquery.count_active_by_block cab on cab.fromcode = ba.fromcode)
on tablename::varchar = ba.typename 
where schemaname = ''handlebar_data''
$?TYPENAME{{ and tablename::varchar = replace( $TYPENAME , '' '',''_'') }}
$!SHOWDISABLED{{ and not coalesce(bd2.notes like ''%hide%'', false) }}
group by tablename, bd.notes, bd2.notes
order by tablename', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (50, 'Describe Sequencing Plate', 'Type-specific Reports', 'Custom query for sequencing extracts.
Supply the first barcode on the plate (ie. the plate label) to see a summary of the contents of the wells.', false, NULL, NULL, 'select
to_char($BASECODE::int8, ''FM00-000000'') as plate_label,
substring(''ABCDEFGH'', (((se.barcode - $BASECODE) % 8) + 1)::int, 1) ||
(se.barcode - $BASECODE) / 8 + 1 as well,
to_char(se.barcode, ''FM00-000000'') as well_barcode,
to_char(nae.sample_barcode, ''FM00-000000'') as sample_barcode,
replace(pgc.relname, ''_'', '' '') as sample_type,
se.storage_location,
se.creation_date,
se.storage_date,
se.created_by,
to_char(se.library_plate_barcode, ''FM00-000000''),
se.library_plate_well,
se.plasmid_preparation,
se.comments
from sequencing_extract se 
left outer join data.library_plate lp on
  lp.barcode = se.library_plate_barcode
left outer join data.transformation_mix tm on
  tm.barcode = lp.source_mix_barcode
left outer join data.nucleic_acid_extracts nae on
  nae.barcode = tm.source_dna_barcode
left outer join (data.generic g inner join pg_class pgc
    on g.tableoid = pgc.oid
) on g.barcode = nae.sample_barcode
where se.barcode >= $BASECODE::int8
and se.barcode < $BASECODE::int8 + 96', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (16, 'All Type Definitions', 'General Reports', 'Link to the type description page', false, NULL, NULL, NULL, 'request_barcodes.cgi?typespopup=1');
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (20, 'Show Allocations', 'General Reports', 'Shows the blocks of codes allocated to users', false, NULL, 'Username;<pivotquery;Item Type;<pivotquery;<hide;Size;Range;Used;Active;Disposed;Free;<hide;<hide;Comments;Date;Show Data;<pivotquery', 'select ba.username, ''Show Users'' as pivot,
replace( ba.typename, ''_'', '' '') as typename, 
''Show Types'' as pivot2, 1 as showdisabled,
ba.tocode - ba.fromcode + 1 as size,
to_char(ba.fromcode, ''FM00-000000'') || '':'' || 
 to_char(ba.tocode, ''FM00-000000'') as range,
used,active, disposed,
(ba.tocode - ba.fromcode + 1 - active - disposed) as free,
ba.fromcode,
ba.tocode,
ba.comments, ba.datestamp,
case when used > 0 then ''View'' else '''' end as viewactive,
''Data Summary'' as pivot2
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
$?MRF{{ desc }}', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (10, 'Show Users', 'General Reports', 'Summarise registered users', false, NULL, 'Username;Real Name;E-Mail;Institute;Blocks Allocated;Codes Allocated;<pivotquery;Codes in Use', 'select bu.username, bu.realname, ''*blocked*'', bu.institute,
count(ba.*),
sum(ba.tocode - ba.fromcode + 1) as allocated,
''Show Allocations'' as pivot,
sum(active) as active
from barcode_user bu 
$!ONLYBARCODES{{ left outer join }}
$?ONLYBARCODES{{ inner join }} 
( barcode_allocation ba 
inner join count_used_by_block us on us.fromcode = ba.fromcode
inner join count_active_by_block act on act.fromcode = ba.fromcode
) on bu.username = ba.username
where true
$?USERNAME{{ and $USERNAME = ba.username }}
$?REALNAME{{ and $REALNAME = bu.realname }}
$?INST{{ and $INST = bu.institute }}
group by bu.username, bu.realname, bu.email, bu.institute
', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (45, 'Full Data View', 'Show Data', 'Show all information on a group of barcodes.  You need to specify the barcode type explicitly for this to work.', false, NULL, 'Barcode;<linknoterms;<hide', 'select to_char(g.barcode, ''FM00-000000'')
,''query_barcodes.cgi?bc='' || to_char(g.barcode, ''FM00-000000'') as link,
g.* from $_BCTYPE $!BCTYPE{{ generic }} g
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
order by g.barcode', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (60, 'Describe Library', 'Type-specific Reports', 'Show all the plates in a selected clone library', false, NULL, 'Library name;Type;Plate Barcode;<linknoterms;Storage location;Creation date;Created by;Source;<linknoterms', 'select library, library_type, 
to_char(barcode, ''FM00-000000'') as barcode, ''query_barcodes.cgi?bc='' || to_char(barcode, ''FM00-000000'') as link1
, storage_location,
creation_date, created_by, 
coalesce(to_char(source_mix_barcode, ''FM00-000000''), source_mix) as source_mix,
case when source_mix_barcode is not null then ''query_barcodes.cgi?bc='' || to_char(source_mix_barcode, ''FM00-000000'') 
else null end as link, comments
from library_plate where true 
$?LIBNAME{{ and library = $LIBNAME }}
and barcode not in (select barcode from barcode_deletion)', NULL);
INSERT INTO query_def (query_id, title, category, long_label, hide, icon_index, column_head, query_body, query_url) VALUES (70, 'Show water samples', 'Type-specific Reports', 'Shows details for water samples', false, NULL, 'Barcode;<linknoterms;Notes;Location;<linknoterms', 'select to_char(g.barcode, ''FM00-000000'')
,''query_barcodes.cgi?bc='' || to_char(g.barcode, ''FM00-000000'') as link
,g.comments
,g.site_latitude || '', '' || g.site_longitude
,''http://maps.google.co.uk/maps?f=q&q='' || g.site_latitude || '','' || g.site_longitude
,storage_location
,creation_date
,storage_date
,created_by 
,d.datestamp as disposed
from water_sample g
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
}}', NULL);


--
-- PostgreSQL database dump
--

SET client_encoding = 'UNICODE';
SET check_function_bodies = false;

SET SESSION AUTHORIZATION 'postgres';

SET search_path = genquery, pg_catalog;

--
-- Data for TOC entry 2 (OID 4560990)
-- Name: query_param; Type: TABLE DATA; Schema: genquery; Owner: postgres
--

INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 20, 'DROPDOWN', 'INST', 'Institute', 'select distinct institute from barcode_user order by institute', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 40, 'TEXT', 'CODE', 'A barcode within block', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 50, 'YESNO', 'MRF', 'Most recent first', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (10, 20, 'DROPDOWN', 'REALNAME', 'Real Name', 'select realname from barcode_user', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (10, 30, 'DROPDOWN', 'INST', 'Institute', 'select distinct institute from barcode_user', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 10, 'DROPDOWN', 'USER', 'Owner Real Name', 'select realname from barcode_user order by realname;', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (15, 2, 'YESNO', 'SHOWDISABLED', 'Include disabled/hidden types?', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (10, 40, 'YESNO', 'ONLYBARCODES', 'Only show users with barcodes?', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 10, 'TEXT', 'FROMCODE', 'Lowest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 20, 'TEXT', 'TOCODE', 'Highest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 30, 'MULTI', 'TYPE', 'Item type', 'select distinct replace(typename, ''_'', '' '') as tn from barcode_allocation', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (20, 5, 'DROPDOWN', 'USERNAME', 'Owner Username', 'select username from barcode_user order by username;', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (10, 10, 'DROPDOWN', 'USERNAME', 'User Name', 'select username from barcode_user order by username', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (50, 10, 'TEXT', 'BASECODE', 'Base code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 30, 'DATE', 'FROMDATE', 'From date', '', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (40, 40, 'DATE', 'TODATE', 'To date', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (15, 1, 'DROPDOWN', 'TYPENAME', 'Show only type', 'select replace(tablename::varchar, ''_'', '' '') as name from pg_tables 
where schemaname::varchar = ''handlebar_data''
order by name', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (150, 1, 'HUGETEXT', NULL, 'SQL Query', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (70, 10, 'TEXT', 'FROMCODE', 'Lowest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (70, 20, 'TEXT', 'TOCODE', 'Highest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (60, 1, 'DROPDOWN', 'LIBNAME', 'Library name', 'select distinct library from library_plate', NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (70, 30, 'DATE', 'FROMDATE', 'From date', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (45, 10, 'TEXT', 'FROMCODE', 'Lowest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (45, 20, 'TEXT', 'TOCODE', 'Highest code', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (45, 30, 'DATE', 'FROMDATE', 'From date', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (45, 40, 'DATE', 'TODATE', 'To date', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (70, 40, 'DATE', 'TODATE', 'To date', NULL, NULL);
INSERT INTO query_param (query_id, param_no, param_type, param_name, param_text, menu_query, suppress_all) VALUES (45, 1, 'DROPDOWN', 'BCTYPE', 'Type to view', 'select distinct typename as tn from barcode_allocation where typename != ''generic''', NULL);


