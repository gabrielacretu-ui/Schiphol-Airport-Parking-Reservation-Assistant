import difflib
import json

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
import re
from datetime import datetime

# -------------------------
#  Validate dutch car plates
# -------------------------
import asyncio
from vehicle import RDW

async def check_plate_async(plate: str) -> dict:
    """
       Validate a Dutch license plate using the RDW service.

       Parameters:
           plate (str): License plate to validate.

       Returns:
           dict: Validation result with status, validity, and normalized plate.
       """
    async with RDW() as rdw:
        try:
            vehicle = await rdw.vehicle(license_plate=plate)
            return {
                "status": "success",
                "valid": True,
                "car_number": vehicle.license_plate
            }
        except Exception:
            return {
                "status": "error",
                "valid": False,
                "message": "Invalid or non-Dutch plate"
            }

def check_plate(plate: str) -> dict:
    """
       Synchronous wrapper for license plate validation.

       Parameters:
           plate (str): License plate to validate.

       Returns:
           dict: Validation result.
       """
    return asyncio.run(check_plate_async(plate))

print(check_plate("1ZKJ05"))
# -------------------------
#  Standardize dutch names
# -------------------------
def standardize_dutch_name(full_name: str) -> str:
    """
      Standardize Dutch names formatting.

      Capitalizes main names and keeps common Dutch prefixes lowercase.

      Parameters:
          full_name (str): Full name input.

      Returns:
          str: Standardized name.
      """
    if not full_name:
        return ""

    # List of common Dutch lowercase prefixes
    prefixes = {"van", "de", "van der", "van den", "van de", "ten", "ter", "v.d."}

    words = full_name.strip().split()
    standardized_words = []

    for i, word in enumerate(words):
        word_lower = word.lower()
        # If the word is a known prefix and NOT the first word, keep lowercase
        if i != 0 and word_lower in prefixes:
            standardized_words.append(word_lower)
        else:
            # Capitalize first letter, keep others lowercase
            standardized_words.append(word_lower.capitalize())

    return " ".join(standardized_words)



# ------------------------------------------------------------------------------------------------
#  Validate values against existing column values(e.g. location integrity, checking absence in db)
# ----------------------------------------------------------------------------------------------------
def validate(conn, var: str, column: str, table: str) -> str | None:
    """
    Validate a value against a database column.

    Checks for exact match first, then uses fuzzy matching
    to find the closest valid value.

    Parameters:
        conn: Database connection.
        var (str): Input value to validate.
        column (str): Column name to check.
        table (str): Table name.

    Returns:
        str | None: Corrected value if found, otherwise None.
   """

    cursor = conn.cursor()

    # build query dynamically
    query = f"SELECT {column} FROM {table}"
    cursor.execute(query)

    all_values = [row[0] for row in cursor.fetchall()]

    # normalize
    var_clean = var.strip().lower()
    normalized_values = {v.lower(): v for v in all_values}


    # exact match
    if var_clean in normalized_values:
        print(normalized_values[var_clean])
        return normalized_values[var_clean]

    # fuzzy match
    matches = difflib.get_close_matches(var_clean, normalized_values.keys(), n=1, cutoff=0.6)

    if matches:
        print(normalized_values[matches[0]])
        return normalized_values[matches[0]]
    print("no value found")

    return None

