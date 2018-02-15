import rdflib, urllib
import pywikibot
from pywikibot import pagegenerators as pg


# Checks whether the entry for the artwork specifies it is a painting
def ispainting(artwork, artworkURI):
    if (artworkURI, rdflib.term.URIRef(u'http://www.cidoc-crm.org/cidoc-crm/P2_has_type'), rdflib.term.URIRef(u'http://opendata.muis.ee/thesaurus/203/13540')) in artwork:
        return True
    else:
        return False


def findlabel(artwork, artworkURI):
    label = artwork.value(subject=artworkURI, predicate=rdflib.term.URIRef(u'http://www.w3.org/2000/01/rdf-schema#label'))
    return label


def findidentifier(artwork, artworkURI):
    identifier = artwork.value(subject=artworkURI, predicate=rdflib.term.URIRef(u'http://purl.org/dc/terms/identifier'))
    return identifier


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
    artwork = rdflib.Graph()
    artwork.parse("https://www.muis.ee/rdf/object/" + id)
    artworkURI = rdflib.term.URIRef(u'http://opendata.muis.ee/object/' + id)
    if ispainting(artwork, artworkURI):
        # TODO: create Wikidata item
        # TODO: change to add Wikidata P4525 property
        print id
        # TODO: change to add Wikidata P31 property
        print "It's a painting"
        label = findlabel(artwork, artworkURI)
        # TODO: change to add Wikidata et label
        print label
        # TODO: change to add Wikidata P217 property
        identifier = findidentifier(artwork, artworkURI)
        print identifier
        # TODO: extract author data
        # TODO: extract technique
        # TODO: extract material
        # TODO: extract measurements

    else:
        print "Not a painting"