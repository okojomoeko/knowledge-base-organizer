"""CLI commands for LLM configuration and management."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..infrastructure.llm_config import get_llm_config_manager
from ..infrastructure.llm_factory import get_llm_service_factory

console = Console()
app = typer.Typer(name="llm", help="LLM configuration and management commands")


@app.command()
def list_providers(
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to LLM configuration file"
    ),
) -> None:
    """List available LLM providers and their configurations."""
    try:
        factory = get_llm_service_factory(config_path)
        providers = factory.list_available_providers()

        config_manager = get_llm_config_manager(config_path)
        config = config_manager.load_config()

        console.print("🤖 [bold blue]Available LLM Providers[/bold blue]\n")

        table = Table()
        table.add_column("Provider", style="cyan")
        table.add_column("Base URL", style="green")
        table.add_column("Model", style="yellow")
        table.add_column("API Format", style="magenta")
        table.add_column("Status", style="white")

        for provider_name in providers:
            provider_config = config.providers[provider_name]

            # Test connection
            try:
                factory.test_provider_connection(provider_name)
                status = "✅ Available"
            except Exception:
                status = "❌ Unavailable"

            # Mark default provider
            display_name = provider_name
            if provider_name == config.default_provider:
                display_name = f"{provider_name} (default)"

            table.add_row(
                display_name,
                provider_config.base_url,
                provider_config.model_name,
                provider_config.api_format,
                status,
            )

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error listing providers: {e}")
        raise typer.Exit(1) from e


@app.command()
def list_models(
    provider: str | None = typer.Option(
        None, "--provider", help="Provider name (uses default if not specified)"
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to LLM configuration file"
    ),
) -> None:
    """List available models for a provider."""
    try:
        factory = get_llm_service_factory(config_path)
        models = factory.list_available_models(provider)

        config_manager = get_llm_config_manager(config_path)
        config = config_manager.load_config()

        provider_name = provider or config.default_provider
        provider_config = config.providers[provider_name]

        console.print(
            f"🤖 [bold blue]Available Models for {provider_name}[/bold blue]\n"
        )

        table = Table()
        table.add_column("Model Name", style="cyan")
        table.add_column("Status", style="white")

        for model in models:
            # Mark current model
            display_name = model
            if model == provider_config.model_name:
                display_name = f"{model} (current)"
                status = "✅ Current"
            else:
                status = "Available"

            table.add_row(display_name, status)

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error listing models: {e}")
        raise typer.Exit(1) from e


@app.command()
def test_connection(
    provider: str | None = typer.Option(
        None, "--provider", help="Provider name (uses default if not specified)"
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to LLM configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Test connection to an LLM provider."""
    try:
        factory = get_llm_service_factory(config_path)

        config_manager = get_llm_config_manager(config_path)
        config = config_manager.load_config()

        provider_name = provider or config.default_provider

        console.print(f"🔍 Testing connection to {provider_name}...")

        # Test connection
        success = factory.test_provider_connection(provider_name)

        if success:
            console.print(
                f"✅ [green]Successfully connected to {provider_name}[/green]"
            )

            if verbose:
                # Get model info
                service = factory.create_llm_service(provider_name)
                model_info = service.get_model_info()

                console.print("\n📋 [bold blue]Model Information[/bold blue]")
                for key, value in model_info.items():
                    if key != "model_details":  # Skip complex nested data
                        console.print(f"  {key}: {value}")
        else:
            console.print(f"❌ [red]Failed to connect to {provider_name}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"❌ Error testing connection: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


@app.command()
def test_generation(
    provider: str | None = typer.Option(
        None, "--provider", help="Provider name (uses default if not specified)"
    ),
    model: str | None = typer.Option(
        None, "--model", help="Model name (uses provider default if not specified)"
    ),
    prompt: str = typer.Option(
        "Hello, how are you?", "--prompt", help="Test prompt to send"
    ),
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to LLM configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Test text generation with an LLM provider."""
    try:
        factory = get_llm_service_factory(config_path)

        config_manager = get_llm_config_manager(config_path)
        config = config_manager.load_config()

        provider_name = provider or config.default_provider

        console.print(f"🤖 Testing text generation with {provider_name}...")
        if model:
            console.print(f"Using model: {model}")

        # Create service
        service = factory.create_llm_service(provider_name, model)

        # Test summarization (simple generation test)
        console.print(f"Prompt: [dim]{prompt}[/dim]")

        response = service.summarize_content(prompt, max_length=200)

        console.print("\n📝 [bold blue]Generated Response[/bold blue]")
        console.print(f"[green]{response}[/green]")

        if verbose:
            model_info = service.get_model_info()
            console.print(f"\n📋 Model: {model_info.get('model_name', 'Unknown')}")
            console.print(f"Base URL: {model_info.get('base_url', 'Unknown')}")

    except Exception as e:
        console.print(f"❌ Error testing generation: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


@app.command()
def create_config(
    output_path: Path = typer.Option(
        Path.cwd() / "llm_config.yaml",
        "--output",
        "-o",
        help="Output path for configuration file",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing configuration file"
    ),
) -> None:
    """Create a new LLM configuration file template."""
    try:
        if output_path.exists() and not force:
            console.print(f"❌ Configuration file already exists: {output_path}")
            console.print("Use --force to overwrite")
            raise typer.Exit(1)

        config_manager = get_llm_config_manager()
        config_manager.create_user_config_template(output_path)

        console.print(
            f"✅ [green]Created LLM configuration template at: {output_path}[/green]"
        )
        console.print("\n📝 [bold blue]Next steps:[/bold blue]")
        console.print("1. Edit the configuration file to match your setup")
        console.print("2. Test the connection: [cyan]llm test-connection[/cyan]")
        console.print("3. Test generation: [cyan]llm test-generation[/cyan]")

    except Exception as e:
        console.print(f"❌ Error creating configuration: {e}")
        raise typer.Exit(1) from e


@app.command()
def show_config(
    config_path: Path | None = typer.Option(
        None, "--config", help="Path to LLM configuration file"
    ),
) -> None:
    """Show current LLM configuration."""
    try:
        config_manager = get_llm_config_manager(config_path)
        config = config_manager.load_config()

        console.print("🤖 [bold blue]Current LLM Configuration[/bold blue]\n")

        console.print(f"Default Provider: [cyan]{config.default_provider}[/cyan]")

        console.print("\n📋 [bold blue]Providers[/bold blue]")
        for name, provider_config in config.providers.items():
            console.print(f"\n[yellow]{name}[/yellow]:")
            console.print(f"  Base URL: {provider_config.base_url}")
            console.print(f"  Model: {provider_config.model_name}")
            console.print(f"  API Format: {provider_config.api_format}")
            console.print(f"  Timeout: {provider_config.timeout}s")

            if provider_config.alternative_models:
                console.print(
                    f"  Alternative Models: {', '.join(provider_config.alternative_models)}"
                )

        console.print("\n⚙️ [bold blue]Feature Settings[/bold blue]")
        console.print(f"  Max Tags: {config.metadata_suggestion.max_tags}")
        console.print(f"  Max Aliases: {config.metadata_suggestion.max_aliases}")
        console.print(
            f"  Default Summary Length: {config.summarization.default_max_length}"
        )

    except Exception as e:
        console.print(f"❌ Error showing configuration: {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
