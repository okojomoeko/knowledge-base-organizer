"""
AI Services CLI Commands

This module provides CLI commands for managing AI service configuration
and checking service availability.
"""

import datetime
import json
import traceback
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from knowledge_base_organizer.cli.di_setup import (
    create_ai_config_file,
    get_ai_config_template,
    setup_cli_dependencies,
)

app = typer.Typer(
    name="ai",
    help="AI services configuration and management",
)
console = Console()


@app.command()
def status(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Check AI services status and availability."""
    console.print("[bold blue]🤖 AI Services Status[/bold blue]")

    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    try:
        # Set up dependencies
        dependencies = setup_cli_dependencies(vault_path)

        # Get service status
        status_info = dependencies.get_service_status()

        # Display overall status
        if status_info["ai_available"]:
            console.print("[green]✓[/green] AI services are available and configured")
        else:
            console.print("[red]✗[/red] AI services are not fully available")

        # Create status table
        table = Table(title="Service Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        for service_name, service_info in status_info.items():
            if service_name == "ai_available":
                continue

            status_icon = "✓" if service_info["available"] else "✗"
            status_color = "green" if service_info["available"] else "red"

            details = ""
            if service_info["available"]:
                if "model_info" in service_info:
                    model_info = service_info["model_info"]
                    details = f"Model: {model_info.get('name', 'Unknown')}"
                elif "index_stats" in service_info:
                    index_stats = service_info["index_stats"]
                    details = f"Documents: {index_stats.get('document_count', 0)}"
            else:
                details = service_info.get("error", "Unknown error")

            table.add_row(
                service_name.replace("_", " ").title(),
                f"[{status_color}]{status_icon}[/{status_color}]",
                details,
            )

        console.print(table)

        # Show verbose information
        if verbose:
            console.print("\n[bold yellow]📋 Detailed Information[/bold yellow]")
            console.print(json.dumps(status_info, indent=2, default=str))

    except Exception as e:
        console.print(f"[red]✗[/red] Error checking AI services: {e}")
        if verbose:
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1) from e


@app.command()
def init_config(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing configuration"
    ),
    template: bool = typer.Option(
        False, "--template", help="Show configuration template without creating file"
    ),
) -> None:
    """Initialize AI services configuration file."""
    if template:
        console.print("[bold blue]🤖 AI Configuration Template[/bold blue]")
        template_config = get_ai_config_template()
        console.print(json.dumps(template_config, indent=2))
        return

    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    config_path = vault_path / ".kiro" / "ai_config.yaml"

    if config_path.exists() and not force:
        console.print(f"[yellow]⚠[/yellow] Configuration already exists: {config_path}")
        console.print("Use --force to overwrite or edit the file manually")
        return

    try:
        created_path = create_ai_config_file(vault_path)
        console.print(f"[green]✓[/green] AI configuration created: {created_path}")
        console.print("\n[dim]You can now edit the configuration file to customize:")
        console.print("- Ollama server URL and models")
        console.print("- Vector store settings")
        console.print("- LLM parameters[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] Error creating configuration: {e}")
        raise typer.Exit(1) from e


@app.command()
def test_connection(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    service: str = typer.Option(
        "all", "--service", help="Service to test (all, embedding, llm, vector_store)"
    ),
) -> None:
    """Test connection to AI services."""
    console.print("[bold blue]🔌 Testing AI Service Connections[/bold blue]")

    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    try:
        dependencies = setup_cli_dependencies(vault_path)

        services_to_test = []
        if service == "all":
            services_to_test = ["embedding", "llm", "vector_store"]
        elif service in ["embedding", "llm", "vector_store"]:
            services_to_test = [service]
        else:
            console.print(f"[red]✗[/red] Unknown service: {service}")
            console.print("Valid services: all, embedding, llm, vector_store")
            raise typer.Exit(1)

        results = {}

        for service_name in services_to_test:
            console.print(f"\n[cyan]Testing {service_name} service...[/cyan]")

            try:
                if service_name == "embedding":
                    # Test embedding service
                    embedding_service = dependencies.embedding_service
                    model_info = embedding_service.get_model_info()

                    # Test actual embedding generation
                    result = embedding_service.create_embedding("test text")

                    results[service_name] = {
                        "status": "success",
                        "model_info": model_info,
                        "test_result": {
                            "dimension": result.dimension,
                            "model_name": result.model_name,
                        },
                    }
                    console.print("[green]✓[/green] Embedding service working")
                    console.print(f"  Model: {result.model_name}")
                    console.print(f"  Dimension: {result.dimension}")

                elif service_name == "llm":
                    # Test LLM service
                    llm_service = dependencies.llm_service
                    model_info = llm_service.get_model_info()

                    # Test actual text generation
                    summary = llm_service.summarize_content(
                        "This is a test document for AI service testing.", max_length=50
                    )

                    results[service_name] = {
                        "status": "success",
                        "model_info": model_info,
                        "test_result": {"summary_length": len(summary)},
                    }
                    console.print("[green]✓[/green] LLM service working")
                    console.print(f"  Model: {model_info.get('name', 'Unknown')}")
                    console.print(f"  Test summary: {summary[:50]}...")

                elif service_name == "vector_store":
                    # Test vector store
                    vector_store = dependencies.vector_store
                    stats = vector_store.get_index_stats()

                    # Test indexing and search
                    test_vector = [0.1] * 768  # Default dimension
                    vector_store.index_document("test_doc", test_vector, {"test": True})
                    search_results = vector_store.search(test_vector, k=1)

                    results[service_name] = {
                        "status": "success",
                        "index_stats": stats,
                        "test_result": {"search_results": len(search_results)},
                    }
                    console.print("[green]✓[/green] Vector store working")
                    console.print(
                        f"  Documents indexed: {stats.get('document_count', 0)}"
                    )
                    console.print(
                        f"  Test search returned: {len(search_results)} results"
                    )

            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "error": str(e),
                }
                console.print(f"[red]✗[/red] {service_name} service failed: {e}")

        # Summary
        console.print("\n[bold yellow]📋 Test Summary[/bold yellow]")
        successful = sum(1 for r in results.values() if r["status"] == "success")
        total = len(results)

        if successful == total:
            console.print(f"[green]✓[/green] All {total} services working correctly")
        else:
            console.print(f"[yellow]⚠[/yellow] {successful}/{total} services working")
            console.print("Check the errors above and your configuration")

    except Exception as e:
        console.print(f"[red]✗[/red] Error testing services: {e}")
        raise typer.Exit(1) from e


@app.command()
def config_info(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
) -> None:
    """Show current AI configuration information."""
    console.print("[bold blue]⚙️  AI Configuration Information[/bold blue]")

    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    config_path = vault_path / ".kiro" / "ai_config.yaml"

    if not config_path.exists():
        console.print(f"[yellow]⚠[/yellow] No AI configuration found at: {config_path}")
        console.print("Run 'ai init-config' to create a default configuration")
        return

    try:
        with config_path.open(encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        console.print(f"[green]✓[/green] Configuration file: {config_path}")
        console.print("\n[bold yellow]📋 Current Configuration[/bold yellow]")

        # Display configuration in a readable format
        ai_services = config_data.get("ai_services", {})

        for service_type, service_config in ai_services.items():
            console.print(f"\n[cyan]{service_type.title()} Service:[/cyan]")
            for key, value in service_config.items():
                console.print(f"  {key}: {value}")

        # Show file modification time
        mod_time = datetime.datetime.fromtimestamp(config_path.stat().st_mtime)
        console.print(
            f"\n[dim]Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
        )

    except Exception as e:
        console.print(f"[red]✗[/red] Error reading configuration: {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
