"""Entity type definitions and spaCy label mappings."""

from enum import Enum


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    DATE = "DATE"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    MONETARY = "MONETARY"
    OTHER = "OTHER"


# spaCy NER label → kn0 EntityType
SPACY_LABEL_MAP: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORGANIZATION,
    "GPE": EntityType.LOCATION,       # Geo-political entity
    "LOC": EntityType.LOCATION,       # Natural location
    "FAC": EntityType.LOCATION,       # Facility
    "DATE": EntityType.DATE,
    "TIME": EntityType.DATE,
    "EVENT": EntityType.EVENT,
    "MONEY": EntityType.MONETARY,
    "PRODUCT": EntityType.CONCEPT,
    "WORK_OF_ART": EntityType.CONCEPT,
    "LAW": EntityType.CONCEPT,
    "LANGUAGE": EntityType.CONCEPT,
    "NORP": EntityType.ORGANIZATION,  # Nationality/religious/political group
}
