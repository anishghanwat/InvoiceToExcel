"""
Main entry point for the InvoiceToExcel application.
"""
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.interfaces.cli import main as cli_main
from src.interfaces.interactive_csv import main as interactive_main


def show_help():
    """Show help information."""
    print("InvoiceToExcel - Document Text Extraction and CSV Conversion")
    print("=" * 60)
    print("Usage:")
    print("  python main.py cli <document_file>        - Simple extraction")
    print("  python main.py interactive                 - Interactive CSV creation (new flow)")
    print("  python main.py bulk <command>             - Bulk processing (see bulk help)")
    print("  python main.py help                       - Show this help")
    print()
    print("Examples:")
    print("  python main.py cli invoice.pdf")
    print("  python main.py interactive                 # Will prompt for template and files")
    print("  python main.py bulk process-dir ./invoices")
    print()
    print("Supported formats: PDF, PNG, JPG, JPEG")


def main():
    """Main application entry point."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help" or command == "--help" or command == "-h":
        show_help()
    elif command == "cli":
        # Run CLI interface
        if len(sys.argv) < 3:
            print("Error: Please provide a document file path")
            print("Usage: python main.py cli <document_file>")
            return
        
        # Modify sys.argv for CLI interface
        sys.argv = ["cli.py", sys.argv[2]]
        cli_main()
    
    elif command == "interactive":
        # Run interactive CSV creator (new flow - prompts for template and files)
        # No file path required - the interactive mode will ask for everything
        interactive_main()
    
    elif command == "bulk":
        # Run bulk processing CLI
        from src.interfaces.bulk_cli import main as bulk_main
        # Remove 'bulk' from args and pass rest to bulk CLI
        sys.argv = ["bulk_cli"] + sys.argv[2:]
        bulk_main()
    
    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == '__main__':
    main()