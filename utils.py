def sanitize_categories(cats: list) -> list:
    eliminate = ('biolink:NamedThing', 'biolink:BiologicalEntity', 'biolink:ThingWithTaxon',
                   'biolink:PhysicalEssence', 'biolink:PhysicalEssenceOrOccurrent')
    return [cat for cat in cats if cat not in eliminate]
