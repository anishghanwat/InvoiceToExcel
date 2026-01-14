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
    print("  python main.py interactive <document_file> - Interactive CSV creation")
    print("  python main.py help                       - Show this help")
    print()
    print("Examples:")
    print("  python main.py cli invoice.pdf")
    print("  python main.py interactive receipt.jpg")
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
        # Run interactive CSV creator
        if len(sys.argv) < 3:
            print("Error: Please provide a document file path")
            print("Usage: python main.py interactive <document_file>")
            return
        
        # Modify sys.argv for interactive interface
        sys.argv = ["interactive_csv.py", sys.argv[2]]
        interactive_main()
    
    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == '__main__':
    main()