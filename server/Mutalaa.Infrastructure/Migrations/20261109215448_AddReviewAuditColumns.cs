using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddReviewAuditColumns : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "duzenlenen",
                schema: "icerik",
                table: "review",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "ikinci_gerekce",
                schema: "icerik",
                table: "review",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<DateTime>(
                name: "ikinci_incelendi_at",
                schema: "icerik",
                table: "review",
                type: "timestamp with time zone",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "duzenlenen",
                schema: "icerik",
                table: "review");

            migrationBuilder.DropColumn(
                name: "ikinci_gerekce",
                schema: "icerik",
                table: "review");

            migrationBuilder.DropColumn(
                name: "ikinci_incelendi_at",
                schema: "icerik",
                table: "review");
        }
    }
}
