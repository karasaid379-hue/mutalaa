using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Mutalaa.Domain.Links;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddLugatMadde : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "review_hedef_tablo_check",
                schema: "icerik",
                table: "review");

            migrationBuilder.CreateTable(
                name: "lugat_madde",
                schema: "icerik",
                columns: table => new
                {
                    id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityAlwaysColumn),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    basliksoz = table.Column<string>(type: "text", nullable: false),
                    basliksoz_norm = table.Column<string>(type: "text", nullable: false),
                    osmanlica_yazim = table.Column<string>(type: "text", nullable: true),
                    koken_dil = table.Column<string>(type: "text", nullable: true),
                    tanim_tr = table.Column<string>(type: "text", nullable: true),
                    ar_kok_id = table.Column<int>(type: "integer", nullable: true),
                    kaynaklar = table.Column<string>(type: "jsonb", nullable: false, defaultValue: "{}"),
                    duzey = table.Column<short>(type: "smallint", nullable: false),
                    status = table.Column<XrefStatus>(type: "icerik.xref_status", nullable: false, defaultValue: XrefStatus.Aday),
                    origin = table.Column<string>(type: "text", nullable: false),
                    version = table.Column<string>(type: "text", nullable: false, defaultValue: "1"),
                    content_hash = table.Column<string>(type: "char(64)", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    created_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    updated_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("lugat_madde_pkey", x => x.id);
                    table.UniqueConstraint("lugat_madde_source_id_basliksoz_key", x => new { x.source_id, x.basliksoz });
                    table.CheckConstraint("lugat_madde_content_hash_check", "content_hash ~ '^[0-9a-f]{64}$'");
                    table.CheckConstraint("lugat_madde_onayli_tanim_check", "status <> 'onayli' OR (tanim_tr IS NOT NULL AND btrim(tanim_tr) <> '')");
                    table.CheckConstraint("lugat_madde_origin_check", "origin IN ('hat','editor')");
                    table.ForeignKey(
                        name: "lugat_madde_ar_kok_id_fkey",
                        column: x => x.ar_kok_id,
                        principalSchema: "icerik",
                        principalTable: "root",
                        principalColumn: "id");
                    table.ForeignKey(
                        name: "lugat_madde_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.AddCheckConstraint(
                name: "review_hedef_tablo_check",
                schema: "icerik",
                table: "review",
                sql: "hedef_tablo IN ('source','unit','quran_word_fix','lemma','lemma_gloss','root','tr_root_index','tr_form','surah_alias','xref','page_map','ayah_box','audio_timing','lugat_madde')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "lugat_madde",
                schema: "icerik");

            // Eski CHECK 'lugat_madde' hedefini kabul etmez; tablo dusurulurken bu incelemelerin hedefi de gider.
            migrationBuilder.Sql("DELETE FROM icerik.review WHERE hedef_tablo = 'lugat_madde';");

            migrationBuilder.DropCheckConstraint(
                name: "review_hedef_tablo_check",
                schema: "icerik",
                table: "review");

            migrationBuilder.AddCheckConstraint(
                name: "review_hedef_tablo_check",
                schema: "icerik",
                table: "review",
                sql: "hedef_tablo IN ('source','unit','quran_word_fix','lemma','lemma_gloss','root','tr_root_index','tr_form','surah_alias','xref','page_map','ayah_box','audio_timing')");
        }
    }
}
