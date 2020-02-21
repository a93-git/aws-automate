import unittest
import awscronparser
import datetime
import calendar

class TestDomParser(unittest.TestCase):

    def test_start_value(self):
        f = awscronparser.CronParser('0 0 * * 4 *')
        g = f.dom_parser('*')
        self.assertEqual(g, list(range(datetime.datetime.utcnow().day), [x for x in calendar.monthcalendar(year[0], month[0])[-1] if x != 0][-1]))

    def test_int_range_value(self):
        f = awscronparser.CronParser('0 0 4-6 * ? *')
        g = f.dom_parser('4-6')
        self.assertEqual(g, [[4, 5, 6]])

if __name__ == '__main__':
    unittest.main()