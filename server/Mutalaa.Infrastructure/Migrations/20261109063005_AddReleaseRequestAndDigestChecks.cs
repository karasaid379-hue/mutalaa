using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddReleaseRequestAndDigestChecks : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "release_surum_derleme_key",
                schema: "icerik",
                table: "release");

            migrationBuilder.AddColumn<int>(
                name: "kaynak_release_id",
                schema: "icerik",
                table: "release",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "notlar",
                schema: "icerik",
                table: "release",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string[]>(
                name: "paketler",
                schema: "icerik",
                table: "release",
                type: "text[]",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "talep",
                schema: "icerik",
                table: "release",
                type: "text",
                nullable: false,
                defaultValue: "yayin");

            migrationBuilder.AddCheckConstraint(
                name: "source_dosya_sha256_check",
                schema: "icerik",
                table: "source",
                sql: "dosya_sha256 ~ '^[0-9a-f]{64}$'");

            migrationBuilder.CreateIndex(
                name: "release_surum_derleme_key",
                schema: "icerik",
                table: "release",
                columns: new[] { "surum", "derleme" },
                unique: true,
                filter: "durum <> 'basarisiz'::icerik.surum_durumu");

            migrationBuilder.AddCheckConstraint(
                name: "release_talep_check",
                schema: "icerik",
                table: "release",
                sql: "talep IN ('yayin','terfi','geri_alma')");

            migrationBuilder.AddCheckConstraint(
                name: "lemma_gloss_content_hash_check",
                schema: "icerik",
                table: "lemma_gloss",
                sql: "content_hash ~ '^[0-9a-f]{64}$'");

            migrationBuilder.AddCheckConstraint(
                name: "audio_timing_file_sha256_check",
                schema: "icerik",
                table: "audio_timing",
                sql: "file_sha256 ~ '^[0-9a-f]{64}$'");

            migrationBuilder.AddForeignKey(
                name: "release_kaynak_release_id_fkey",
                schema: "icerik",
                table: "release",
                column: "kaynak_release_id",
                principalSchema: "icerik",
                principalTable: "release",
                principalColumn: "id");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "release_kaynak_release_id_fkey",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropCheckConstraint(
                name: "source_dosya_sha256_check",
                schema: "icerik",
                table: "source");

            migrationBuilder.DropIndex(
                name: "release_surum_derleme_key",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropCheckConstraint(
                name: "release_talep_check",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropCheckConstraint(
                name: "lemma_gloss_content_hash_check",
                schema: "icerik",
                table: "lemma_gloss");

            migrationBuilder.DropCheckConstraint(
                name: "audio_timing_file_sha256_check",
                schema: "icerik",
                table: "audio_timing");

            migrationBuilder.DropColumn(
                name: "kaynak_release_id",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropColumn(
                name: "notlar",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropColumn(
                name: "paketler",
                schema: "icerik",
                table: "release");

            migrationBuilder.DropColumn(
                name: "talep",
                schema: "icerik",
                table: "release");

            migrationBuilder.CreateIndex(
                name: "release_surum_derleme_key",
                schema: "icerik",
                table: "release",
                columns: new[] { "surum", "derleme" },
                unique: true);
        }
    }
}
