using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddLemmaWave : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "lemma_dalga",
                schema: "icerik",
                columns: table => new
                {
                    lemma_id = table.Column<int>(type: "integer", nullable: false),
                    dalga = table.Column<short>(type: "smallint", nullable: false),
                    sira = table.Column<int>(type: "integer", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("lemma_dalga_pkey", x => x.lemma_id);
                    table.CheckConstraint("lemma_dalga_dalga_check", "dalga BETWEEN 0 AND 4");
                    table.ForeignKey(
                        name: "lemma_dalga_lemma_id_fkey",
                        column: x => x.lemma_id,
                        principalSchema: "icerik",
                        principalTable: "lemma",
                        principalColumn: "id");
                });

            migrationBuilder.CreateIndex(
                name: "root_letters_bw_key",
                schema: "icerik",
                table: "root",
                column: "letters_bw",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "lemma_qac_ref_key",
                schema: "icerik",
                table: "lemma",
                column: "qac_ref",
                unique: true,
                filter: "lang = 'ar'");

            migrationBuilder.CreateIndex(
                name: "lemma_dalga_dalga_sira",
                schema: "icerik",
                table: "lemma_dalga",
                columns: new[] { "dalga", "sira" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "lemma_dalga",
                schema: "icerik");

            migrationBuilder.DropIndex(
                name: "root_letters_bw_key",
                schema: "icerik",
                table: "root");

            migrationBuilder.DropIndex(
                name: "lemma_qac_ref_key",
                schema: "icerik",
                table: "lemma");
        }
    }
}
