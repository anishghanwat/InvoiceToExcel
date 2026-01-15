"""
Command-line interface for bulk invoice processing.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from src.core.bulk_processor import BulkInvoiceProcessor
from src.core.templates.template_parser import TemplateParser
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import settings


def progress_callback(current: int, total: int, filename: str):
    """Progress callback for bulk processing."""
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"\rProgress: {percentage:.1f}% ({current}/{total}) - {filename}", end="", flush=True)


def main():
    """Main CLI entry point for bulk processing."""
    parser = argparse.ArgumentParser(
        description="Bulk invoice processing with parallel execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all invoices in a directory
  python -m src.interfaces.bulk_cli process-dir ./invoices --output-dir ./output
  
  # Process with specific template
  python -m src.interfaces.bulk_cli process-dir ./invoices --template templates/gstr1.json
  
  # Process specific files
  python -m src.interfaces.bulk_cli process-files invoice1.pdf invoice2.pdf invoice3.pdf
  
  # Process with custom workers and no AI
  python -m src.interfaces.bulk_cli process-dir ./invoices --workers 5 --no-ai
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Process directory command
    dir_parser = subparsers.add_parser('process-dir', help='Process all invoices in a directory')
    dir_parser.add_argument('input_dir', help='Input directory containing invoice files')
    dir_parser.add_argument('--template', help='Template file path (JSON)')
    dir_parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')
    dir_parser.add_argument('--output-format', choices=['csv', 'json', 'excel'], default='csv',
                          help='Output format (default: csv)')
    dir_parser.add_argument('--workers', type=int, default=3,
                          help='Number of parallel workers (default: 3)')
    dir_parser.add_argument('--no-consolidated', action='store_true',
                          help='Do not create consolidated output file')
    dir_parser.add_argument('--skip-existing', action='store_true',
                          help='Skip files that already have output')
    dir_parser.add_argument('--no-ai', action='store_true',
                          help='Disable AI fixing')
    dir_parser.add_argument('--no-progress', action='store_true',
                          help='Disable progress output')
    
    # Process files command
    files_parser = subparsers.add_parser('process-files', help='Process specific invoice files')
    files_parser.add_argument('files', nargs='+', help='Invoice file paths')
    files_parser.add_argument('--template', help='Template file path (JSON)')
    files_parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')
    files_parser.add_argument('--output-format', choices=['csv', 'json', 'excel'], default='csv',
                            help='Output format (default: csv)')
    files_parser.add_argument('--workers', type=int, default=3,
                            help='Number of parallel workers (default: 3)')
    files_parser.add_argument('--no-consolidated', action='store_true',
                            help='Do not create consolidated output file')
    files_parser.add_argument('--no-ai', action='store_true',
                            help='Disable AI fixing')
    files_parser.add_argument('--no-progress', action='store_true',
                            help='Disable progress output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load template if provided
    template = None
    if args.template:
        template_parser = TemplateParser()
        template = template_parser.parse_from_file(args.template)
        print(f"📋 Using template: {args.template}")
    
    # Initialize bulk processor
    print(f"🚀 Initializing bulk processor (workers: {args.workers})...")
    processor = BulkInvoiceProcessor(
        max_workers=args.workers,
        use_ai=not args.no_ai,
        enable_logging=True
    )
    
    # Process based on command
    if args.command == 'process-dir':
        print(f"📁 Processing directory: {args.input_dir}")
        summary = processor.process_directory(
            input_dir=args.input_dir,
            template=template,
            output_format=args.output_format,
            output_dir=args.output_dir,
            consolidated_output=not args.no_consolidated,
            skip_existing=args.skip_existing,
            progress_callback=None if args.no_progress else progress_callback
        )
    elif args.command == 'process-files':
        print(f"📄 Processing {len(args.files)} file(s)...")
        summary = processor.process_file_list(
            file_paths=args.files,
            template=template,
            output_format=args.output_format,
            output_dir=args.output_dir,
            consolidated_output=not args.no_consolidated,
            progress_callback=None if args.no_progress else progress_callback
        )
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)
    
    # Print summary
    print("\n" + "=" * 70)
    print("BULK PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total Files: {summary['total']}")
    print(f"Processed: {summary['processed']}")
    print(f"✅ Successful: {summary['successful']}")
    print(f"❌ Failed: {summary['failed']}")
    if summary.get('skipped', 0) > 0:
        print(f"⏭️  Skipped: {summary['skipped']}")
    print(f"⏱️  Processing Time: {summary['processing_time_seconds']:.2f} seconds")
    print(f"📊 Average Time per Invoice: {summary['average_time_per_invoice']:.2f} seconds")
    
    if summary.get('consolidated_output'):
        print(f"\n📦 Consolidated Output: {summary['consolidated_output']}")
    
    # Show failed files
    failed_files = [r for r in summary['results'] if not r.get('success')]
    if failed_files:
        print(f"\n❌ Failed Files ({len(failed_files)}):")
        for result in failed_files:
            print(f"   - {Path(result['file']).name}: {result.get('error', 'Unknown error')}")
    
    # Exit with error code if any failures
    sys.exit(1 if summary['failed'] > 0 else 0)


if __name__ == '__main__':
    main()
