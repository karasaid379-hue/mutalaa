using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddLugatAnlam : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // K-51 madde 14. Genislet: anlam_no DEFAULT 1 mevcut satirlarin hepsini 1 yapar (tasima); daralt: tekillik
            // (source_id, basliksoz, anlam_no) olur, origin CHECK'ine 'kaynak' eklenir. Ayni transaction'da calisir.
            migrationBuilder.DropUniqueConstraint(
                name: "lugat_madde_source_id_basliksoz_key",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.DropCheckConstraint(
                name: "lugat_madde_origin_check",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.AddColumn<short>(
                name: "anlam_no",
                schema: "icerik",
                table: "lugat_madde",
                type: "smallint",
                nullable: false,
                defaultValue: (short)1);

            migrationBuilder.AddUniqueConstraint(
                name: "lugat_madde_source_id_basliksoz_anlam_no_key",
                schema: "icerik",
                table: "lugat_madde",
                columns: new[] { "source_id", "basliksoz", "anlam_no" });

            migrationBuilder.AddCheckConstraint(
                name: "lugat_madde_anlam_no_check",
                schema: "icerik",
                table: "lugat_madde",
                sql: "anlam_no >= 1");

            migrationBuilder.AddCheckConstraint(
                name: "lugat_madde_duzey_check",
                schema: "icerik",
                table: "lugat_madde",
                sql: "duzey BETWEEN 1 AND 4");

            migrationBuilder.AddCheckConstraint(
                name: "lugat_madde_origin_check",
                schema: "icerik",
                table: "lugat_madde",
                sql: "origin IN ('hat','editor','kaynak')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Eski sema ikinci anlami ve 'kaynak' kokenini tasiyamaz: bu satirlar hat tarafindan yeniden yuklenebilir (K-51 madde 14).
            migrationBuilder.Sql("DELETE FROM icerik.lugat_madde WHERE anlam_no > 1 OR origin = 'kaynak';");

            migrationBuilder.DropUniqueConstraint(
                name: "lugat_madde_source_id_basliksoz_anlam_no_key",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.DropCheckConstraint(
                name: "lugat_madde_anlam_no_check",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.DropCheckConstraint(
                name: "lugat_madde_duzey_check",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.DropCheckConstraint(
                name: "lugat_madde_origin_check",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.DropColumn(
                name: "anlam_no",
                schema: "icerik",
                table: "lugat_madde");

            migrationBuilder.AddUniqueConstraint(
                name: "lugat_madde_source_id_basliksoz_key",
                schema: "icerik",
                table: "lugat_madde",
                columns: new[] { "source_id", "basliksoz" });

            migrationBuilder.AddCheckConstraint(
                name: "lugat_madde_origin_check",
                schema: "icerik",
                table: "lugat_madde",
                sql: "origin IN ('hat','editor')");
        }
    }
}
