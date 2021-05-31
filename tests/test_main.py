from typer.testing import CliRunner

from bgraph.main import app

runner = CliRunner()


def test_app():
    """Test if we can run the app."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
