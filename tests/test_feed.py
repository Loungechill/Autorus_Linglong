import unittest
import xml.etree.ElementTree as ET
from scripts.build_feed import filter_feed, season


def catalog(names):
    offers = ''.join(
        f'<offer id="00{i}" available="true"><name>{name}</name>'
        '<vendor>LINGLONG</vendor><categoryId>105</categoryId>'
        '<price>7446</price><url>https://example.org/?a=1&amp;b=2</url></offer>'
        for i, name in enumerate(names)
    )
    return ('<yml_catalog date="2026-10-23 10:00"><shop><categories>'
            '<category id="105">Автомобильные шины</category></categories>'
            f'<offers>{offers}</offers></shop></yml_catalog>').encode()


class FilterTests(unittest.TestCase):
    def test_seasons_and_full_offer_preservation(self):
        source = catalog(['Winter Grip шип', 'Nord Master зима',
                          'Comfort Master лето', 'All Season всесез', 'Winter нешип'])
        output, report = filter_feed(source)
        original = ET.fromstring(source)
        filtered = ET.fromstring(output)
        kept = filtered.findall('./shop/offers/offer')
        self.assertEqual([o.get('id') for o in kept], ['000', '001', '004'])
        for new, old in zip(kept, [original.findall('./shop/offers/offer')[i] for i in (0, 1, 4)]):
            self.assertEqual(ET.tostring(new), ET.tostring(old))
        self.assertEqual(ET.tostring(filtered.find('./shop/categories')),
                         ET.tostring(original.find('./shop/categories')))
        self.assertEqual(report, dict(source_offers=5, winter_offers=3, excluded_offers=2))

    def test_unknown_empty_and_invalid_sources_fail(self):
        for source in (catalog(['Unknown model']), catalog(['Summer лето']),
                       b'<html>error</html>', b'<yml_catalog>',
                       b'<!DOCTYPE x><yml_catalog/>'):
            with self.subTest(source=source), self.assertRaises((ValueError, ET.ParseError)):
                filter_feed(source)

    def test_explicit_nonwinter_markers_take_priority(self):
        self.assertEqual(season('All-Season winter suitable'), 'other')
        self.assertEqual(season('GREEN-Max Van 4S'), 'other')

    def test_duplicate_ids_fail(self):
        source = catalog(['зима', 'шип']).replace(b'id="001"', b'id="000"')
        with self.assertRaises(ValueError):
            filter_feed(source)

    def test_standard_yml_doctype_is_preserved(self):
        dtd = b'<!DOCTYPE yml_catalog SYSTEM "shops.dtd">'
        output, _ = filter_feed(dtd + catalog(['зима']))
        self.assertIn(dtd, output)
        self.assertEqual(len(ET.fromstring(output).findall('./shop/offers/offer')), 1)


if __name__ == '__main__':
    unittest.main()
