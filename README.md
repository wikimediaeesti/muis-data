# muis-data

## import-paintings.py

This tool imports data from the [Estonian Museums Information System (MuIS)](https://www.muis.ee/) into Wikidata.

You will need a working [pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation) installation to use the tool.

Right now, the bot imports metadata for paintings in the collection of the [Tartu Art Museum](http://tartmus.ee/), the [Estonian Art Museum](https://kunstimuuseum.ekm.ee/), the Tartu City Museum and the Pärnu Museum.

## upload-images.py 

Uploads image files (that already have metadata in Wikidata) from muis.ee to Commons and adds image claim to Wikidata item.
