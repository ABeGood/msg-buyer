import json
import os
import pandas as pd
import logging
import ast
import re
from datetime import datetime
from .car_models_expand import models_expanded_eur, models_expanded_gur

"""
Pipeline for processing data from Razom API.
Processes GUR and EUR automotive parts data.

Usage Examples:
1. Basic usage (saves only final result):
   pipeline_gur_eur_data(json_data, 'output/final_result.csv')
2. Debug mode with intermediate files in the same directory as output:
   pipeline_gur_eur_data(json_data, 'output/final_result.csv', mode='debug')
3. Debug mode with custom intermediate path:
   pipeline_gur_eur_data(json_data, 'output/final_result.csv', mode='debug', intermediate_path='debug/intermediate')

Debug Mode Features:
- If debug mode is enabled, saves intermediate CSV files for each processing stage (e1_, e2_, e3_, etc.).
- For key columns (car_model, car_id, production_years, has_dash), generates separate debug CSV files (debug_*_stage.csv) that show only the rows where values changed between stages, matched by car_id.
- Intermediate and debug files are saved to the specified intermediate_path, or to the output directory (from output_path) if not provided.

Parameters:
- input_json_data (dict): JSON data containing automotive parts information.
- output_path (str): Path where the final result will be saved.
- mode (str, optional): Processing mode. If 'debug', intermediate files will be saved.
- intermediate_path (str, optional): Path for saving intermediate files. 
  If not specified and mode='debug', uses the directory of output_path.
"""

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def pipeline_gur_eur_data(input_json_data: dict, output_path: str, mode: str = None, intermediate_path: str = None) -> pd.DataFrame:
    # Determine catalog segment from output_path
    catalog_segment_name = _determine_catalog_segment_name_from_path(output_path)
    
    # Set up paths for intermediate files
    if mode == 'debug':
        if intermediate_path is None:
            # Use the same directory as output_path for intermediate files
            intermediate_path = os.path.dirname(output_path)
        save_intermediate = True
    else:
        save_intermediate = False
        intermediate_path = None
    
    try:
        # Stage 1: JSON → CSV
        df = _convert_json_to_csv(input_json_data, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 2: Data expansion
        df = _expand_data(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 3: Data cleaning
        df = _clean_data(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 4: Car expansion
        df = _expand_cars(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 5: Year separation
        df = _separate_years(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 6: Year expansion
        df = _expand_years(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 7: Roman numeral normalization
        df = _normalize_roman_numerals(df, catalog_segment_name, save_intermediate, intermediate_path, output_path)
        
        # Stage 8: Dash detection in models
        df = _detect_dash_in_models(df, catalog_segment_name, save_intermediate, intermediate_path)
        
        # Stage 9: Model expansion
        df = _expand_models(df, catalog_segment_name, save_intermediate, intermediate_path, output_path)
        
        # Stage 10: Final processing
        df = _final_processing(df, catalog_segment_name, output_path, save_intermediate, intermediate_path)
        return df
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise


def _convert_json_to_csv(input_json_data: dict, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 1: JSON to CSV conversion
    """
    raw_data = input_json_data['data'] 
    df = pd.DataFrame(raw_data)
    
    # Save intermediate file with e1 prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e1_{catalog_segment_name}_catalog.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df.to_csv(full_path, index=False)
    
    return df


def _expand_data(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 2: Data expansion (flattening nested structures)
    
    Creates searchable columns from nested JSON structures:
    - applicability_cars -> cars_brands, cars_models, cars_ids, cars_modifications
    - oes -> oes_numbers, oes_ids
    - product_segments -> segments_names, segments_ids
    - purchase -> price_usd, price_eur, remains
    """
    df_expanded = df.copy()

    def safe_literal_eval(value): # Convert JSON strings to Python objects
        if isinstance(value, (list, dict)):
            return value  # Already Python object
        else:
            return ast.literal_eval(value)  # String, needs parsing
    
    df_expanded['applicability_cars'] = df_expanded['applicability_cars'].apply(safe_literal_eval)
    df_expanded['oes'] = df_expanded['oes'].apply(safe_literal_eval)
    df_expanded['product_segments'] = df_expanded['product_segments'].apply(safe_literal_eval)
    df_expanded['purchase'] = df_expanded['purchase'].apply(safe_literal_eval)

    # Cars search columns - use df_searchable, not df
    df_expanded['cars_brands'] = df_expanded['applicability_cars'].apply(
        lambda cars: ' | '.join([car['brand'] for car in cars])
    )
    df_expanded['cars_models'] = df_expanded['applicability_cars'].apply(
        lambda cars: ' | '.join([car['model'] for car in cars])
    )
    df_expanded['cars_ids'] = df_expanded['applicability_cars'].apply(
        lambda cars: ' | '.join([str(car['car_id']) for car in cars])
    )
    df_expanded['cars_modifications'] = df_expanded['applicability_cars'].apply(
        lambda cars: ' | '.join([f"{car['modification_name']} (car_id:{car['car_id']})" for car in cars])
    )
    
    # OEs search columns - use df_searchable, not df
    df_expanded['oes_numbers'] = df_expanded['oes'].apply(
        lambda oes: ' | '.join([oe['number'] for oe in oes])
    )
    df_expanded['oes_ids'] = df_expanded['oes'].apply(
        lambda oes: ' | '.join([str(oe['oe_id']) for oe in oes])
    )
    
    # Create search columns for segments
    df_expanded['segments_names'] = df_expanded['product_segments'].apply(
        lambda segments: ' | '.join([segment['name'] for segment in segments])
    )
    df_expanded['segments_ids'] = df_expanded['product_segments'].apply(
        lambda segments: ' | '.join([str(segment['segment_id']) for segment in segments])
    )
    
    # Create separate columns for purchase data (purchase is a list of dicts)
    df_expanded['price_usd'] = df_expanded['purchase'].apply(
        lambda x: x[0].get('price_usd', '') if x and len(x) > 0 else ''
    )
    df_expanded['price_eur'] = df_expanded['purchase'].apply(
        lambda x: x[0].get('price_eur', '') if x and len(x) > 0 else ''
    )
    df_expanded['remains'] = df_expanded['purchase'].apply(
        lambda x: x[0].get('remains', 0) if x and len(x) > 0 else 0
    )
    
    # Convert to numeric if needed
    df_expanded['price_usd'] = pd.to_numeric(df_expanded['price_usd'], errors='coerce')
    df_expanded['price_eur'] = pd.to_numeric(df_expanded['price_eur'], errors='coerce')
    df_expanded['remains'] = pd.to_numeric(df_expanded['remains'], errors='coerce')
    
    # Save intermediate file with e2 prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e2_{catalog_segment_name}_catalog.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_expanded.to_csv(full_path, index=False)
    
    return df_expanded


def _clean_data(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 3: Data cleaning. Removes unnecessary columns, keeping only those needed for further processing.
    """
    df_clean = df.copy()
    
    columns_to_drop = [
        'Unnamed: 0.1',  # Index from CSV (if exists)
        'Unnamed: 0',    # Index from CSV
        'article',        # Original article
        'brand',          # Original brand column
        'applicability_cars',  # Original JSON data (already expanded)
        'product_segments',    # Original JSON data (already expanded)
        'oes',                 # Original JSON data (already expanded)
        'purchase',            # Original JSON data (already expanded)
        'cars_brands',         # Duplicate data
        'cars_models',         # Duplicate data
        'cars_ids',            # Duplicate data
        'oes_ids',             # Duplicate data
        'segments_ids'         # Duplicate data
    ]
    
    # Remove only columns that exist
    existing_columns_to_drop = [col for col in columns_to_drop if col in df_clean.columns]
    df_clean = df_clean.drop(columns=existing_columns_to_drop)
    
    # Save intermediate version after cleaning with e3_clean prefix if debug mode is enabled
    if save_intermediate:
        filename_after = f"e3_{catalog_segment_name}_catalog_clean.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename_after)
        else:
            full_path = filename_after
        df_clean.to_csv(full_path, index=False)
    
    return df_clean


def _expand_cars(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 4: Splits cars_modifications column by '|' separator and creates separate rows for each car modification.
    Also extracts car_id from each modification and creates a separate column.
    """
    df_cars_expanded = df.copy()
    
    # Split cars_modifications by '|'
    df_cars_expanded['cars_modifications'] = df_cars_expanded['cars_modifications'].str.split('|')
    df_cars_expanded = df_cars_expanded.explode('cars_modifications')
    df_cars_expanded['cars_modifications'] = df_cars_expanded['cars_modifications'].str.strip()
    
    # Extract car_id from each modification
    df_cars_expanded['car_id'] = df_cars_expanded['cars_modifications'].apply(
        lambda x: extract_car_id_from_modification(x)
    )
    
    # Convert car_id to int (remove float)
    # Replace None with 0 and convert to int
    df_cars_expanded['car_id'] = df_cars_expanded['car_id'].fillna(0).astype(int)
    
    # Clean cars_modifications from car_id information
    df_cars_expanded['cars_modifications'] = df_cars_expanded['cars_modifications'].apply(
        lambda x: clean_modification_name(x)
    )
    
    df_cars_expanded = df_cars_expanded.reset_index(drop=True)
    
    # Save intermediate version with e4_ prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e4_{catalog_segment_name}_catalog_cars_expanded.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_cars_expanded.to_csv(full_path, index=False)
    
    return df_cars_expanded


def _separate_years(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 5: Extracts car model and production years from cars_modifications column, creating separate car_model and production_years columns.
    """
    df_separate_years = df.copy()
    df_separate_years[['car_model', 'production_years']] = df_separate_years['cars_modifications'].apply(
        lambda x: pd.Series(extract_years_and_model(x))
    )

    df_separate_years = df_separate_years.drop(columns=['cars_modifications'])
    
    # Save intermediate version with e5_ prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e5_{catalog_segment_name}_catalog_separate_years.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_separate_years.to_csv(full_path, index=False)
    
    return df_separate_years


def _expand_years(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 6: Expand year range like '99-04' to full years string '1999, 2000, 2001, 2002, 2003, 2004'. Handle cases like '13-' (up to current year)
    """
    df_expanded_years = df.copy()
    df_expanded_years['production_years'] = df_expanded_years['production_years'].apply(expand_production_years)
    
    # Save intermediate version with e6_ prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e6_{catalog_segment_name}_catalog_expanded_years.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_expanded_years.to_csv(full_path, index=False)
    
    return df_expanded_years


def _normalize_roman_numerals(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None, output_path: str = None) -> pd.DataFrame:
    """
    Stage 7: Normalizes Roman numerals in car model names, replacing them with Arabic numerals.
    Exceptions for models like HR-V, CR-V, where V is a letter, not a Roman numeral.
    """
    df_models_norm = df.copy()
    df_models_norm['car_model'] = df_models_norm['car_model'].apply(normalize_roman_numerals)
    
    # Save intermediate version with e7_ prefix if debug mode is enabled AND compare changes in car_model
    if save_intermediate:
        compare_column_changes(df, df_models_norm, 'car_model', 'stage7_roman_num_to_arab', intermediate_path, output_path, catalog_segment_name)
        filename = f"e7_{catalog_segment_name}_catalog_roman_norm.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_models_norm.to_csv(full_path, index=False)
    
    return df_models_norm


def _detect_dash_in_models(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 8: Dash detection in car model names.
    Adds has_dash column that shows whether car_model contains a dash.
    """
    df_dash_detected = df.copy()
    
    # Add has_dash column
    df_dash_detected['has_dash'] = df_dash_detected['car_model'].str.contains('-', na=False)
    
    # Save intermediate version with e8_ prefix if debug mode is enabled
    if save_intermediate:
        filename = f"e8_{catalog_segment_name}_catalog_dash_detected.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_dash_detected.to_csv(full_path, index=False)
    
    return df_dash_detected


def _expand_models(df: pd.DataFrame, catalog_segment_name: str, save_intermediate: bool = False, intermediate_path: str = None, output_path: str = None) -> pd.DataFrame:
    """
    Stage 9: Model expansion
    Expands car model names using the appropriate models_expanded dictionary,
    replacing abbreviated names with full lists of model codes.
    """
    df_models_expanded = df.copy()
    
    # Apply expand_car_model function to car_model column with segment parameter
    df_models_expanded['car_model'] = df_models_expanded['car_model'].apply(
        lambda x: expand_car_model(x, catalog_segment_name)
    )
    
    # Save intermediate version with e9_ prefix if debug mode is enabled
    if save_intermediate:
        compare_column_changes(df, df_models_expanded, 'car_model', 'stage9_expand_models', intermediate_path, output_path, catalog_segment_name)
        filename = f"e9_{catalog_segment_name}_catalog_final.csv"
        if intermediate_path:
            full_path = os.path.join(intermediate_path, filename)
        else:
            full_path = filename
        df_models_expanded.to_csv(full_path, index=False)
    
    # Remove has_dash column after all saves
    if 'has_dash' in df_models_expanded.columns:
        df_models_expanded = df_models_expanded.drop(columns=['has_dash'])
    
    return df_models_expanded


def _final_processing(df: pd.DataFrame, catalog_segment_name: str, output_path: str, save_intermediate: bool = False, intermediate_path: str = None) -> pd.DataFrame:
    """
    Stage 10: Final processing
    
    Performs final data processing and saves the result to the specified output path.
    """
    df_final = df.copy()
    
    # Save final result to the specified output path
    df_final.to_csv(output_path, index=False)
    
    return df_final


def _determine_catalog_segment_name_from_path(path: str) -> str:
    if path is None:
        logger.warning("Path not specified, using 'eur' as default")
        return 'eur'
    path_lower = path.lower()
    if 'eur' in path_lower:
        return 'eur'
    elif 'gur' in path_lower:
        return 'gur'
    else:
        logger.warning(f"Could not determine catalog segment from path '{path}', using 'eur' as default")
        return 'eur'


def extract_car_id_from_modification(modification_str: str) -> int:
    """
    Extracts car_id from modification string like 'Audi A3 96-03 (car_id:80024)'
    """
    match = re.search(r'\(car_id:(\d+)\)', modification_str)
    if match:
        return int(match.group(1))
    return None


def clean_modification_name(modification_str: str) -> str:
    """
    Cleans modification name from car_id information
    'Audi A3 96-03 (car_id:80024)' -> 'Audi A3 96-03'
    """
    return re.sub(r'\s*\(car_id:\d+\)', '', modification_str).strip()


def expand_production_years(year_range):
    """
    Expand year range like '99-04' to full years string '1999, 2000, 2001, 2002, 2003, 2004'
    Handle cases like '13-' (up to current year)
    """
    if pd.isna(year_range) or year_range == '':
        return ''

    year_range = str(year_range).strip()
    current_year = datetime.now().year

    # Handle incomplete ranges like "13-"
    if year_range.endswith('-'):
        start_year_str = year_range[:-1]
        if len(start_year_str) == 2:
            start_year_2digit = int(start_year_str)
            # Determine century: if >= 50, assume 19xx, else 20xx
            start_year = 2000 + start_year_2digit if start_year_2digit < 50 else 1900 + start_year_2digit
            years_list = list(range(start_year, current_year + 1))
            return ', '.join(map(str, years_list))

    # Handle complete ranges like "99-04"
    if '-' in year_range and not year_range.endswith('-'):
        parts = year_range.split('-')
        if len(parts) == 2:
            start_str, end_str = parts
            if len(start_str) == 2 and len(end_str) == 2:
                start_2digit = int(start_str)
                end_2digit = int(end_str)

                # Determine centuries
                start_year = 2000 + start_2digit if start_2digit < 50 else 1900 + start_2digit
                end_year = 2000 + end_2digit if end_2digit < 50 else 1900 + end_2digit

                # Handle year wrapping (e.g., 99-04 means 1999-2004)
                if start_year > end_year:
                    end_year += 100

                years_list = list(range(start_year, end_year + 1))
                return ', '.join(map(str, years_list))

    return ''


def extract_years_and_model(modification):
    """
    Extracts car model and production years from modification string.
    
    Args:
        modification: Car modification string (e.g.: "BMW X5 15-20 xDrive")
    
    Returns:
        tuple: (model_part, years_part) - model and production years
    """
    if pd.isna(modification) or modification == '':
        return modification, ''

    # Pattern to match years in the middle: find 2-digit year pattern and extract around it    
    # This handles cases where years are embedded with additional text after
    pattern = r'^(.+?)\s+(\d{2}-(?:\d{2}|)?)\s*(.*)$'

    match = re.match(pattern, modification.strip())
    if match:
        model_part_before = match.group(1).strip()
        years_part = match.group(2)
        additional_text = match.group(3).strip()

        # Combine model with additional text if it exists
        if additional_text:
            model_part = f"{model_part_before} {additional_text}"
        else:
            model_part = model_part_before

        return model_part, years_part
    else:
        # No years found, return original modification and empty years
        return modification.strip(), ''


def expand_car_model(model_name, catalog_segment_name):
    """
    Expands car model name using the appropriate models_expanded dictionary.
    
    Args:
        model_name (str): Original model name, e.g. 'BMW 1 E81-88'
        catalog_segment_name (str): Catalog segment ('eur' or 'gur')
    
    Returns:
        str: Expanded model codes separated by commas, or original name if mapping not found
    """
    if not isinstance(model_name, str):
        return str(model_name)

    # Choose the correct dictionary depending on the segment
    models_expanded = models_expanded_eur if catalog_segment_name == 'eur' else models_expanded_gur

    # Check if exact match exists in models_expanded
    if model_name in models_expanded:
        # Extract just the model codes (E81, E82, etc.)
        expanded_list = models_expanded[model_name]
        if expanded_list:
            # Return format: "BMW 1 E81, E82, E87, E88"
            base_name = " ".join(model_name.split()[:-1])  # "BMW 1"
            return f"{base_name} {', '.join(expanded_list)}"

    # If no expansion found, return original
    return model_name


def normalize_roman_numerals(text):
    """
    Normalizes Roman numerals in car model names, replacing them with Arabic numerals.
    Exceptions for models like HR-V, CR-V, where V is a letter, not a Roman numeral.
    """
    if pd.isna(text):
        return text

    # Skip normalization for known car model patterns where V is a letter
    car_model_exceptions = [
        r'HR-V\b',     # Honda HR-V
        r'CR-V\b',     # Honda CR-V
        r'BR-V\b',     # Honda BR-V
        r'WR-V\b',     # Honda WR-V
        r'XR-V\b',     # Any XR-V models
        r'FR-V\b',     # Honda FR-V
        r'MR-V\b',     # Any MR-V models
        r'\b[A-Z]{2}-V\b',  # General pattern for XX-V models
        r'Model X\b',  # Tesla Model X
    ]

    result = str(text)

    # Check if text contains car model exceptions
    for exception_pattern in car_model_exceptions:
        if re.search(exception_pattern, result):
            # Skip V replacement for this text
            roman_patterns = [
                (r'\bVIII\b', '8'),
                (r'\bVII\b', '7'),
                (r'\bVI\b', '6'),
                (r'\bIX\b', '9'),
                (r'\bIV\b', '4'),
                (r'\bIII\b', '3'),
                (r'\bII\b', '2'),
                (r'\bX\b', '10'),
                (r'\bI\b', '1')
            ]
            break
    else:
        # Normal pattern including V
        roman_patterns = [
            (r'\bVIII\b', '8'),
            (r'\bVII\b', '7'),
            (r'\bVI\b', '6'),
            (r'\bIX\b', '9'),
            (r'\bIV\b', '4'),
            (r'\bV\b', '5'),
            (r'\bIII\b', '3'),
            (r'\bII\b', '2'),
            (r'\bX\b', '10'),
            (r'\bI\b', '1')
        ]

    for pattern, replacement in roman_patterns:
        result = re.sub(pattern, replacement, result)

    return result


def compare_column_changes(old_df, new_df, column_name, stage_name, intermediate_path, output_path=None, catalog_segment_name=None):
    """
    Compares changes in a column between two stages and shows only new values.
    Matches old and new values by car_id.
    
    Args:
        old_df (pd.DataFrame): DataFrame before changes
        new_df (pd.DataFrame): DataFrame after changes
        column_name (str): Column name for comparison
        stage_name (str): Stage name for file naming
        intermediate_path (str): Path for saving result
        output_path (str): Path for saving if intermediate_path is not specified
        catalog_segment_name (str): Catalog segment name for file naming
    """
    # Determine save path
    if intermediate_path:
        save_path = intermediate_path
    elif output_path:
        save_path = os.path.dirname(output_path)
    else:
        return
    
    if column_name not in old_df.columns or column_name not in new_df.columns:
        logger.warning(f"Колонка '{column_name}' не найдена в одном из DataFrame")
        return
    
    if 'car_id' not in old_df.columns or 'car_id' not in new_df.columns:
        logger.warning("Колонка 'car_id' не найдена в одном из DataFrame")
        return
    
    # Create dictionaries for fast lookup by car_id
    old_dict = dict(zip(old_df['car_id'], old_df[column_name]))
    new_dict = dict(zip(new_df['car_id'], new_df[column_name]))
    
    # Find changes
    comparison_data = []
    
    for car_id in new_dict:
        new_value = new_dict[car_id]
        
        # Check if this car_id exists in old data
        if car_id in old_dict:
            old_value = old_dict[car_id]
            
            # If values are different, add to result
            if str(old_value) != str(new_value):
                comparison_data.append({
                    'old_value': old_value,
                    'new_value': new_value
                })
        else:
            # New car_id (wasn't in old data)
            comparison_data.append({
                'old_value': '',
                'new_value': new_value
            })
    
    if comparison_data:
        # Create DataFrame with results
        comparison_df = pd.DataFrame(comparison_data)
        
        # Save to CSV file
        if catalog_segment_name:
            filename = f"debug_{catalog_segment_name}_{column_name}_{stage_name}.csv"
        else:
            filename = f"debug_{column_name}_{stage_name}.csv"
        full_path = os.path.join(save_path, filename)
        comparison_df.to_csv(full_path, index=False, encoding='utf-8')