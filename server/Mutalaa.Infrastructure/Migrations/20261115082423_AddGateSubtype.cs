using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mutalaa.Infrastructure.Migrations
{
    /// <summary>
    /// K-51 madde 5: kapi alt turu. xref_gate.alt_tur eklenir ve birincil anahtar (tur, alt_tur, set_sinifi) olur; CHECK tur-alt tur tutarliligini ister
    /// (benzer_ayet: sozluksel | alim; kok: tr_lemma | xref; digerleri bos). Var olan satirlar once bos alt tur alir; kok ve benzer_ayet icin bos alt tur
    /// gecersiz ve eski olcum hangi alt tura ait oldugu belli olmadigindan bu satirlar silinir (kapi yeniden olculene kadar kapali kalir: "kapi-olculmedi";
    /// satirlari qa gold yeniden yazar). Down alt turlu satirlari siler: eski sema onlari tasiyamaz.
    /// </summary>
    public partial class AddGateSubtype : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropPrimaryKey(
                name: "xref_gate_pkey",
                schema: "icerik",
                table: "xref_gate");

            migrationBuilder.AddColumn<string>(
                name: "alt_tur",
                schema: "icerik",
                table: "xref_gate",
                type: "text",
                nullable: false,
                defaultValue: "");

            // Kalici varsayilan yok: alt tur her yazimda acik verilir.
            migrationBuilder.Sql("ALTER TABLE icerik.xref_gate ALTER COLUMN alt_tur DROP DEFAULT;");

            migrationBuilder.Sql("DELETE FROM icerik.xref_gate WHERE alt_tur = '' AND tur IN ('kok', 'benzer_ayet');");

            migrationBuilder.AddPrimaryKey(
                name: "xref_gate_pkey",
                schema: "icerik",
                table: "xref_gate",
                columns: new[] { "tur", "alt_tur", "set_sinifi" });

            migrationBuilder.AddCheckConstraint(
                name: "xref_gate_alt_tur_check",
                schema: "icerik",
                table: "xref_gate",
                sql: "alt_tur IN ('','sozluksel','alim','tr_lemma','xref') AND ((tur = 'benzer_ayet' AND alt_tur IN ('sozluksel','alim')) OR (tur = 'kok' AND alt_tur IN ('tr_lemma','xref')) OR (tur NOT IN ('benzer_ayet','kok') AND alt_tur = ''))");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropPrimaryKey(
                name: "xref_gate_pkey",
                schema: "icerik",
                table: "xref_gate");

            migrationBuilder.DropCheckConstraint(
                name: "xref_gate_alt_tur_check",
                schema: "icerik",
                table: "xref_gate");

            migrationBuilder.Sql("DELETE FROM icerik.xref_gate WHERE alt_tur <> '';");

            migrationBuilder.DropColumn(
                name: "alt_tur",
                schema: "icerik",
                table: "xref_gate");

            migrationBuilder.AddPrimaryKey(
                name: "xref_gate_pkey",
                schema: "icerik",
                table: "xref_gate",
                columns: new[] { "tur", "set_sinifi" });
        }
    }
}
