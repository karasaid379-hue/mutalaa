using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Mutalaa.Domain.Content;
using Mutalaa.Domain.Licensing;
using Mutalaa.Domain.Links;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Reviews;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;
using NpgsqlTypes;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class CreateEditorialSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "icerik");

            migrationBuilder.EnsureSchema(
                name: "kimlik");

            migrationBuilder.AlterDatabase()
                .Annotation("Npgsql:Enum:icerik.derleme_turu", "dev,internal,public")
                .Annotation("Npgsql:Enum:icerik.inceleme_durumu", "acik,onaylandi,reddedildi,geri_alindi")
                .Annotation("Npgsql:Enum:icerik.license_status", "serbest,bekliyor,ic_kullanim,kapali")
                .Annotation("Npgsql:Enum:icerik.metin_durumu", "taslak,incelemede,onayli")
                .Annotation("Npgsql:Enum:icerik.source_kind", "kuran_metni,meal,tefsir,hadis,hadis_ceviri,risale,kitap,morfoloji,kelime_anlami,sozluk,mushaf_duzeni,mushaf_gorseli,font,baski,ses,zamanlama,baglanti_verisi")
                .Annotation("Npgsql:Enum:icerik.surum_durumu", "hazirlaniyor,dogrulandi,yayinlandi,basarisiz,geri_cekildi")
                .Annotation("Npgsql:Enum:icerik.unit_kind", "ayet,meal,tefsir,risale,hadis,hadis_ceviri,kitap")
                .Annotation("Npgsql:Enum:icerik.unit_status", "etkin,kullanim_disi")
                .Annotation("Npgsql:Enum:icerik.xref_origin", "hat,editor,kullanici_oyu")
                .Annotation("Npgsql:Enum:icerik.xref_status", "aday,onayli,red")
                .Annotation("Npgsql:Enum:icerik.xref_type", "atif,iktibas,ima,kok,lemma,konu,benzer_ayet,anlamsal");

            migrationBuilder.CreateTable(
                name: "hadith_location",
                schema: "icerik",
                columns: table => new
                {
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    book_no = table.Column<int>(type: "integer", nullable: true),
                    book_name = table.Column<string>(type: "text", nullable: true),
                    bab_no = table.Column<int>(type: "integer", nullable: true),
                    bab_name = table.Column<string>(type: "text", nullable: true),
                    ord = table.Column<int>(type: "integer", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("hadith_location_pkey", x => x.anchor);
                });

            migrationBuilder.CreateTable(
                name: "hadith_number_map",
                schema: "icerik",
                columns: table => new
                {
                    collection = table.Column<string>(type: "text", nullable: false),
                    system = table.Column<string>(type: "text", nullable: false),
                    number = table.Column<string>(type: "text", nullable: false),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("hadith_number_map_pkey", x => new { x.collection, x.system, x.number });
                });

            migrationBuilder.CreateTable(
                name: "pipeline_run",
                schema: "icerik",
                columns: table => new
                {
                    run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    komut = table.Column<string>(type: "text", nullable: false),
                    git_commit = table.Column<string>(type: "text", nullable: false),
                    parmak_izi = table.Column<string>(type: "char(64)", nullable: false),
                    baslangic = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    bitis = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    durum = table.Column<string>(type: "text", nullable: false),
                    manifest = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pipeline_run_pkey", x => x.run_id);
                    table.CheckConstraint("pipeline_run_durum_check", "durum IN ('calisiyor','basarili','basarisiz')");
                });

            migrationBuilder.CreateTable(
                name: "quran_word_fix",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "uuidv7()"),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    field = table.Column<string>(type: "text", nullable: false),
                    qac_value = table.Column<string>(type: "text", nullable: true),
                    new_value = table.Column<string>(type: "text", nullable: false),
                    reason = table.Column<string>(type: "text", nullable: false),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    editor = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("quran_word_fix_pkey", x => x.id);
                    table.CheckConstraint("quran_word_fix_field_check", "field IN ('root_id','lemma_id','pos','features')");
                });

            migrationBuilder.CreateTable(
                name: "release",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    surum = table.Column<string>(type: "text", nullable: false),
                    derleme = table.Column<BuildFlavor>(type: "icerik.derleme_turu", nullable: false),
                    durum = table.Column<ReleaseStatus>(type: "icerik.surum_durumu", nullable: false, defaultValue: ReleaseStatus.Hazirlaniyor),
                    manifest = table.Column<string>(type: "jsonb", nullable: true),
                    kapi_raporu = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    kaynak_durumu = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    ozetler = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    olusturan = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    yayinlandi_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("release_pkey", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "roles",
                schema: "kimlik",
                columns: table => new
                {
                    id = table.Column<string>(type: "text", nullable: false),
                    name = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    normalized_name = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    concurrency_stamp = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_roles", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "source",
                schema: "icerik",
                columns: table => new
                {
                    slug = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    tur = table.Column<SourceKind>(type: "icerik.source_kind", nullable: false),
                    baslik = table.Column<string>(type: "text", nullable: false),
                    yazar = table.Column<string>(type: "text", nullable: true),
                    yazar_vefat_yili = table.Column<short>(type: "smallint", nullable: true),
                    surum = table.Column<string>(type: "text", nullable: false),
                    provider = table.Column<string>(type: "text", nullable: true),
                    kaynak_url = table.Column<string>(type: "text", nullable: true),
                    alinma_tarihi = table.Column<DateOnly>(type: "date", nullable: true),
                    dosya_sha256 = table.Column<string>(type: "char(64)", nullable: true),
                    baski_bilgisi = table.Column<string>(type: "jsonb", nullable: true),
                    license_name = table.Column<string>(type: "text", nullable: false),
                    license_url = table.Column<string>(type: "text", nullable: true),
                    license_status = table.Column<LicenseStatus>(type: "icerik.license_status", nullable: false, defaultValue: LicenseStatus.Bekliyor),
                    lisans_kopyasi = table.Column<string>(type: "text", nullable: true),
                    lisans_sha256 = table.Column<string>(type: "char(64)", nullable: true),
                    kamu_mali_tarihi = table.Column<DateOnly>(type: "date", nullable: true),
                    kisitlar = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    embed_ok = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    kurul_gerekli = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    kurul_onay = table.Column<string>(type: "jsonb", nullable: true),
                    kurul_onay_tarihi = table.Column<DateOnly>(type: "date", nullable: true),
                    kurul_onay_ozeti = table.Column<string>(type: "char(64)", nullable: true),
                    atif_metni = table.Column<string>(type: "text", nullable: false),
                    atif_url = table.Column<string>(type: "text", nullable: true),
                    notice_text = table.Column<string>(type: "text", nullable: true),
                    yeniden_kontrol = table.Column<DateOnly>(type: "date", nullable: true),
                    notlar = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("source_pkey", x => x.slug);
                    table.CheckConstraint("source_check", "kurul_onay IS NULL OR (kurul_onay ?& ARRAY['onay_no','onayli_surum'] AND kurul_onay_tarihi IS NOT NULL AND kurul_onay_ozeti IS NOT NULL)");
                });

            migrationBuilder.CreateTable(
                name: "surah_alias",
                schema: "icerik",
                columns: table => new
                {
                    surah_no = table.Column<short>(type: "smallint", nullable: false),
                    alias = table.Column<string>(type: "text", nullable: false),
                    alias_key = table.Column<string>(type: "text", nullable: false),
                    kind = table.Column<string>(type: "text", nullable: false),
                    risky = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("surah_alias_pkey", x => new { x.surah_no, x.alias });
                    table.CheckConstraint("surah_alias_kind_check", "kind IN ('kanonik','yazim','arapca','diger_ad')");
                    table.CheckConstraint("surah_alias_surah_no_check", "surah_no BETWEEN 1 AND 114");
                });

            migrationBuilder.CreateTable(
                name: "users",
                schema: "kimlik",
                columns: table => new
                {
                    id = table.Column<string>(type: "text", nullable: false),
                    user_name = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    normalized_user_name = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    email = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    normalized_email = table.Column<string>(type: "character varying(256)", maxLength: 256, nullable: true),
                    email_confirmed = table.Column<bool>(type: "boolean", nullable: false),
                    password_hash = table.Column<string>(type: "text", nullable: true),
                    security_stamp = table.Column<string>(type: "text", nullable: true),
                    concurrency_stamp = table.Column<string>(type: "text", nullable: true),
                    phone_number = table.Column<string>(type: "text", nullable: true),
                    phone_number_confirmed = table.Column<bool>(type: "boolean", nullable: false),
                    two_factor_enabled = table.Column<bool>(type: "boolean", nullable: false),
                    lockout_end = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    lockout_enabled = table.Column<bool>(type: "boolean", nullable: false),
                    access_failed_count = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_users", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "xref",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "uuidv7()"),
                    src_anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    src_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    dst_anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    dst_span = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    type = table.Column<XrefType>(type: "icerik.xref_type", nullable: false),
                    score = table.Column<float>(type: "real", nullable: false),
                    confidence = table.Column<float>(type: "real", nullable: false),
                    evidence = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    origin = table.Column<XrefOrigin>(type: "icerik.xref_origin", nullable: false),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    votes_up = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    votes_down = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    license = table.Column<LicenseStatus>(type: "icerik.license_status", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("xref_pkey", x => x.id);
                    table.CheckConstraint("xref_confidence_check", "confidence BETWEEN 0 AND 1");
                    table.CheckConstraint("xref_score_check", "score BETWEEN 0 AND 1");
                });

            migrationBuilder.CreateTable(
                name: "role_claims",
                schema: "kimlik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    role_id = table.Column<string>(type: "text", nullable: false),
                    claim_type = table.Column<string>(type: "text", nullable: true),
                    claim_value = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_role_claims", x => x.id);
                    table.ForeignKey(
                        name: "fk_role_claims_roles_role_id",
                        column: x => x.role_id,
                        principalSchema: "kimlik",
                        principalTable: "roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "audio_timing",
                schema: "icerik",
                columns: table => new
                {
                    source_id = table.Column<string>(type: "text", nullable: false),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    file = table.Column<string>(type: "text", nullable: false),
                    file_sha256 = table.Column<string>(type: "char(64)", nullable: false),
                    start_ms = table.Column<int>(type: "integer", nullable: false),
                    end_ms = table.Column<int>(type: "integer", nullable: false),
                    words = table.Column<string>(type: "jsonb", nullable: true),
                    timing_source = table.Column<string>(type: "text", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("audio_timing_pkey", x => new { x.source_id, x.anchor });
                    table.CheckConstraint("audio_timing_check", "start_ms < end_ms");
                    table.ForeignKey(
                        name: "audio_timing_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "ayah_box",
                schema: "icerik",
                columns: table => new
                {
                    source_id = table.Column<string>(type: "text", nullable: false),
                    page = table.Column<int>(type: "integer", nullable: false),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    seq = table.Column<short>(type: "smallint", nullable: false),
                    x = table.Column<int>(type: "integer", nullable: false),
                    y = table.Column<int>(type: "integer", nullable: false),
                    w = table.Column<int>(type: "integer", nullable: false),
                    h = table.Column<int>(type: "integer", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("ayah_box_pkey", x => new { x.source_id, x.page, x.anchor, x.seq });
                    table.CheckConstraint("ayah_box_check", "w > 0 AND h > 0");
                    table.ForeignKey(
                        name: "ayah_box_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "page_map",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    volume = table.Column<short>(type: "smallint", nullable: true),
                    page = table.Column<int>(type: "integer", nullable: false),
                    line = table.Column<short>(type: "smallint", nullable: true),
                    line_type = table.Column<string>(type: "text", nullable: true),
                    centered = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    start_anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    start_offset = table.Column<int>(type: "integer", nullable: true),
                    end_anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    end_offset = table.Column<int>(type: "integer", nullable: true),
                    glyphs = table.Column<string>(type: "jsonb", nullable: true),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("page_map_pkey", x => x.id);
                    table.CheckConstraint("page_map_line_type_check", "line_type IN ('ayet','sure_adi','besmele')");
                    table.ForeignKey(
                        name: "page_map_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "root",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false),
                    letters = table.Column<string>(type: "text", nullable: false),
                    letters_bw = table.Column<string>(type: "text", nullable: true),
                    occurrences = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    ayah_count = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    idf_q = table.Column<float>(type: "real", nullable: true),
                    kok_anlami = table.Column<string>(type: "text", nullable: true),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("root_pkey", x => x.id);
                    table.ForeignKey(
                        name: "root_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "unit",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    kind = table.Column<UnitKind>(type: "icerik.unit_kind", nullable: false),
                    role = table.Column<string>(type: "text", nullable: false, defaultValue: "govde"),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    parent_path = table.Column<string>(type: "text", nullable: true, collation: "C"),
                    ord = table.Column<long>(type: "bigint", nullable: false),
                    ayah_range = table.Column<NpgsqlRange<int>>(type: "int4range", nullable: true),
                    metin = table.Column<string>(type: "text", nullable: false),
                    marks = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "[]"),
                    sentences = table.Column<NpgsqlRange<int>[]>(type: "int4range[]", nullable: true),
                    attrs = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    content_hash = table.Column<string>(type: "char(64)", nullable: false),
                    rev = table.Column<int>(type: "integer", nullable: false, defaultValue: 1),
                    metin_durumu = table.Column<TextStatus>(type: "icerik.metin_durumu", nullable: false, defaultValue: TextStatus.Taslak),
                    status = table.Column<UnitStatus>(type: "icerik.unit_status", nullable: false, defaultValue: UnitStatus.Etkin),
                    successors = table.Column<string>(type: "jsonb", nullable: true),
                    tr_narrow = table.Column<string>(type: "text", nullable: true),
                    tr_wide = table.Column<string>(type: "text", nullable: true),
                    tr_stem = table.Column<string>(type: "text", nullable: true),
                    ar_norm = table.Column<string>(type: "text", nullable: true),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    provenance = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    run_id = table.Column<Guid>(type: "uuid", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    tsv_ar = table.Column<NpgsqlTsVector>(type: "tsvector", nullable: true, computedColumnSql: "to_tsvector('arabic', coalesce(ar_norm, ''))", stored: true),
                    tsv_tr = table.Column<NpgsqlTsVector>(type: "tsvector", nullable: true, computedColumnSql: "to_tsvector('turkish', coalesce(tr_narrow, ''))", stored: true),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("unit_pkey", x => x.id);
                    table.CheckConstraint("unit_check", "status = 'etkin' OR successors IS NOT NULL");
                    table.CheckConstraint("unit_content_hash_check", "content_hash ~ '^[0-9a-f]{64}$'");
                    table.CheckConstraint("unit_role_check", "role IN ('govde','baslik','hasiye','dipnot','siir')");
                    table.ForeignKey(
                        name: "unit_run_id_fkey",
                        column: x => x.run_id,
                        principalSchema: "icerik",
                        principalTable: "pipeline_run",
                        principalColumn: "run_id");
                    table.ForeignKey(
                        name: "unit_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "user_claims",
                schema: "kimlik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    user_id = table.Column<string>(type: "text", nullable: false),
                    claim_type = table.Column<string>(type: "text", nullable: true),
                    claim_value = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_claims", x => x.id);
                    table.ForeignKey(
                        name: "fk_user_claims_users_user_id",
                        column: x => x.user_id,
                        principalSchema: "kimlik",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_logins",
                schema: "kimlik",
                columns: table => new
                {
                    login_provider = table.Column<string>(type: "text", nullable: false),
                    provider_key = table.Column<string>(type: "text", nullable: false),
                    provider_display_name = table.Column<string>(type: "text", nullable: true),
                    user_id = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_logins", x => new { x.login_provider, x.provider_key });
                    table.ForeignKey(
                        name: "fk_user_logins_users_user_id",
                        column: x => x.user_id,
                        principalSchema: "kimlik",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_roles",
                schema: "kimlik",
                columns: table => new
                {
                    user_id = table.Column<string>(type: "text", nullable: false),
                    role_id = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_roles", x => new { x.user_id, x.role_id });
                    table.ForeignKey(
                        name: "fk_user_roles_roles_role_id",
                        column: x => x.role_id,
                        principalSchema: "kimlik",
                        principalTable: "roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_user_roles_users_user_id",
                        column: x => x.user_id,
                        principalSchema: "kimlik",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_tokens",
                schema: "kimlik",
                columns: table => new
                {
                    user_id = table.Column<string>(type: "text", nullable: false),
                    login_provider = table.Column<string>(type: "text", nullable: false),
                    name = table.Column<string>(type: "text", nullable: false),
                    value = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_tokens", x => new { x.user_id, x.login_provider, x.name });
                    table.ForeignKey(
                        name: "fk_user_tokens_users_user_id",
                        column: x => x.user_id,
                        principalSchema: "kimlik",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "review",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    hedef_tablo = table.Column<string>(type: "text", nullable: false),
                    hedef_anahtar = table.Column<string>(type: "text", nullable: false),
                    xref_id = table.Column<Guid>(type: "uuid", nullable: true),
                    alan = table.Column<string>(type: "text", nullable: false),
                    eylem = table.Column<string>(type: "text", nullable: false),
                    onceki = table.Column<string>(type: "jsonb", nullable: true),
                    onerilen = table.Column<string>(type: "jsonb", nullable: true),
                    durum = table.Column<ReviewStatus>(type: "icerik.inceleme_durumu", nullable: false, defaultValue: ReviewStatus.Acik),
                    koken = table.Column<XrefOrigin>(type: "icerik.xref_origin", nullable: false),
                    yz_modeli = table.Column<string>(type: "text", nullable: true),
                    yz_kaydi = table.Column<string>(type: "jsonb", nullable: true),
                    guven = table.Column<float>(type: "real", nullable: true),
                    oneren = table.Column<string>(type: "text", nullable: false),
                    inceleyen = table.Column<string>(type: "text", nullable: true),
                    ikinci_inceleyen = table.Column<string>(type: "text", nullable: true),
                    sure_ms = table.Column<int>(type: "integer", nullable: true),
                    gerekce = table.Column<string>(type: "text", nullable: true),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    incelendi_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("review_pkey", x => x.id);
                    table.CheckConstraint("review_hedef_tablo_check", "hedef_tablo IN ('source','unit','quran_word_fix','lemma','lemma_gloss','root','tr_root_index','tr_form','surah_alias','xref','page_map','ayah_box','audio_timing')");
                    table.CheckConstraint("review_yz_kaydi_check", "(yz_modeli IS NULL AND yz_kaydi IS NULL) OR (yz_modeli IS NOT NULL AND yz_kaydi IS NOT NULL AND jsonb_typeof(yz_kaydi) = 'object' AND yz_kaydi ?& ARRAY['prompt_id','prompt_sha256','input_sha256'] AND coalesce(yz_kaydi->>'prompt_sha256','') ~ '^[0-9a-f]{64}$' AND coalesce(yz_kaydi->>'input_sha256','') ~ '^[0-9a-f]{64}$')");
                    table.ForeignKey(
                        name: "review_xref_id_fkey",
                        column: x => x.xref_id,
                        principalSchema: "icerik",
                        principalTable: "xref",
                        principalColumn: "id");
                });

            migrationBuilder.CreateTable(
                name: "lemma",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false),
                    lang = table.Column<string>(type: "text", nullable: false),
                    text = table.Column<string>(type: "text", nullable: false),
                    text_clean = table.Column<string>(type: "text", nullable: false),
                    root_id = table.Column<int>(type: "integer", nullable: true),
                    occurrences = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    qac_ref = table.Column<string>(type: "text", nullable: true),
                    ar_lemma_id = table.Column<int>(type: "integer", nullable: true),
                    etymological_only = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    origin = table.Column<string>(type: "text", nullable: true),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    freq = table.Column<int>(type: "integer", nullable: true),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("lemma_pkey", x => x.id);
                    table.CheckConstraint("lemma_lang_check", "lang IN ('ar','tr')");
                    table.ForeignKey(
                        name: "lemma_ar_lemma_id_fkey",
                        column: x => x.ar_lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "lemma_root_id_fkey",
                        column: x => x.root_id,
                        principalSchema: "icerik",
                        principalTable: "root",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "lemma_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "lemma_gloss",
                schema: "icerik",
                columns: table => new
                {
                    lemma_id = table.Column<int>(type: "integer", nullable: false),
                    anlam_kisa = table.Column<string>(type: "text", nullable: false),
                    kuran_anlamlari = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "[]"),
                    turkce_es_kelime = table.Column<string>(type: "text", nullable: true),
                    yalnizca_etimolojik = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    editor_notu = table.Column<string>(type: "text", nullable: true),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    origin = table.Column<string>(type: "text", nullable: false),
                    version = table.Column<string>(type: "text", nullable: false),
                    content_hash = table.Column<string>(type: "char(64)", nullable: false),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("lemma_gloss_pkey", x => x.lemma_id);
                    table.ForeignKey(
                        name: "lemma_gloss_lemma_id_fkey",
                        column: x => x.lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                });

            migrationBuilder.CreateTable(
                name: "quran_word",
                schema: "icerik",
                columns: table => new
                {
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    surah = table.Column<short>(type: "smallint", nullable: false),
                    ayah = table.Column<short>(type: "smallint", nullable: false),
                    word = table.Column<short>(type: "smallint", nullable: false),
                    ayah_index = table.Column<short>(type: "smallint", nullable: false),
                    text_uthmani = table.Column<string>(type: "text", nullable: false),
                    norm = table.Column<string>(type: "text", nullable: false),
                    char_start = table.Column<int>(type: "integer", nullable: false),
                    char_end = table.Column<int>(type: "integer", nullable: false),
                    root_id = table.Column<int>(type: "integer", nullable: true),
                    lemma_id = table.Column<int>(type: "integer", nullable: true),
                    pos = table.Column<string>(type: "text", nullable: true),
                    features = table.Column<string>(type: "jsonb", nullable: true),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    morph_source = table.Column<string>(type: "text", nullable: true),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("quran_word_pkey", x => x.anchor);
                    table.CheckConstraint("quran_word_check", "char_start < char_end");
                    table.ForeignKey(
                        name: "quran_word_lemma_id_fkey",
                        column: x => x.lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "quran_word_morph_source_fkey",
                        column: x => x.morph_source,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                    table.ForeignKey(
                        name: "quran_word_root_id_fkey",
                        column: x => x.root_id,
                        principalSchema: "icerik",
                        principalTable: "root",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "quran_word_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateTable(
                name: "tr_form",
                schema: "icerik",
                columns: table => new
                {
                    key_narrow = table.Column<string>(type: "text", nullable: false),
                    tr_lemma_id = table.Column<int>(type: "integer", nullable: false),
                    key_wide = table.Column<string>(type: "text", nullable: false),
                    freq = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("tr_form_pkey", x => new { x.key_narrow, x.tr_lemma_id });
                    table.ForeignKey(
                        name: "tr_form_tr_lemma_id_fkey",
                        column: x => x.tr_lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                });

            migrationBuilder.CreateTable(
                name: "tr_root_index",
                schema: "icerik",
                columns: table => new
                {
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    span_start = table.Column<int>(type: "integer", nullable: false),
                    span_end = table.Column<int>(type: "integer", nullable: false),
                    root_id = table.Column<int>(type: "integer", nullable: false),
                    tr_lemma_id = table.Column<int>(type: "integer", nullable: false),
                    etymological_only = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("tr_root_index_pkey", x => new { x.anchor, x.span_start });
                    table.CheckConstraint("tr_root_index_check", "span_start < span_end");
                    table.ForeignKey(
                        name: "tr_root_index_root_id_fkey",
                        column: x => x.root_id,
                        principalSchema: "icerik",
                        principalTable: "root",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "tr_root_index_tr_lemma_id_fkey",
                        column: x => x.tr_lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                });

            migrationBuilder.CreateIndex(
                name: "page_map_source_id_volume_page_line_key",
                schema: "icerik",
                table: "page_map",
                columns: new[] { "source_id", "volume", "page", "line" },
                unique: true)
                .Annotation("Npgsql:NullsDistinct", false);

            migrationBuilder.CreateIndex(
                name: "page_map_start",
                schema: "icerik",
                table: "page_map",
                column: "start_anchor");

            migrationBuilder.CreateIndex(
                name: "quran_word_ayah",
                schema: "icerik",
                table: "quran_word",
                columns: new[] { "ayah_index", "word" });

            migrationBuilder.CreateIndex(
                name: "quran_word_lemma",
                schema: "icerik",
                table: "quran_word",
                column: "lemma_id");

            migrationBuilder.CreateIndex(
                name: "quran_word_root",
                schema: "icerik",
                table: "quran_word",
                column: "root_id");

            migrationBuilder.CreateIndex(
                name: "quran_word_surah_ayah_word_key",
                schema: "icerik",
                table: "quran_word",
                columns: new[] { "surah", "ayah", "word" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "quran_word_fix_anchor_field_key",
                schema: "icerik",
                table: "quran_word_fix",
                columns: new[] { "anchor", "field" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "release_surum_derleme_key",
                schema: "icerik",
                table: "release",
                columns: new[] { "surum", "derleme" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "review_queue",
                schema: "icerik",
                table: "review",
                columns: new[] { "hedef_tablo", "created_at" },
                filter: "durum = 'acik'");

            migrationBuilder.CreateIndex(
                name: "review_xref",
                schema: "icerik",
                table: "review",
                column: "xref_id",
                filter: "xref_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_role_claims_role_id",
                schema: "kimlik",
                table: "role_claims",
                column: "role_id");

            migrationBuilder.CreateIndex(
                name: "ix_roles_normalized_name",
                schema: "kimlik",
                table: "roles",
                column: "normalized_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "root_letters_key",
                schema: "icerik",
                table: "root",
                column: "letters",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "tr_form_wide",
                schema: "icerik",
                table: "tr_form",
                column: "key_wide");

            migrationBuilder.CreateIndex(
                name: "tr_root_index_root",
                schema: "icerik",
                table: "tr_root_index",
                columns: new[] { "root_id", "anchor" });

            migrationBuilder.CreateIndex(
                name: "unit_anchor_key",
                schema: "icerik",
                table: "unit",
                column: "anchor",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "unit_ayah",
                schema: "icerik",
                table: "unit",
                column: "ayah_range")
                .Annotation("Npgsql:IndexMethod", "gist");

            migrationBuilder.CreateIndex(
                name: "unit_parent",
                schema: "icerik",
                table: "unit",
                columns: new[] { "parent_path", "ord" });

            migrationBuilder.CreateIndex(
                name: "unit_source_ord",
                schema: "icerik",
                table: "unit",
                columns: new[] { "source_id", "ord" });

            migrationBuilder.CreateIndex(
                name: "unit_tsv_ar",
                schema: "icerik",
                table: "unit",
                column: "tsv_ar")
                .Annotation("Npgsql:IndexMethod", "gin");

            migrationBuilder.CreateIndex(
                name: "unit_tsv_tr",
                schema: "icerik",
                table: "unit",
                column: "tsv_tr")
                .Annotation("Npgsql:IndexMethod", "gin");

            migrationBuilder.CreateIndex(
                name: "ix_user_claims_user_id",
                schema: "kimlik",
                table: "user_claims",
                column: "user_id");

            migrationBuilder.CreateIndex(
                name: "ix_user_logins_user_id",
                schema: "kimlik",
                table: "user_logins",
                column: "user_id");

            migrationBuilder.CreateIndex(
                name: "ix_user_roles_role_id",
                schema: "kimlik",
                table: "user_roles",
                column: "role_id");

            migrationBuilder.CreateIndex(
                name: "ix_users_normalized_email",
                schema: "kimlik",
                table: "users",
                column: "normalized_email");

            migrationBuilder.CreateIndex(
                name: "ix_users_normalized_user_name",
                schema: "kimlik",
                table: "users",
                column: "normalized_user_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "xref_dst",
                schema: "icerik",
                table: "xref",
                columns: new[] { "dst_anchor", "type" });

            migrationBuilder.CreateIndex(
                name: "xref_queue",
                schema: "icerik",
                table: "xref",
                columns: new[] { "type", "confidence" },
                descending: new[] { false, true },
                filter: "status = 'aday'");

            migrationBuilder.CreateIndex(
                name: "xref_src",
                schema: "icerik",
                table: "xref",
                columns: new[] { "src_anchor", "type" });

            // EF Core ifade edemez: hat bu kisiti ON CONFLICT ON CONSTRAINT ile hedefler (K-37 madde 4).
            migrationBuilder.Sql(
                "ALTER TABLE icerik.xref ADD CONSTRAINT xref_natural_key "
                + "UNIQUE NULLS NOT DISTINCT (type, src_anchor, src_span, dst_anchor, dst_span);");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "audio_timing",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "ayah_box",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "hadith_location",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "hadith_number_map",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "lemma_gloss",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "page_map",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "quran_word",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "quran_word_fix",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "release",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "review",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "role_claims",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "surah_alias",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "tr_form",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "tr_root_index",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "unit",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "user_claims",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "user_logins",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "user_roles",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "user_tokens",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "xref",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "lemma",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "pipeline_run",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "roles",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "users",
                schema: "kimlik");

            migrationBuilder.DropTable(
                name: "root",
                schema: "icerik");

            migrationBuilder.DropTable(
                name: "source",
                schema: "icerik");
        }
    }
}
