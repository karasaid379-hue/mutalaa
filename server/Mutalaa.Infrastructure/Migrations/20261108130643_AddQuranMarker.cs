using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddQuranMarker : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "quran_marker",
                schema: "icerik",
                columns: table => new
                {
                    kind = table.Column<string>(type: "text", nullable: false),
                    no = table.Column<short>(type: "smallint", nullable: false),
                    anchor = table.Column<string>(type: "text", nullable: false, collation: "C"),
                    secde_turu = table.Column<string>(type: "text", nullable: true),
                    source_id = table.Column<string>(type: "text", nullable: false),
                    data_version = table.Column<string>(type: "text", nullable: false),
                    xmin = table.Column<uint>(type: "xid", rowVersion: true, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("quran_marker_pkey", x => new { x.kind, x.no });
                    table.CheckConstraint("quran_marker_check", "(kind = 'secde') = (secde_turu IS NOT NULL)");
                    table.CheckConstraint("quran_marker_kind_check", "kind IN ('cuz','hizb','rub','secde')");
                    table.CheckConstraint("quran_marker_secde_turu_check", "secde_turu IN ('recommended','obligatory')");
                    table.ForeignKey(
                        name: "quran_marker_source_id_fkey",
                        column: x => x.source_id,
                        principalSchema: "icerik",
                        principalTable: "source",
                        principalColumn: "slug");
                });

            migrationBuilder.CreateIndex(
                name: "quran_marker_anchor",
                schema: "icerik",
                table: "quran_marker",
                column: "anchor");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "quran_marker",
                schema: "icerik");
        }
    }
}
