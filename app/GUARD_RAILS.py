from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine

# Initialize Presidio
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# -------------------------
#  Add Dutch-specific recognizers
# -------------------------

# Dutch BSN (9 digits)
bsn_pattern = Pattern(
    name="nl_bsn",
    regex=r"\b\d{9}\b",
    score=0.85
)
bsn_recognizer = PatternRecognizer(
    supported_entity="NL_BSN",
    patterns=[bsn_pattern]
)
analyzer.registry.add_recognizer(bsn_recognizer)

# Dutch Passport (2 letters + 7 digits)
passport_pattern = Pattern(
    name="nl_passport",
    regex=r"\b[A-Z]{2}\d{7}\b",
    score=0.85
)
passport_recognizer = PatternRecognizer(
    supported_entity="NL_PASSPORT",
    patterns=[passport_pattern]
)
analyzer.registry.add_recognizer(passport_recognizer)



# -------------------------
#  Define sensitive entities to mask
# -------------------------
SENSITIVE_ENTITIES = [
    "CREDIT_CARD",
    "IBAN_CODE",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IP_ADDRESS",
    "NL_BSN",
    "NL_PASSPORT"
]


# -------------------------
# Main function to sanitize user input
# -------------------------
def sanitize_input_nl(text: str) -> str:
    """
    Mask Dutch-sensitive information in user input while keeping operational data intact:
    - license plates
    - parking locations
    - reservation IDs
    """
    # Analyze text
    results = analyzer.analyze(
        text=text,
        entities=SENSITIVE_ENTITIES,
        language="en"
    )

    # Anonymize detected entities
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results
    )

    return anonymized.text
