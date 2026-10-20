"""`mutalaa` komut satiri girisi."""

import typer

app = typer.Typer(
    name="mutalaa",
    help="Mutalaa icerik hatti.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Mutalaa icerik hatti komutlari."""
