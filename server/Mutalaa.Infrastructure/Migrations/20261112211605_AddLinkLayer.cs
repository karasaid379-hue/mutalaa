using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Mutalaa.Domain.Links;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddLinkLayer : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Enum etiketi ham SQL ile eklenir: EF'nin uretecegi Down etiketi geri alamaz (PostgreSQL enum etiketi silmez), IF NOT EXISTS ise
            // Down sonrasi yeniden Up'in calismasini saglar. Yeni etiket ayni islemde kullanilmaz (PostgreSQL 12+ islem icinde ekler).
            migrationBuilder.Sql("ALTER TYPE icerik.inceleme_durumu ADD VALUE IF NOT EXISTS 'uzmanda';");

            migrationBuilder.AddColumn<string>(
                name: "unit_hash",
                schema: "icerik",
                table: "tr_root_index",
                type: "char(16)",
                nullable: false,
                defaultValue: "0000000000000000");

            migrationBuilder.AddColumn<string>(
                name: "data_version",
                schema: "icerik",
                table: "tr_form",
                type: "text",
                nullable: false,
                defaultValue: "oncesi");

            // Gecici varsayilanlar yalniz dolu tablo icindir (K-51 madde 1: hat bu tablolari her kosuda yeniden uretir); kalici varsayilan yok.
            migrationBuilder.Sql("ALTER TABLE icerik.tr_root_index ALTER COLUMN unit_hash DROP DEFAULT;");
            migrationBuilder.Sql("ALTER TABLE icerik.tr_form ALTER COLUMN data_version DROP DEFAULT;");

            migrationBuilder.AddColumn<string>(
                name: "kanit",
                schema: "icerik",
                table: "lemma",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "onay_yolu",
                schema: "icerik",
                table: "lemma",
                type: "text",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "xref_gate",
                schema: "icerik",
                columns: table => new
                {
                    tur = table.Column<XrefType>(type: "icerik.xref_type", nullable: false),
                    set_sinifi = table.Column<string>(type: "text", nullable: false),
                    set_surumu = table.Column<string>(type: "text", nullable: false),
                    sonuc = table.Column<string>(type: "text", nullable: false),
                    set_kaynaklari = table.Column<string[]>(type: "text[]", nullable: false),
                    rapor_sha256 = table.Column<string>(type: "char(64)", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    olculdu_at = table.Column<DateTime>(type: "timestamp with time zone", nullable: false, defaultValueSql: "now()"),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("xref_gate_pkey", x => new { x.tur, x.set_sinifi });
                    table.CheckConstraint("xref_gate_rapor_sha256_check", "rapor_sha256 ~ '^[0-9a-f]{64}$'");
                    table.CheckConstraint("xref_gate_set_sinifi_check", "set_sinifi IN ('altin','silver','sentetik')");
                    table.CheckConstraint("xref_gate_sonuc_check", "sonuc IN ('gecti','kaldi')");
                });

            migrationBuilder.AddCheckConstraint(
                name: "tr_root_index_unit_hash_check",
                schema: "icerik",
                table: "tr_root_index",
                sql: "unit_hash ~ '^[0-9a-f]{16}$'");

            migrationBuilder.CreateIndex(
                name: "lemma_tr_text_clean_key",
                schema: "icerik",
                table: "lemma",
                columns: new[] { "lang", "text_clean" },
                unique: true,
                filter: "lang = 'tr'");

            migrationBuilder.AddCheckConstraint(
                name: "lemma_onay_yolu_check",
                schema: "icerik",
                table: "lemma",
                sql: "onay_yolu IS NULL OR onay_yolu IN ('editor','otomatik')");

            migrationBuilder.AddCheckConstraint(
                name: "lemma_otomatik_kanit_check",
                schema: "icerik",
                table: "lemma",
                sql: "onay_yolu IS DISTINCT FROM 'otomatik' OR (kanit IS NOT NULL AND jsonb_typeof(kanit) = 'object')");

            migrationBuilder.AddCheckConstraint(
                name: "lemma_tr_onayli_onay_yolu_check",
                schema: "icerik",
                table: "lemma",
                sql: "NOT (lang = 'tr' AND status = 'onayli') OR onay_yolu IS NOT NULL");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "xref_gate",
                schema: "icerik");

            migrationBuilder.DropCheckConstraint(
                name: "tr_root_index_unit_hash_check",
                schema: "icerik",
                table: "tr_root_index");

            migrationBuilder.DropIndex(
                name: "lemma_tr_text_clean_key",
                schema: "icerik",
                table: "lemma");

            migrationBuilder.DropCheckConstraint(
                name: "lemma_onay_yolu_check",
                schema: "icerik",
                table: "lemma");

            migrationBuilder.DropCheckConstraint(
                name: "lemma_otomatik_kanit_check",
                schema: "icerik",
                table: "lemma");

            migrationBuilder.DropCheckConstraint(
                name: "lemma_tr_onayli_onay_yolu_check",
                schema: "icerik",
                table: "lemma");

            migrationBuilder.DropColumn(
                name: "unit_hash",
                schema: "icerik",
                table: "tr_root_index");

            migrationBuilder.DropColumn(
                name: "data_version",
                schema: "icerik",
                table: "tr_form");

            migrationBuilder.DropColumn(
                name: "kanit",
                schema: "icerik",
                table: "lemma");

            migrationBuilder.DropColumn(
                name: "onay_yolu",
                schema: "icerik",
                table: "lemma");

            // inceleme_durumu.uzmanda geri alinmaz: PostgreSQL enum etiketi silemez. Etiket kalir (zararsiz); Up IF NOT EXISTS kullanir.
        }
    }
}
