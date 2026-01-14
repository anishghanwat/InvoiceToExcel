"""
Benchmarking Framework for Accuracy Tracking
Tracks before/after AI accuracy for enterprise trust.
"""
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class BenchmarkingFramework:
    """Track accuracy improvements from AI normalization."""
    
    def __init__(self, log_dir: str = "logs/benchmarking"):
        """Initialize benchmarking framework."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_invoice_processing(
        self,
        invoice_id: str,
        before_ai: Dict[str, Any],
        after_ai: Dict[str, Any],
        ground_truth: Dict[str, Any],
        canonical_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log invoice processing for benchmarking.
        
        Format:
        {
          "invoice_id": "INV-123",
          "before_ai": {"total": 1000},
          "after_ai": {"total": 1180, "confidence": 0.94},
          "ground_truth": {"total": 1180},
          "correct": true
        }
        """
        log_entry = {
            "invoice_id": invoice_id,
            "timestamp": datetime.now().isoformat(),
            "before_ai": {
                "total": before_ai.get("total_amount"),
                "invoice_date": before_ai.get("invoice_date"),
                "vendor": before_ai.get("vendor"),
                "invoice_number": before_ai.get("invoice_number")
            },
            "after_ai": {
                "total": after_ai.get("total_amount"),
                "invoice_date": after_ai.get("invoice_date"),
                "vendor": after_ai.get("vendor"),
                "invoice_number": after_ai.get("invoice_number"),
                "confidence": canonical_schema.get("confidence", {}).get("overall", 0.0)
            },
            "ground_truth": ground_truth,
            "correct": self._check_correctness(after_ai, ground_truth),
            "field_accuracy": self._calculate_field_accuracy(after_ai, ground_truth)
        }
        
        # Save log entry
        log_file = self.log_dir / f"{invoice_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, default=str)
        
        return log_entry
    
    def _check_correctness(self, after_ai: Dict[str, Any], ground_truth: Dict[str, Any]) -> bool:
        """Check if AI output matches ground truth."""
        required_fields = ["total_amount", "invoice_date", "vendor", "invoice_number"]
        
        for field in required_fields:
            ai_value = after_ai.get(field)
            truth_value = ground_truth.get(field)
            
            if ai_value != truth_value:
                return False
        
        return True
    
    def _calculate_field_accuracy(self, after_ai: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, bool]:
        """Calculate accuracy per field."""
        fields = ["total_amount", "invoice_date", "vendor", "invoice_number"]
        accuracy = {}
        
        for field in fields:
            ai_value = after_ai.get(field)
            truth_value = ground_truth.get(field)
            accuracy[field] = ai_value == truth_value
        
        return accuracy
    
    def calculate_metrics(self, log_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """
        Calculate benchmarking metrics.
        
        Returns:
            {
                "field_accuracy": {...},
                "weighted_accuracy": 0.92,
                "overall_accuracy": 0.88,
                "total_invoices": 100
            }
        """
        if not log_files:
            log_files = list(self.log_dir.glob("*.json"))
        
        if not log_files:
            return {"error": "No log files found"}
        
        field_correct = {
            "total_amount": 0,
            "invoice_date": 0,
            "vendor": 0,
            "invoice_number": 0
        }
        total = len(log_files)
        
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_entry = json.load(f)
            
            field_accuracy = log_entry.get("field_accuracy", {})
            for field, correct in field_accuracy.items():
                if correct:
                    field_correct[field] += 1
        
        # Calculate field accuracy
        field_accuracy = {
            field: correct / total if total > 0 else 0.0
            for field, correct in field_correct.items()
        }
        
        # Calculate weighted accuracy
        weights = {
            "total_amount": 0.40,
            "invoice_date": 0.25,
            "vendor": 0.20,
            "invoice_number": 0.15
        }
        
        weighted_accuracy = sum(
            field_accuracy.get(field, 0.0) * weight
            for field, weight in weights.items()
        )
        
        # Overall accuracy (all fields correct)
        overall_correct = sum(1 for log_file in log_files
                             for log_entry in [json.load(open(log_file, 'r', encoding='utf-8'))]
                             if log_entry.get("correct", False))
        overall_accuracy = overall_correct / total if total > 0 else 0.0
        
        return {
            "field_accuracy": field_accuracy,
            "weighted_accuracy": weighted_accuracy,
            "overall_accuracy": overall_accuracy,
            "total_invoices": total
        }
    
    def generate_report(self) -> str:
        """Generate benchmarking report."""
        metrics = self.calculate_metrics()
        
        report = f"""
# Benchmarking Report

## Accuracy Metrics

### Field-Level Accuracy
- Total Amount: {metrics.get('field_accuracy', {}).get('total_amount', 0):.2%}
- Invoice Date: {metrics.get('field_accuracy', {}).get('invoice_date', 0):.2%}
- Vendor: {metrics.get('field_accuracy', {}).get('vendor', 0):.2%}
- Invoice Number: {metrics.get('field_accuracy', {}).get('invoice_number', 0):.2%}

### Overall Metrics
- Weighted Accuracy: {metrics.get('weighted_accuracy', 0):.2%}
- Overall Accuracy: {metrics.get('overall_accuracy', 0):.2%}
- Total Invoices: {metrics.get('total_invoices', 0)}

## Expected Accuracy by Stage
- Textract only: ~60-70%
- Rules only: ~75%
- Rules + AI semantic: ~88-92%
- + AI repair: 92-96%
"""
        return report
