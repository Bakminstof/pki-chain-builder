from rich.console import Console
from rich.prompt import Prompt

from core.models import CASubject
from core.settings import settings

CONSOLE = Console()

LINE_SYMBOL = "="
LINE_LENGTH = 60

type CommonName = str
type AltNames = list[str]


def make_title(
    input_string: str,
    *,
    line_symbol: str = LINE_SYMBOL,
    line_length: int = LINE_LENGTH,
) -> str:
    return f"{f"| {input_string} |":{line_symbol}^{line_length}}"


def input_names(
    common_name: CommonName | None = None,
    alt_names: AltNames | None = None,
) -> tuple[CommonName, AltNames]:
    if common_name is None:
        common_name = Prompt.ask(
            "[bold yellow]Common name (CN)[/bold yellow]",
            default=settings.intermediate_ca.crl_server.host,
        )

    if alt_names is None:
        alt_names = Prompt.ask(
            "[bold yellow]Alt names (SAN)[/bold yellow]",
            default=f"{settings.intermediate_ca.crl_server.host};my-server.com;mail.my-server.com",
        ).split(";")

    CONSOLE.print(f"[cyan]CN:[/cyan] [bold white]{common_name}[/bold white]")
    CONSOLE.print(f"[cyan]SAN:[/cyan] [bold white]{alt_names}[/bold white]")

    return common_name, alt_names


def input_crl_server_info(
    crl_server_host: str | None = None,
    crl_server_port: int | None = None,
) -> tuple[str, int]:
    if crl_server_host is None:
        crl_server_host = Prompt.ask(
            "[bold yellow]CRL distribution point (DP) host[/bold yellow]",
            default=settings.intermediate_ca.crl_server.host,
        )

    if crl_server_port is None:
        crl_server_port = Prompt.ask(
            "[bold yellow]CRL distribution point (DP) port[/bold yellow]",
            default=str(settings.intermediate_ca.crl_server.port),
        )

    CONSOLE.print(f"[cyan]CRL DP host:[/cyan] [bold white]{crl_server_host}[/bold white]")
    CONSOLE.print(f"[cyan]CRL DP port:[/cyan] [bold white]{crl_server_port}[/bold white]")

    return crl_server_host, int(crl_server_port)


def input_subject(
    country_name: str | None = None,
    organization_name: str | None = None,
    common_name: str | None = None,
) -> CASubject:
    if country_name is None:
        country_name = Prompt.ask(
            "[bold yellow]Country (2 letters) (C)[/bold yellow]", default="US"
        )

    if organization_name is None:
        organization_name = Prompt.ask(
            "[bold yellow]Organization (O)[/bold yellow]", default="Example Ltd"
        )

    if common_name is None:
        common_name = Prompt.ask(
            "[bold yellow]Common Name (CN)[/bold yellow]", default="example.com"
        )

    CONSOLE.print(f"[cyan]C:[/cyan] [bold white]{country_name}[/bold white]")
    CONSOLE.print(f"[cyan]O:[/cyan] [bold white]{organization_name}[/bold white]")
    CONSOLE.print(f"[cyan]CN:[/cyan] [bold white]{common_name}[/bold white]")

    return CASubject(
        country_name=country_name,
        organization_name=organization_name,
        common_name=common_name,
    )
