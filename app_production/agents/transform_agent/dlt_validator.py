"""
DLT Pipeline Validator
Validates Delta Live Tables notebooks before execution
"""

import json
import re
from typing import Dict, List, Tuple
import ast


class DLTValidator:
    """Validates DLT notebooks for common errors before execution"""

    def __init__(self):
        self.known_columns = {
            "job_id",
            "title",
            "company",
            "location",
            "description",
            "category",
            "extract_date",
            "work_modality",
            "contract_type",
            "salary_min",
            "salary_max",
            "has_salary",
            "posted_date",
            "posted_time",
            "search_term",
            "source",
            "url",
        }

        self.invalid_columns = {"type", "salary_range"}

        self.valid_table_patterns = {
            "bronze": r"^[a-z_]+_bronze$",
            "silver": r"^[a-z_]+_silver$",
            "gold": r"^gold_[a-z_]+$",
            "metrics": r"^[a-z_]+_metrics$",
            "state": r"^[a-z_]+_current_state$",
        }

    def validate_notebook(self, notebook_path: str, domain: str) -> Dict[str, any]:
        """
        Validates a DLT notebook for common issues
        Returns dict with 'valid' boolean and 'errors' list
        """
        validation_result = {"valid": True, "errors": [], "warnings": [], "auto_fixes": []}

        try:
            with open(notebook_path, "r") as f:
                content = f.read()

            # Check for missing imports based on usage
            required_imports = {
                "lit(": "lit",
                "count(": "count",
                "avg(": "avg",
                "sum(": "sum",
                "col(": "col",
                "when(": "when",
                "trim(": "trim",
                "lower(": "lower",
                "regexp_replace(": "regexp_replace",
                "regexp_extract(": "regexp_extract",
                "to_timestamp(": "to_timestamp",
                "current_timestamp(": "current_timestamp",
                "unix_timestamp(": "unix_timestamp",
                "md5(": "md5",
            }

            # Check for bronze layer configuration - spark.readStream is OK for external schemas
            # Note: spark.readStream with Auto Loader is preferred for external raw data ingestion
            # This was changed from dlt.read_stream because DLT doesn't support external schemas well

            for usage, func_name in required_imports.items():
                if usage in content:
                    # Check if it's imported - improved logic
                    is_imported = False

                    # Check direct imports
                    if f"import {func_name}" in content:
                        is_imported = True

                    # Check if imported from pyspark.sql.functions
                    if "from pyspark.sql.functions" in content:
                        import_line = content.split("from pyspark.sql.functions")[1].split(")")[0]
                        if func_name in import_line:
                            is_imported = True

                    if not is_imported:
                        validation_result["errors"].append(f"Function '{func_name}' is used but not imported")
                        validation_result["valid"] = False

            # Check for invalid column references
            for invalid_col in self.invalid_columns:
                if f'"{invalid_col}"' in content or f"'{invalid_col}'" in content:
                    validation_result["errors"].append(f"Reference to non-existent column '{invalid_col}'")
                    validation_result["valid"] = False

            # Check table naming conventions
            table_names = re.findall(r'name\s*=\s*["\']([^"\']+)["\']', content)
            for table_name in table_names:
                if not self._validate_table_name(table_name):
                    validation_result["errors"].append(
                        f"Invalid table name '{table_name}' - should follow medallion naming"
                    )
                    validation_result["valid"] = False

            # Check for duplicate table/query names (CRITICAL - causes pipeline failures)
            all_table_names = []

            # Get @dlt.table names
            dlt_table_names = re.findall(r'name\s*=\s*["\']([^"\']+)["\']', content)
            all_table_names.extend(dlt_table_names)

            # Get dlt.apply_changes target names - but exclude if same as @dlt.table name (CDC pattern)
            apply_changes_targets = re.findall(r'target\s*=\s*["\']([^"\']+)["\']', content)
            for target in apply_changes_targets:
                if target not in dlt_table_names:  # Only add if not already a table name
                    all_table_names.append(target)

            # Check for duplicates
            seen_names = set()
            for name in all_table_names:
                if name in seen_names:
                    validation_result["errors"].append(
                        f"CRITICAL: Duplicate table/query name '{name}' - causes 'Cannot have multiple queries named' error"
                    )
                    validation_result["auto_fixes"].append(
                        f"Remove duplicate definition of '{name}' or rename one of them"
                    )
                    validation_result["valid"] = False
                seen_names.add(name)

            # Check for dlt.read_stream on external schemas
            if 'dlt.read_stream("' + domain + '_raw")' in content:
                validation_result["errors"].append(f"Cannot use dlt.read_stream on external schema '{domain}_raw'")
                validation_result["auto_fixes"].append("Use spark.readStream with cloudFiles for external data")
                validation_result["valid"] = False

            # Check for LIVE_REFERENCE_OUTSIDE_QUERY_DEFINITION (CRITICAL - causes pipeline failures)
            # Look for dlt.apply_changes calls outside of @dlt.table functions

            # Find all @dlt.table decorated functions
            dlt_table_functions = set()
            lines = content.split("\n")

            i = 0
            while i < len(lines):
                if "@dlt.table" in lines[i]:
                    # Look ahead to find the function definition
                    j = i + 1
                    while j < len(lines) and j < i + 20:  # Look within reasonable distance
                        if lines[j].strip().startswith("def "):
                            func_name = lines[j].strip().split("def ")[1].split("(")[0].strip()
                            dlt_table_functions.add(func_name)
                            break
                        j += 1
                i += 1

            # Now check all dlt.apply_changes calls
            for i, line in enumerate(lines):
                if "dlt.apply_changes(" in line.strip() and not line.strip().startswith("#"):
                    # Find which function this is in
                    current_function = None
                    for j in range(i - 1, max(0, i - 50), -1):
                        if lines[j].strip().startswith("def "):
                            current_function = lines[j].strip().split("def ")[1].split("(")[0].strip()
                            break

                    # Check if this function is a @dlt.table decorated function
                    if current_function and current_function not in dlt_table_functions:
                        validation_result["errors"].append(
                            "CRITICAL: dlt.apply_changes must be inside @dlt.table function - causes LIVE_REFERENCE_OUTSIDE_QUERY_DEFINITION"
                        )
                        validation_result["auto_fixes"].append(
                            "Wrap dlt.apply_changes in @dlt.table decorated function"
                        )
                        validation_result["valid"] = False
                        break  # Only report once

            # Remove duplicate dlt.apply_changes check - already handled above

            # Check for proper imports
            required_imports = ["import dlt", "from pyspark.sql.functions import"]
            for imp in required_imports:
                if imp not in content:
                    validation_result["warnings"].append(f"Missing import: {imp}")

            # Check volume paths
            volume_pattern = r"/Volumes/vagas_linkedin/([^/]+)/linkedin_data_volume"
            volumes = re.findall(volume_pattern, content)
            for vol in volumes:
                expected = f"{domain}_raw"
                if vol != expected:
                    validation_result["errors"].append(f"Wrong volume path: {vol}, expected {expected}")
                    validation_result["valid"] = False

        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["valid"] = False

        return validation_result

    def _validate_table_name(self, table_name: str) -> bool:
        """Validates table name follows medallion architecture"""
        for pattern_type, pattern in self.valid_table_patterns.items():
            if re.match(pattern, table_name):
                return True
        return False

    def auto_correct_notebook(self, notebook_path: str, domain: str) -> bool:
        """
        Attempts to auto-correct common issues in notebook
        Returns True if corrections were made
        """
        corrections_made = False

        try:
            with open(notebook_path, "r") as f:
                content = f.read()

            original_content = content

            # Fix invalid column references
            content = content.replace('"type"', '"contract_type"')
            content = content.replace("'type'", "'contract_type'")
            content = content.replace('"salary_range"', '"salary_min", "salary_max"')
            content = content.replace("'salary_range'", "'salary_min', 'salary_max'")

            # Fix table names
            content = re.sub(r'name\s*=\s*["\']data_analytics_gold["\']', 'name="gold_data_analytics"', content)
            content = re.sub(r'name\s*=\s*["\']data_engineer_gold["\']', 'name="gold_data_engineer"', content)
            content = re.sub(r'name\s*=\s*["\']digital_analytics_gold["\']', 'name="gold_digital_analytics"', content)

            # Fix dlt.read_stream on raw schemas
            if f'dlt.read_stream("{domain}_raw")' in content:
                replacement = f"""spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("multiline", "true")
        .load("/Volumes/vagas_linkedin/{domain}_raw/linkedin_data_volume/*/{domain}_*.json")"""
                content = content.replace(f'dlt.read_stream("{domain}_raw")', replacement)

            if content != original_content:
                with open(notebook_path, "w") as f:
                    f.write(content)
                corrections_made = True

        except Exception as e:
            print(f"Auto-correction failed: {str(e)}")

        return corrections_made

    def validate_all_notebooks(self, base_path: str = "/usr/local/anaconda3/vaga_linkedin/transform_output") -> Dict:
        """Validates all DLT notebooks"""
        domains = ["data_engineer", "data_analytics", "digital_analytics"]
        results = {}

        for domain in domains:
            notebook_path = f"{base_path}/dlt_{domain}_transformation.py"
            results[domain] = self.validate_notebook(notebook_path, domain)

        return results
