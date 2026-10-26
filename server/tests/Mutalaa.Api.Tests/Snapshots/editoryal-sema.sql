--
-- PostgreSQL database dump
--



SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: icerik; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA icerik;


--
-- Name: kimlik; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA kimlik;


--
-- Name: derleme_turu; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.derleme_turu AS ENUM (
    'dev',
    'internal',
    'public'
);


--
-- Name: inceleme_durumu; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.inceleme_durumu AS ENUM (
    'acik',
    'onaylandi',
    'reddedildi',
    'geri_alindi'
);


--
-- Name: license_status; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.license_status AS ENUM (
    'serbest',
    'bekliyor',
    'ic_kullanim',
    'kapali'
);


--
-- Name: metin_durumu; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.metin_durumu AS ENUM (
    'taslak',
    'incelemede',
    'onayli'
);


--
-- Name: source_kind; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.source_kind AS ENUM (
    'kuran_metni',
    'meal',
    'tefsir',
    'hadis',
    'hadis_ceviri',
    'risale',
    'kitap',
    'morfoloji',
    'kelime_anlami',
    'sozluk',
    'mushaf_duzeni',
    'mushaf_gorseli',
    'font',
    'baski',
    'ses',
    'zamanlama',
    'baglanti_verisi'
);


--
-- Name: surum_durumu; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.surum_durumu AS ENUM (
    'hazirlaniyor',
    'dogrulandi',
    'yayinlandi',
    'basarisiz',
    'geri_cekildi'
);


--
-- Name: unit_kind; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.unit_kind AS ENUM (
    'ayet',
    'meal',
    'tefsir',
    'risale',
    'hadis',
    'hadis_ceviri',
    'kitap'
);


--
-- Name: unit_status; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.unit_status AS ENUM (
    'etkin',
    'kullanim_disi'
);


--
-- Name: xref_origin; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.xref_origin AS ENUM (
    'hat',
    'editor',
    'kullanici_oyu'
);


--
-- Name: xref_status; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.xref_status AS ENUM (
    'aday',
    'onayli',
    'red'
);


--
-- Name: xref_type; Type: TYPE; Schema: icerik; Owner: -
--

CREATE TYPE icerik.xref_type AS ENUM (
    'atif',
    'iktibas',
    'ima',
    'kok',
    'lemma',
    'konu',
    'benzer_ayet',
    'anlamsal'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: __EFMigrationsHistory; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik."__EFMigrationsHistory" (
    migration_id character varying(150) NOT NULL,
    product_version character varying(32) NOT NULL
);


--
-- Name: audio_timing; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.audio_timing (
    source_id text NOT NULL,
    anchor text NOT NULL COLLATE pg_catalog."C",
    file text NOT NULL,
    file_sha256 character(64) NOT NULL,
    start_ms integer NOT NULL,
    end_ms integer NOT NULL,
    words jsonb,
    timing_source text NOT NULL,
    data_version text NOT NULL,
    CONSTRAINT audio_timing_check CHECK ((start_ms < end_ms))
);


--
-- Name: ayah_box; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.ayah_box (
    source_id text NOT NULL,
    page integer NOT NULL,
    anchor text NOT NULL COLLATE pg_catalog."C",
    seq smallint NOT NULL,
    x integer NOT NULL,
    y integer NOT NULL,
    w integer NOT NULL,
    h integer NOT NULL,
    data_version text NOT NULL,
    CONSTRAINT ayah_box_check CHECK (((w > 0) AND (h > 0)))
);


--
-- Name: hadith_location; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.hadith_location (
    anchor text NOT NULL COLLATE pg_catalog."C",
    book_no integer,
    book_name text,
    bab_no integer,
    bab_name text,
    ord integer NOT NULL
);


--
-- Name: hadith_number_map; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.hadith_number_map (
    collection text NOT NULL,
    system text NOT NULL,
    number text NOT NULL,
    anchor text NOT NULL COLLATE pg_catalog."C"
);


--
-- Name: lemma; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.lemma (
    id integer NOT NULL,
    lang text NOT NULL,
    text text NOT NULL,
    text_clean text NOT NULL,
    root_id integer,
    occurrences integer DEFAULT 0 NOT NULL,
    qac_ref text,
    ar_lemma_id integer,
    etymological_only boolean DEFAULT false NOT NULL,
    origin text,
    status icerik.xref_status DEFAULT 'aday'::icerik.xref_status NOT NULL,
    freq integer,
    source_id text NOT NULL,
    data_version text NOT NULL,
    CONSTRAINT lemma_lang_check CHECK ((lang = ANY (ARRAY['ar'::text, 'tr'::text])))
);


--
-- Name: lemma_gloss; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.lemma_gloss (
    lemma_id integer NOT NULL,
    anlam_kisa text NOT NULL,
    kuran_anlamlari jsonb DEFAULT '[]'::jsonb NOT NULL,
    turkce_es_kelime text,
    yalnizca_etimolojik boolean DEFAULT false NOT NULL,
    editor_notu text,
    status icerik.xref_status DEFAULT 'aday'::icerik.xref_status NOT NULL,
    origin text NOT NULL,
    version text NOT NULL,
    content_hash character(64) NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: page_map; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.page_map (
    id bigint NOT NULL,
    source_id text NOT NULL,
    volume smallint,
    page integer NOT NULL,
    line smallint,
    line_type text,
    centered boolean DEFAULT false NOT NULL,
    start_anchor text NOT NULL COLLATE pg_catalog."C",
    start_offset integer,
    end_anchor text NOT NULL COLLATE pg_catalog."C",
    end_offset integer,
    glyphs jsonb,
    data_version text NOT NULL,
    CONSTRAINT page_map_line_type_check CHECK ((line_type = ANY (ARRAY['ayet'::text, 'sure_adi'::text, 'besmele'::text])))
);


--
-- Name: page_map_id_seq; Type: SEQUENCE; Schema: icerik; Owner: -
--

ALTER TABLE icerik.page_map ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME icerik.page_map_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: pipeline_run; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.pipeline_run (
    run_id uuid NOT NULL,
    komut text NOT NULL,
    git_commit text NOT NULL,
    parmak_izi character(64) NOT NULL,
    baslangic timestamp with time zone NOT NULL,
    bitis timestamp with time zone,
    durum text NOT NULL,
    manifest jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT pipeline_run_durum_check CHECK ((durum = ANY (ARRAY['calisiyor'::text, 'basarili'::text, 'basarisiz'::text])))
);


--
-- Name: quran_word; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.quran_word (
    anchor text NOT NULL COLLATE pg_catalog."C",
    surah smallint NOT NULL,
    ayah smallint NOT NULL,
    word smallint NOT NULL,
    ayah_index smallint NOT NULL,
    text_uthmani text NOT NULL,
    norm text NOT NULL,
    char_start integer NOT NULL,
    char_end integer NOT NULL,
    root_id integer,
    lemma_id integer,
    pos text,
    features jsonb,
    source_id text NOT NULL,
    morph_source text,
    data_version text NOT NULL,
    CONSTRAINT quran_word_check CHECK ((char_start < char_end))
);


--
-- Name: quran_word_fix; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.quran_word_fix (
    id uuid DEFAULT uuidv7() NOT NULL,
    anchor text NOT NULL COLLATE pg_catalog."C",
    field text NOT NULL,
    qac_value text,
    new_value text NOT NULL,
    reason text NOT NULL,
    status icerik.xref_status DEFAULT 'aday'::icerik.xref_status NOT NULL,
    editor text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT quran_word_fix_field_check CHECK ((field = ANY (ARRAY['root_id'::text, 'lemma_id'::text, 'pos'::text, 'features'::text])))
);


--
-- Name: release; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.release (
    id integer NOT NULL,
    surum text NOT NULL,
    derleme icerik.derleme_turu NOT NULL,
    durum icerik.surum_durumu DEFAULT 'hazirlaniyor'::icerik.surum_durumu NOT NULL,
    manifest jsonb,
    kapi_raporu jsonb DEFAULT '{}'::jsonb NOT NULL,
    kaynak_durumu jsonb DEFAULT '{}'::jsonb NOT NULL,
    ozetler jsonb DEFAULT '{}'::jsonb NOT NULL,
    data_version text NOT NULL,
    olusturan text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    yayinlandi_at timestamp with time zone
);


--
-- Name: release_id_seq; Type: SEQUENCE; Schema: icerik; Owner: -
--

ALTER TABLE icerik.release ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME icerik.release_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: review; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.review (
    id bigint NOT NULL,
    hedef_tablo text NOT NULL,
    hedef_anahtar text NOT NULL,
    xref_id uuid,
    alan text NOT NULL,
    eylem text NOT NULL,
    onceki jsonb,
    onerilen jsonb,
    durum icerik.inceleme_durumu DEFAULT 'acik'::icerik.inceleme_durumu NOT NULL,
    koken icerik.xref_origin NOT NULL,
    yz_modeli text,
    yz_kaydi jsonb,
    guven real,
    oneren text NOT NULL,
    inceleyen text,
    ikinci_inceleyen text,
    sure_ms integer,
    gerekce text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    incelendi_at timestamp with time zone,
    CONSTRAINT review_hedef_tablo_check CHECK ((hedef_tablo = ANY (ARRAY['source'::text, 'unit'::text, 'quran_word_fix'::text, 'lemma'::text, 'lemma_gloss'::text, 'root'::text, 'tr_root_index'::text, 'tr_form'::text, 'surah_alias'::text, 'xref'::text, 'page_map'::text, 'ayah_box'::text, 'audio_timing'::text]))),
    CONSTRAINT review_yz_kaydi_check CHECK ((((yz_modeli IS NULL) AND (yz_kaydi IS NULL)) OR ((yz_modeli IS NOT NULL) AND (yz_kaydi IS NOT NULL) AND (jsonb_typeof(yz_kaydi) = 'object'::text) AND (yz_kaydi ?& ARRAY['prompt_id'::text, 'prompt_sha256'::text, 'input_sha256'::text]) AND (COALESCE((yz_kaydi ->> 'prompt_sha256'::text), ''::text) ~ '^[0-9a-f]{64}$'::text) AND (COALESCE((yz_kaydi ->> 'input_sha256'::text), ''::text) ~ '^[0-9a-f]{64}$'::text))))
);


--
-- Name: review_id_seq; Type: SEQUENCE; Schema: icerik; Owner: -
--

ALTER TABLE icerik.review ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME icerik.review_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: root; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.root (
    id integer NOT NULL,
    letters text NOT NULL,
    letters_bw text,
    occurrences integer DEFAULT 0 NOT NULL,
    ayah_count integer DEFAULT 0 NOT NULL,
    idf_q real,
    kok_anlami text,
    source_id text NOT NULL,
    data_version text NOT NULL
);


--
-- Name: source; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.source (
    slug text NOT NULL COLLATE pg_catalog."C",
    tur icerik.source_kind NOT NULL,
    baslik text NOT NULL,
    yazar text,
    yazar_vefat_yili smallint,
    surum text NOT NULL,
    provider text,
    kaynak_url text,
    alinma_tarihi date,
    dosya_sha256 character(64),
    baski_bilgisi jsonb,
    license_name text NOT NULL,
    license_url text,
    license_status icerik.license_status DEFAULT 'bekliyor'::icerik.license_status NOT NULL,
    lisans_kopyasi text,
    lisans_sha256 character(64),
    kamu_mali_tarihi date,
    kisitlar jsonb DEFAULT '{}'::jsonb NOT NULL,
    embed_ok boolean DEFAULT false NOT NULL,
    kurul_gerekli boolean DEFAULT false NOT NULL,
    kurul_onay jsonb,
    kurul_onay_tarihi date,
    kurul_onay_ozeti character(64),
    atif_metni text NOT NULL,
    atif_url text,
    notice_text text,
    yeniden_kontrol date,
    notlar text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT source_check CHECK (((kurul_onay IS NULL) OR ((kurul_onay ?& ARRAY['onay_no'::text, 'onayli_surum'::text]) AND (kurul_onay_tarihi IS NOT NULL) AND (kurul_onay_ozeti IS NOT NULL))))
);


--
-- Name: surah_alias; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.surah_alias (
    surah_no smallint NOT NULL,
    alias text NOT NULL,
    alias_key text NOT NULL,
    kind text NOT NULL,
    risky boolean DEFAULT false NOT NULL,
    status icerik.xref_status DEFAULT 'aday'::icerik.xref_status NOT NULL,
    CONSTRAINT surah_alias_kind_check CHECK ((kind = ANY (ARRAY['kanonik'::text, 'yazim'::text, 'arapca'::text, 'diger_ad'::text]))),
    CONSTRAINT surah_alias_surah_no_check CHECK (((surah_no >= 1) AND (surah_no <= 114)))
);


--
-- Name: tr_form; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.tr_form (
    key_narrow text NOT NULL,
    tr_lemma_id integer NOT NULL,
    key_wide text NOT NULL,
    freq integer DEFAULT 0 NOT NULL
);


--
-- Name: tr_root_index; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.tr_root_index (
    anchor text NOT NULL COLLATE pg_catalog."C",
    span_start integer NOT NULL,
    span_end integer NOT NULL,
    root_id integer NOT NULL,
    tr_lemma_id integer NOT NULL,
    etymological_only boolean DEFAULT false NOT NULL,
    data_version text NOT NULL,
    CONSTRAINT tr_root_index_check CHECK ((span_start < span_end))
);


--
-- Name: unit; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.unit (
    id bigint NOT NULL,
    anchor text NOT NULL COLLATE pg_catalog."C",
    kind icerik.unit_kind NOT NULL,
    role text DEFAULT 'govde'::text NOT NULL,
    source_id text NOT NULL,
    parent_path text COLLATE pg_catalog."C",
    ord bigint NOT NULL,
    ayah_range int4range,
    metin text NOT NULL,
    marks jsonb DEFAULT '[]'::jsonb NOT NULL,
    sentences int4range[],
    attrs jsonb DEFAULT '{}'::jsonb NOT NULL,
    content_hash character(64) NOT NULL,
    rev integer DEFAULT 1 NOT NULL,
    metin_durumu icerik.metin_durumu DEFAULT 'taslak'::icerik.metin_durumu NOT NULL,
    status icerik.unit_status DEFAULT 'etkin'::icerik.unit_status NOT NULL,
    successors jsonb,
    tr_narrow text,
    tr_wide text,
    tr_stem text,
    ar_norm text,
    data_version text NOT NULL,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    run_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tsv_ar tsvector GENERATED ALWAYS AS (to_tsvector('arabic'::regconfig, COALESCE(ar_norm, ''::text))) STORED,
    tsv_tr tsvector GENERATED ALWAYS AS (to_tsvector('turkish'::regconfig, COALESCE(tr_narrow, ''::text))) STORED,
    CONSTRAINT unit_check CHECK (((status = 'etkin'::icerik.unit_status) OR (successors IS NOT NULL))),
    CONSTRAINT unit_content_hash_check CHECK ((content_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT unit_role_check CHECK ((role = ANY (ARRAY['govde'::text, 'baslik'::text, 'hasiye'::text, 'dipnot'::text, 'siir'::text])))
);


--
-- Name: unit_id_seq; Type: SEQUENCE; Schema: icerik; Owner: -
--

ALTER TABLE icerik.unit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME icerik.unit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: xref; Type: TABLE; Schema: icerik; Owner: -
--

CREATE TABLE icerik.xref (
    id uuid DEFAULT uuidv7() NOT NULL,
    src_anchor text NOT NULL COLLATE pg_catalog."C",
    src_span int4range,
    dst_anchor text NOT NULL COLLATE pg_catalog."C",
    dst_span int4range,
    type icerik.xref_type NOT NULL,
    score real NOT NULL,
    confidence real NOT NULL,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    origin icerik.xref_origin NOT NULL,
    status icerik.xref_status DEFAULT 'aday'::icerik.xref_status NOT NULL,
    votes_up integer DEFAULT 0 NOT NULL,
    votes_down integer DEFAULT 0 NOT NULL,
    data_version text NOT NULL,
    license icerik.license_status NOT NULL,
    CONSTRAINT xref_confidence_check CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision))),
    CONSTRAINT xref_score_check CHECK (((score >= (0)::double precision) AND (score <= (1)::double precision)))
);


--
-- Name: role_claims; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.role_claims (
    id integer NOT NULL,
    role_id text NOT NULL,
    claim_type text,
    claim_value text
);


--
-- Name: role_claims_id_seq; Type: SEQUENCE; Schema: kimlik; Owner: -
--

ALTER TABLE kimlik.role_claims ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME kimlik.role_claims_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: roles; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.roles (
    id text NOT NULL,
    name character varying(256),
    normalized_name character varying(256),
    concurrency_stamp text
);


--
-- Name: user_claims; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.user_claims (
    id integer NOT NULL,
    user_id text NOT NULL,
    claim_type text,
    claim_value text
);


--
-- Name: user_claims_id_seq; Type: SEQUENCE; Schema: kimlik; Owner: -
--

ALTER TABLE kimlik.user_claims ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME kimlik.user_claims_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: user_logins; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.user_logins (
    login_provider text NOT NULL,
    provider_key text NOT NULL,
    provider_display_name text,
    user_id text NOT NULL
);


--
-- Name: user_roles; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.user_roles (
    user_id text NOT NULL,
    role_id text NOT NULL
);


--
-- Name: user_tokens; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.user_tokens (
    user_id text NOT NULL,
    login_provider text NOT NULL,
    name text NOT NULL,
    value text
);


--
-- Name: users; Type: TABLE; Schema: kimlik; Owner: -
--

CREATE TABLE kimlik.users (
    id text NOT NULL,
    user_name character varying(256),
    normalized_user_name character varying(256),
    email character varying(256),
    normalized_email character varying(256),
    email_confirmed boolean NOT NULL,
    password_hash text,
    security_stamp text,
    concurrency_stamp text,
    phone_number text,
    phone_number_confirmed boolean NOT NULL,
    two_factor_enabled boolean NOT NULL,
    lockout_end timestamp with time zone,
    lockout_enabled boolean NOT NULL,
    access_failed_count integer NOT NULL
);


--
-- Name: audio_timing audio_timing_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.audio_timing
    ADD CONSTRAINT audio_timing_pkey PRIMARY KEY (source_id, anchor);


--
-- Name: ayah_box ayah_box_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.ayah_box
    ADD CONSTRAINT ayah_box_pkey PRIMARY KEY (source_id, page, anchor, seq);


--
-- Name: hadith_location hadith_location_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.hadith_location
    ADD CONSTRAINT hadith_location_pkey PRIMARY KEY (anchor);


--
-- Name: hadith_number_map hadith_number_map_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.hadith_number_map
    ADD CONSTRAINT hadith_number_map_pkey PRIMARY KEY (collection, system, number);


--
-- Name: lemma_gloss lemma_gloss_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma_gloss
    ADD CONSTRAINT lemma_gloss_pkey PRIMARY KEY (lemma_id);


--
-- Name: lemma lemma_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma
    ADD CONSTRAINT lemma_pkey PRIMARY KEY (id);


--
-- Name: page_map page_map_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.page_map
    ADD CONSTRAINT page_map_pkey PRIMARY KEY (id);


--
-- Name: pipeline_run pipeline_run_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.pipeline_run
    ADD CONSTRAINT pipeline_run_pkey PRIMARY KEY (run_id);


--
-- Name: __EFMigrationsHistory pk___ef_migrations_history; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik."__EFMigrationsHistory"
    ADD CONSTRAINT pk___ef_migrations_history PRIMARY KEY (migration_id);


--
-- Name: quran_word_fix quran_word_fix_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word_fix
    ADD CONSTRAINT quran_word_fix_pkey PRIMARY KEY (id);


--
-- Name: quran_word quran_word_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word
    ADD CONSTRAINT quran_word_pkey PRIMARY KEY (anchor);


--
-- Name: release release_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.release
    ADD CONSTRAINT release_pkey PRIMARY KEY (id);


--
-- Name: review review_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.review
    ADD CONSTRAINT review_pkey PRIMARY KEY (id);


--
-- Name: root root_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.root
    ADD CONSTRAINT root_pkey PRIMARY KEY (id);


--
-- Name: source source_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.source
    ADD CONSTRAINT source_pkey PRIMARY KEY (slug);


--
-- Name: surah_alias surah_alias_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.surah_alias
    ADD CONSTRAINT surah_alias_pkey PRIMARY KEY (surah_no, alias);


--
-- Name: tr_form tr_form_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.tr_form
    ADD CONSTRAINT tr_form_pkey PRIMARY KEY (key_narrow, tr_lemma_id);


--
-- Name: tr_root_index tr_root_index_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.tr_root_index
    ADD CONSTRAINT tr_root_index_pkey PRIMARY KEY (anchor, span_start);


--
-- Name: unit unit_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.unit
    ADD CONSTRAINT unit_pkey PRIMARY KEY (id);


--
-- Name: xref xref_natural_key; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.xref
    ADD CONSTRAINT xref_natural_key UNIQUE NULLS NOT DISTINCT (type, src_anchor, src_span, dst_anchor, dst_span);


--
-- Name: xref xref_pkey; Type: CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.xref
    ADD CONSTRAINT xref_pkey PRIMARY KEY (id);


--
-- Name: role_claims pk_role_claims; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.role_claims
    ADD CONSTRAINT pk_role_claims PRIMARY KEY (id);


--
-- Name: roles pk_roles; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.roles
    ADD CONSTRAINT pk_roles PRIMARY KEY (id);


--
-- Name: user_claims pk_user_claims; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_claims
    ADD CONSTRAINT pk_user_claims PRIMARY KEY (id);


--
-- Name: user_logins pk_user_logins; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_logins
    ADD CONSTRAINT pk_user_logins PRIMARY KEY (login_provider, provider_key);


--
-- Name: user_roles pk_user_roles; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_roles
    ADD CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id);


--
-- Name: user_tokens pk_user_tokens; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_tokens
    ADD CONSTRAINT pk_user_tokens PRIMARY KEY (user_id, login_provider, name);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: page_map_source_id_volume_page_line_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX page_map_source_id_volume_page_line_key ON icerik.page_map USING btree (source_id, volume, page, line) NULLS NOT DISTINCT;


--
-- Name: page_map_start; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX page_map_start ON icerik.page_map USING btree (start_anchor);


--
-- Name: quran_word_ayah; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX quran_word_ayah ON icerik.quran_word USING btree (ayah_index, word);


--
-- Name: quran_word_fix_anchor_field_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX quran_word_fix_anchor_field_key ON icerik.quran_word_fix USING btree (anchor, field);


--
-- Name: quran_word_lemma; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX quran_word_lemma ON icerik.quran_word USING btree (lemma_id);


--
-- Name: quran_word_root; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX quran_word_root ON icerik.quran_word USING btree (root_id);


--
-- Name: quran_word_surah_ayah_word_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX quran_word_surah_ayah_word_key ON icerik.quran_word USING btree (surah, ayah, word);


--
-- Name: release_surum_derleme_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX release_surum_derleme_key ON icerik.release USING btree (surum, derleme);


--
-- Name: review_queue; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX review_queue ON icerik.review USING btree (hedef_tablo, created_at) WHERE (durum = 'acik'::icerik.inceleme_durumu);


--
-- Name: review_xref; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX review_xref ON icerik.review USING btree (xref_id) WHERE (xref_id IS NOT NULL);


--
-- Name: root_letters_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX root_letters_key ON icerik.root USING btree (letters);


--
-- Name: tr_form_wide; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX tr_form_wide ON icerik.tr_form USING btree (key_wide);


--
-- Name: tr_root_index_root; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX tr_root_index_root ON icerik.tr_root_index USING btree (root_id, anchor);


--
-- Name: unit_anchor_key; Type: INDEX; Schema: icerik; Owner: -
--

CREATE UNIQUE INDEX unit_anchor_key ON icerik.unit USING btree (anchor);


--
-- Name: unit_ayah; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX unit_ayah ON icerik.unit USING gist (ayah_range);


--
-- Name: unit_parent; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX unit_parent ON icerik.unit USING btree (parent_path, ord);


--
-- Name: unit_source_ord; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX unit_source_ord ON icerik.unit USING btree (source_id, ord);


--
-- Name: unit_tsv_ar; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX unit_tsv_ar ON icerik.unit USING gin (tsv_ar);


--
-- Name: unit_tsv_tr; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX unit_tsv_tr ON icerik.unit USING gin (tsv_tr);


--
-- Name: xref_dst; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX xref_dst ON icerik.xref USING btree (dst_anchor, type);


--
-- Name: xref_queue; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX xref_queue ON icerik.xref USING btree (type, confidence DESC) WHERE (status = 'aday'::icerik.xref_status);


--
-- Name: xref_src; Type: INDEX; Schema: icerik; Owner: -
--

CREATE INDEX xref_src ON icerik.xref USING btree (src_anchor, type);


--
-- Name: ix_role_claims_role_id; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE INDEX ix_role_claims_role_id ON kimlik.role_claims USING btree (role_id);


--
-- Name: ix_roles_normalized_name; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE UNIQUE INDEX ix_roles_normalized_name ON kimlik.roles USING btree (normalized_name);


--
-- Name: ix_user_claims_user_id; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE INDEX ix_user_claims_user_id ON kimlik.user_claims USING btree (user_id);


--
-- Name: ix_user_logins_user_id; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE INDEX ix_user_logins_user_id ON kimlik.user_logins USING btree (user_id);


--
-- Name: ix_user_roles_role_id; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE INDEX ix_user_roles_role_id ON kimlik.user_roles USING btree (role_id);


--
-- Name: ix_users_normalized_email; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE UNIQUE INDEX ix_users_normalized_email ON kimlik.users USING btree (normalized_email);


--
-- Name: ix_users_normalized_user_name; Type: INDEX; Schema: kimlik; Owner: -
--

CREATE UNIQUE INDEX ix_users_normalized_user_name ON kimlik.users USING btree (normalized_user_name);


--
-- Name: audio_timing audio_timing_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.audio_timing
    ADD CONSTRAINT audio_timing_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: ayah_box ayah_box_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.ayah_box
    ADD CONSTRAINT ayah_box_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: lemma lemma_ar_lemma_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma
    ADD CONSTRAINT lemma_ar_lemma_id_fkey FOREIGN KEY (ar_lemma_id) REFERENCES icerik.lemma(id);


--
-- Name: lemma_gloss lemma_gloss_lemma_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma_gloss
    ADD CONSTRAINT lemma_gloss_lemma_id_fkey FOREIGN KEY (lemma_id) REFERENCES icerik.lemma(id);


--
-- Name: lemma lemma_root_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma
    ADD CONSTRAINT lemma_root_id_fkey FOREIGN KEY (root_id) REFERENCES icerik.root(id);


--
-- Name: lemma lemma_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.lemma
    ADD CONSTRAINT lemma_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: page_map page_map_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.page_map
    ADD CONSTRAINT page_map_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: quran_word quran_word_lemma_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word
    ADD CONSTRAINT quran_word_lemma_id_fkey FOREIGN KEY (lemma_id) REFERENCES icerik.lemma(id);


--
-- Name: quran_word quran_word_morph_source_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word
    ADD CONSTRAINT quran_word_morph_source_fkey FOREIGN KEY (morph_source) REFERENCES icerik.source(slug);


--
-- Name: quran_word quran_word_root_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word
    ADD CONSTRAINT quran_word_root_id_fkey FOREIGN KEY (root_id) REFERENCES icerik.root(id);


--
-- Name: quran_word quran_word_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.quran_word
    ADD CONSTRAINT quran_word_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: review review_xref_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.review
    ADD CONSTRAINT review_xref_id_fkey FOREIGN KEY (xref_id) REFERENCES icerik.xref(id);


--
-- Name: root root_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.root
    ADD CONSTRAINT root_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: tr_form tr_form_tr_lemma_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.tr_form
    ADD CONSTRAINT tr_form_tr_lemma_id_fkey FOREIGN KEY (tr_lemma_id) REFERENCES icerik.lemma(id);


--
-- Name: tr_root_index tr_root_index_root_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.tr_root_index
    ADD CONSTRAINT tr_root_index_root_id_fkey FOREIGN KEY (root_id) REFERENCES icerik.root(id);


--
-- Name: tr_root_index tr_root_index_tr_lemma_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.tr_root_index
    ADD CONSTRAINT tr_root_index_tr_lemma_id_fkey FOREIGN KEY (tr_lemma_id) REFERENCES icerik.lemma(id);


--
-- Name: unit unit_run_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.unit
    ADD CONSTRAINT unit_run_id_fkey FOREIGN KEY (run_id) REFERENCES icerik.pipeline_run(run_id);


--
-- Name: unit unit_source_id_fkey; Type: FK CONSTRAINT; Schema: icerik; Owner: -
--

ALTER TABLE ONLY icerik.unit
    ADD CONSTRAINT unit_source_id_fkey FOREIGN KEY (source_id) REFERENCES icerik.source(slug);


--
-- Name: role_claims fk_role_claims_roles_role_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.role_claims
    ADD CONSTRAINT fk_role_claims_roles_role_id FOREIGN KEY (role_id) REFERENCES kimlik.roles(id) ON DELETE CASCADE;


--
-- Name: user_claims fk_user_claims_users_user_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_claims
    ADD CONSTRAINT fk_user_claims_users_user_id FOREIGN KEY (user_id) REFERENCES kimlik.users(id) ON DELETE CASCADE;


--
-- Name: user_logins fk_user_logins_users_user_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_logins
    ADD CONSTRAINT fk_user_logins_users_user_id FOREIGN KEY (user_id) REFERENCES kimlik.users(id) ON DELETE CASCADE;


--
-- Name: user_roles fk_user_roles_roles_role_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_roles
    ADD CONSTRAINT fk_user_roles_roles_role_id FOREIGN KEY (role_id) REFERENCES kimlik.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles fk_user_roles_users_user_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_roles
    ADD CONSTRAINT fk_user_roles_users_user_id FOREIGN KEY (user_id) REFERENCES kimlik.users(id) ON DELETE CASCADE;


--
-- Name: user_tokens fk_user_tokens_users_user_id; Type: FK CONSTRAINT; Schema: kimlik; Owner: -
--

ALTER TABLE ONLY kimlik.user_tokens
    ADD CONSTRAINT fk_user_tokens_users_user_id FOREIGN KEY (user_id) REFERENCES kimlik.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--
