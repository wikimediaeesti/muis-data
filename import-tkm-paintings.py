import rdflib, urllib
import pywikibot
from lxml import etree
from pywikibot import pagegenerators as pg


# Checks whether the entry for the artwork specifies it is a painting
def ispainting(physical_thing):
    typeXML = physical_thing.find('crm:P2_has_type', physical_thing.nsmap)
    type = typeXML.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
    if type == 'http://opendata.muis.ee/thesaurus/203/13540':
        return True
    else:
        return False


def findlabel(physical_thing):
    label = physical_thing.find('rdfs:label', physical_thing.nsmap).text
    return label


def findidentifier(physical_thing):
    identifier = physical_thing.find('dcterms:identifier', physical_thing.nsmap).text
    return identifier


# TODO: This should allow multiple types (ID 261412)
def findtechnique(physical_thing):
    psP2 = physical_thing.find('crm:P2_has_type', physical_thing.nsmap)
    techniqueSection = psP2.find('muis:Technique', physical_thing.nsmap)
    technique = techniqueSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
    techniqueResource = technique.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
    return decodeTechnique(techniqueResource)


def decodeTechnique(technique):
    switcher = {
        # 6li
        'http://opendata.muis.ee/thesaurus/107/5329': "Q296955",
        'http://opendata.muis.ee/thesaurus/107/33126': "Q296955",
        # segatehnika = "mixed technique"
        'http://opendata.muis.ee/thesaurus/107/5328': "nothing",
        # tempera
        'http://opendata.muis.ee/thesaurus/107/5259': "Q175166",
        # guass
        'http://opendata.muis.ee/thesaurus/107/5539': "Q204330"
    }
    return switcher.get(technique, "nothing")

def findmaterial(physical_thing):
    psP2 = physical_thing.find('crm:P45_consists_of', physical_thing.nsmap)
    materialSection = psP2.find('crm:E57_Material', physical_thing.nsmap)
    material = materialSection.find('crm:P130_shows_features_of', physical_thing.nsmap)
    materialResource = material.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
    return decodeMaterial(materialResource)


def decodeMaterial(material):
    switcher = {
        # l6uend
        'http://opendata.muis.ee/thesaurus/112/32314': "Q219803",
        # vineer
        'http://opendata.muis.ee/thesaurus/112/2345': "Q12321255",
        'http://opendata.muis.ee/thesaurus/112/2461': "Q12321255",
        # metall
        'http://opendata.muis.ee/thesaurus/112/2139': "Q11426",
        # paber
        'http://opendata.muis.ee/thesaurus/112/2195': "Q11472",
        # masoniit
        'http://opendata.muis.ee/thesaurus/112/29672': "Q1808397",
        # kartong = cardboard
        'http://opendata.muis.ee/thesaurus/112/2203': "Q389782",
        # papp = cardboard
        'http://opendata.muis.ee/thesaurus/112/2362': "Q389782",
        # puitkiudplaat
        'http://opendata.muis.ee/thesaurus/112/2410': "Q1397443",

    }
    return switcher.get(material, "nothing")


def finddimensions(physical_thing):
    dimensionsXML = physical_thing.findall('crm:P43_has_dimension', physical_thing.nsmap)
    # We assume if there's only two dimensions, they're likely height and width so we go on
    if len(dimensionsXML) == 2:
        dimensions = {}
        for dimension in dimensionsXML:
            dimensionXML = dimension.find('crm:E54_Dimension', physical_thing.nsmap)
            dimensionType = dimensionXML.find('crm:P2_has_type', physical_thing.nsmap)
            dimensionTypeURI = dimensionType.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            dimensionUnit = dimensionXML.find('crm:P91_has_unit', physical_thing.nsmap)
            dimensionUnitURI = dimensionUnit.xpath('self::*//@rdf:resource', namespaces=physical_thing.nsmap)[0]
            # 49/2506 = height
            if dimensionTypeURI == 'http://opendata.muis.ee/thesaurus/49/2506':
                dimensions['height'] = dimensionXML.find('crm:P90_has_value', physical_thing.nsmap).text
                dimensions['height-unit'] = decodeUnit(dimensionUnitURI)
            # 49/2485 = width
            if dimensionTypeURI == 'http://opendata.muis.ee/thesaurus/49/2485':
                dimensions['width'] = dimensionXML.find('crm:P90_has_value', physical_thing.nsmap).text
                dimensions['width-unit'] = decodeUnit(dimensionUnitURI)
        # (for now) We only want to send dimensions if we have height + width + units
        if len(dimensions) == 4:
            return dimensions
        else:
            return None
    return None


def decodeUnit(unit):
    switcher = {
        # cm
        'http://opendata.muis.ee/thesaurus/200/2526': "cm",
    }
    return switcher.get(unit, "nothing")


site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()


# We take the painting collection from Tartu Art Museum and extract the IDs of all the artworks in it
collection = rdflib.Graph()
collection.parse("https://www.muis.ee/rdf/collection/442")

artworkIDs = []

for artworkURI in collection.objects(predicate=rdflib.term.URIRef(u'http://www.cidoc-crm.org/cidoc-crm/P46_is_composed_of')):
    artworkIDs.append(str(artworkURI).rsplit('/', 1)[-1])

print artworkIDs

for id in artworkIDs[:1]:
    # We take a painting and take all the info we can find
    artworkxml = etree.parse(urllib.urlopen("https://www.muis.ee/rdf/object/" + id))
    physical_thing = artworkxml.find('crm:E18_Physical_Thing', artworkxml.getroot().nsmap)
    if ispainting(physical_thing):
        # TODO: create Wikidata item
        # TODO: change to add Wikidata P4525 property
        print id
        # TODO: change to add Wikidata P31 property
        print "It's a painting"
        label = findlabel(physical_thing)
        # TODO: change to add Wikidata et label
        print label
        # TODO: change to add Wikidata P217 property
        identifier = findidentifier(physical_thing)
        print identifier
        # TODO: extract author data (P170)
        # TODO: extract painting date (P571)
        # TODO: set collection (P195) Tartu Art Museum (Q12376420)
        # TODO: change to send technique (P186)
        composedOf = physical_thing.find('crm:P46_is_composed_of', physical_thing.nsmap)
        second_physical_thing = composedOf.find('crm:E18_Physical_Thing', physical_thing.nsmap)
        technique = findtechnique(second_physical_thing)
        print technique
        # TODO: change to send material (P186)
        material = findmaterial(second_physical_thing)
        print material
        # TODO: change to send height (P2048)
        dimensions = finddimensions(second_physical_thing)
        print dimensions['height'] + " " + dimensions['height-unit']
        # TODO: change to send width (P2049)
        print dimensions['width'] + " " + dimensions['width-unit']

    else:
        print "Not a painting"