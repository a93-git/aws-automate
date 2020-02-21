""" Validates the given cron expression as per the AWS' Scheduled expression for Cloudwatch Rules

For more details on the AWS' specification, refer to the below documentation:
https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html#CronExpressions

From the doc:
    "Cron expressions have six required fields, which are separated by white space."

TODO Validate cron expression
TODO Docstring
TODO '?' wildcard in DOM and DOW

Minutes parser - done
Hours parser - done
DoM - done
Month - done
DoW - ++ Not started yet ++
Year - done

Various weekday numbers referenced throughout the parser:

            SUN	MON	TUE	WED	THU	FRI	SAT
aws	        1	2	3	4	5	6	7
calendar	6	0	1	2	3	4	5
iso	        7	1	2	3	4	5	6
python      0   1   2   3   4   5   6

convert from iso weekday to aws:
aws_day = (isoweekday)%7 + 1

convert from calendar module weekday to aws (not perfect but works for now):
for Mon - Sat - calendarday + 2
for Sun - calendarday  - 5

1-7 - done
SUN-SAT - done
, - done
- - done
* - done
? - done
L - done
# - done
"""

import datetime
import calendar

FIELDS = ['Minutes', 'Hours', 'DoM', 'Month', 'DoW', 'Year']
VALUES = [[list(range(60)), ',', '-', '*', '/'], [list(range(24)), ',', '-', '*', '/'], [list(range(1, 32)), ',', '-', '*', '?', '/', 'L', 'W'], [dict(zip(range(1, 13), ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])), ',', '-', '*', '/'], [dict(zip(range(1-8), ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'])), ',', '-', '*', '?', 'L', '#'], list(range(1970, 2200))]
ALLOWED_VALUES = dict(zip(FIELDS, VALUES))
MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
MONTHS_NUMBER = dict(zip(MONTHS, range(1, 13)))
DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
DAYS_NUMBER = dict(zip(DAYS, range(1, 8)))


class CronParser():
    """

    """
    def __init__(self, cron_expression):
        """ Takes a cron expression as argument to initialize the object and extracts the field values

        Arguments:
        cron_expression - A string with six space separated fields

        Return:
        None
        """
        if type(cron_expression) is not str:
            print("Cron expression must be string type and not {0}".format(type(cron_expression)))
        else:
            self.expression = cron_expression.strip()
            self._expression_field_values = dict(zip(FIELDS, self.expression.split(' ')))

    def _check_dom_dotw(self, dom, dotw):
        """ Checks if both Day-of-month field and the Day-of-the-week fields have been specified

        Arguments:
        dom - Day-of-month field value
        dotw - Day-of-the-week field value

        Return:
        True if it doesn't match else False
        """
        if dom != '?' or dotw != '?':
            print("Out of DoM and DotW, one field must be '?'. Both can't be specified in the same expression")
            return False
        else:
            True

    def minute_parser(self):
        """ Returns a list of minute values in the cron expression"""

        minute = []
        try:
            minute.append(int(self._expression_field_values['Minutes']))
            # minute = int(self._expression_field_values['Minutes'])
            # return minute[0]
            return minute
        except:
            if self._expression_field_values['Minutes'] == '*':
                minute.append(datetime.datetime.utcnow().minute)
                # minute = datetime.datetime.utcnow().minute
                # return minute[0]
                return minute
            else:
                for i in self._expression_field_values['Minutes'].split(','):
                    try:
                        # minute = int(i)
                        minute.append(int(i))
                        # return minute[0]
                    except:
                        minute = []
                        j = i.split('/')
                        k = j[0].split('-')
                        if len(j) > 1:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1, int(j[1])) # Adding 1 to the stop value to make it inlcusive of the last value
                            else:
                                l = range(int(k[0]), 2*int(k[0]) + 1, int(j[1]))
                        else:
                            if len(k) > 1:
                                l = range(int(k[0]), int((k[1]) + 1))
                            else:
                                l = range(int(k[0], 2*int((k[0]) + 1)))
                        for i in list(l):
                            minute.append(i)
                # return minute[0]
                return minute

    def hour_parser(self):
        """ Returns a list of hour values as per the cron expression"""

        hour = []
        try:
            hour.append(int(self._expression_field_values['Hours']))
            # return hour[0]
            return hour
        except:
            if self._expression_field_values['Hours'] == '*':
                hour.append(datetime.datetime.utcnow().hour)
                # return hour[0]
                return hour
            else:
                for i in self._expression_field_values['Hours'].split(','):
                    try:
                        hour.append(int(i))
                    except:
                        j = i.split('/')
                        k = j[0].split('-')
                        # if len(j) > 1:
                        #     l = range(int(k[0]), int(k[1])+1, int(j[1]))
                        # else:
                        #     l = range(int(k[0]), int(k[1])+1)
                        # hour.append(list(l))
                        if len(j) > 1:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1, int(j[1]))
                            else:
                                # If there is only one value before / e.g. 6/6. It will go upto the next value
                                l = range(int(k[0]), 2*int(k[0]) + 1, int(j[1]))
                        else:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1)
                            else:
                                l = range(int(k[0]), 2*int(k[0])+1)
                        for i in list(l):
                            hour.append(i)

                # return hour[0]
                return hour

    def dom_parser(self, month, year=datetime.datetime.utcnow().year):
        """ Returns a list of DoM values in the cron expression
        
        Arguments:
        month - A list of months in which the cron is scheduled to run
        year - A list of years in which this cron is scheduled to run

        Return:
        A list of days in a month on which this cron will run
        """

        dom = []
        try:
            dom.append(int(self._expression_field_values['DoM']))
            # return dom[0]
            return dom
        except:
            if self._expression_field_values['DoM'] == '*':
                # Return dates till the last of the month
                for i in list(range(datetime.datetime.utcnow().day, [x for x in calendar.monthcalendar(year, month)[-1] if x != 0][-1] + 1)):
                    dom.append(i)
                # return dom[0]
                return dom
            elif self._expression_field_values['DoM'].upper() == 'L':
                for y in year:
                    a = {}
                    for m in month:
                        # Get the last day of the month (e.g. 31 or 29 or 30 etc.)
                        a[m] = [x for x in calendar.monthcalendar(y, m)[-1] if x != 0][-1]
                    dom.append(a)
                # return dom[0]
                return dom
            elif self._expression_field_values['DoM'] == '?':
                # '?' wildcard renders this field ineffective
                return ''
            elif 'W' in self._expression_field_values['DoM'].upper():
                date = int(self._expression_field_values['DoM'].upper().strip('W'))
                a = calendar.weekday(year, month, date)
                # In calender module, 5 == Saturday, 6 == Sunday, 1 == Monday
                _time_string = '{0}-{1}-{2}'.format(year, month, date)
                _format_string = r'%Y-%m-%d'
                if a == 5 or a == 6:
                    if a == 5:
                        # Get the last day if Saturday and the last day in the same month
                        b = month
                        last_day = datetime.datetime.strptime(_time_string, _format_string) - datetime.timedelta(days=1)
                        if last_day.month == b:
                            dom.append(last_day.day)
                            # return dom[0]
                            return dom
                        else:
                            # Else get the day next to Sunday
                            last_day = datetime.datetime.strptime(_time_string, _format_string) + datetime.timedelta(days=2)
                            dom.append(last_day.day)
                            # return dom[0]
                            return dom
                    elif a == 6:
                        # Get the next day if Sunday and the next day in the same month
                        b = month
                        next_day = datetime.datetime.strptime(_time_string, _format_string) + datetime.timedelta(days=1)
                        if next_day.month == b:
                            dom.append(next_day.day)
                            # return dom[0]
                            return dom
                        else:
                            # Else get the day before Saturday
                            next_day = datetime.datetime.strptime(_time_string, _format_string) - datetime.timedelta(days=2)
                            dom.append(next_day.day)
                            # return dom[0]
                            return dom
                    else:
                        dom.append(a+2) # There is a difference of 2 in weekdays between calendar days and AWS days (calendar: MON - 0, TUE - 1, ...; AWS: Mon - 2, TUE - 3, ...)
                        # return dom[0]
                        return dom
                else:
                    dom.append(int(self._expression_field_values['DoM'].upper().strip('W')))
                    # return dom[0]
                    return dom
            else:
                for i in self._expression_field_values['DoM'].split(','):
                    try:
                        dom.append(int(i))
                    except:
                        j = i.split('/')
                        k = j[0].split('-')
                        if len(j) > 1:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1, int(j[1]))
                            else:
                                # If there is only one value before / e.g. 6/6. It will go upto the next value
                                l = range(int(k[0]), 2*int(k[0]) + 1, int(j[1]))
                        else:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1)
                            else:
                                l = range(int(k[0]), 2*int(k[0])+1)
                        for i in list(l):
                            dom.append(i) # This one will send a list of lists
                # return dom[0]
                return dom

    def month_parser(self):
        """ Returns a list of month values as per the cron expression

        Return:
        A list with integer month values
        """

        month = []
        try:
            month.append(int(self._expression_field_values['Month']))
            # return month[0]
            return month
        except:
            if self._expression_field_values['Month'] == '*':
                month.append(datetime.datetime.utcnow().month)
                # return month[0]
                return month
            # Check if the below condition is required or already fulfilled by the try block
            elif self._expression_field_values['Month'] in ALLOWED_VALUES['Month'][0].keys():
                month.append(self._expression_field_values['Month'])
                # return month[0]
                return month
            elif self._expression_field_values['Month'].upper in ALLOWED_VALUES['Month'][0].values():
                # Single string month
                month.append(MONTHS_NUMBER[self._expression_field_values['Month']])
                # return month[0]
                return month
            else:
                for i in self._expression_field_values['Month'].split(','):
                    try:
                        month.append(int(i))
                    except:
                        j = i.split('/')
                        k = j[0].split('-')
                        try:
                            if len(j) > 1:
                                if len(k) > 1:
                                    l = range(int(k[0]), int(k[1])+1, int(j[1]))
                                else:
                                    l = range(int(k[0]), 2*int(k[0]) + 1, int(j[1]))
                            else:
                                if len(k) > 1:
                                    l = range(int(k[0]), int(k[1]) + 1)
                                else:
                                    l = range(int(k[0]), 2*int(k[0]))
                            for i in list(l):
                                month.append(i)
                        except:
                            try:
                                # String months range
                                p = MONTHS_NUMBER[k[0]]
                                q = MONTHS_NUMBER[k[1]]
                                if len(j) > 1:
                                    l = range(int(p), int(q)+1, int(j[1]))
                                else:
                                    l = range(int(p), int(q)+1)
                                for i in list(l):
                                    month.append(i)
                            except Exception as e:
                                print("Error in parsing month values. Given value is {0}".format(self._expression_field_values['Month']))
                                print("Error message is {0}".format(e))
                                raise e
                # return month[0]
                return month

    def dow_parser(self, month=None, year=None):
        """ Returns a list of DoW values in the cron expression
        
        Arguments:
        month - required to evaluate the nth day of week e.g. 2nd Friday of the month
        year - required to evaluate the nth day of week e.g. 2nd Friday of the month in a given year

        Return:
        A list of days of a week on which this cron will run
        In case of L, it will return a list containing the date for the next run
        """

        dow = []
        try:
            dow.append(int(self._expression_field_values['DoW']))
            # return dow[0]
            return dow
        except:
            if self._expression_field_values['DoW'] == '*':
                dow.append(datetime.datetime.isoweekday(datetime.datetime.utcnow()))
                # return dow[0]
                return dow
            # Check if the below condition is required or already fulfilled by the try block
            elif self._expression_field_values['DoW'] in ALLOWED_VALUES['DoW'][0].keys():
                dow.append(int(self._expression_field_values['DoW']))
                # return dow[0]
                return dow
            elif self._expression_field_values['DoW'].upper in ALLOWED_VALUES['DoW'][0].values():
                # Single string day of week
                dow.append(MONTHS_NUMBER[self._expression_field_values['DoW']])
                # return dow[0]
                return dow
            elif self._expression_field_values['DoW'].upper() == 'L':
                # 'L' in DoW expression stands for the last day of the week
                # For AWS cron expressions, last day is Saturday (7)
                # Find the next nearest Saturday

                # Get today's day
                _day_today = datetime.datetime.isoweekday(datetime.datetime.utcnow()) % 7 + 1
                _sat = 7
                # Number of days in between today and the next Saturday
                _delta = abs(_sat - _day_today)

                # Day on the next Saturday
                _next_sat = datetime.datetime.utcnow() + datetime.timedelta(days=_delta)
                dow.append([_next_sat.day, _next_sat.month, _next_sat.year])
                # return dow[0]
                return dow
            elif self._expression_field_values['DoW'] == '?':
                # '?' wildcard renders this field ineffective
                return ''
            
            elif '#' in self._expression_field_values['DoW']:

                # Refactor the code below

                # Find the _nth _day_of_week in a month e.g. 2nd Friday
                a = self._expression_field_values['DoW'].split('#')
                _aws_day_of_week = int(a[0])
                _nth = a[1]
                _day_today = datetime.datetime.utcnow()
                _month_calendar = calendar.monthcalendar(year, month)

                # Check this module's docstring for the below conversion context
                if 2 <= _aws_day_of_week <= 7:
                    _calendar_day_of_week = _aws_day_of_week - 2
                else:
                    _calendar_day_of_week = 6

                o = []
                for val in _month_calendar:
                    if val[_calendar_day_of_week] != 0: # 0 is a placeholder in the calendar output for days of week that don't belong to the current month
                            o.append()

                if o[_nth] > _day_today.day:
                    return o[_nth]
                else:
                    _month_calendar = calendar.monthcalendar(year, month)

                    # Check this module's docstring for the below conversion context
                    if 2 <= _aws_day_of_week <= 7:
                        _calendar_day_of_week = _aws_day_of_week - 2
                    else:
                        _calendar_day_of_week = 6

                    o = []
                    for val in _month_calendar:
                        if val[_calendar_day_of_week] != 0: # 0 is a placeholder in the calendar output for days of week that don't belong to the current month
                                o.append()
                    return o[_nth]
            else:
                for i in self._expression_field_values['DoW'].split(','):
                    try:
                        dow.append(int(i))
                    except:
                        k = i.split('-')
                        try:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1)
                            else:
                                l = range(int(k[0]), 2 * int(k[0]) + 1)
                            for i in list(l):
                                dow.append(i)
                        except:
                            try:
                                # String day of week range
                                p = DAYS_NUMBER[k[0]]
                                q = DAYS_NUMBER[k[1]]
                                l = range(int(p), int(q)+1)
                                for i in list(l):
                                    dow.append(i)
                            except Exception as e:
                                print("Error in parsing day of week values. Given value is {0}".format(self._expression_field_values['DoW']))
                                print("Error message is {0}".format(e))
                                raise e
            # return dow[0]
            return dow
        
    def year_parser(self):
        """ Returns a list of year values as per the cron expression"""

        year = []
        try:
            year.append(int(self._expression_field_values['Year']))
            # return year[0]
            return year
        except:
            if self._expression_field_values['Year'] == '*':
                year.append(datetime.datetime.utcnow().year)
                # return year[0]
                return year
            else:
                for i in self._expression_field_values['Year'].split(','):
                    try:
                        year.append(int(i))
                    except:
                        j = i.split('/')
                        k = j[0].split('-')
                        if len(j) > 1:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1, int(j[1]))
                            else:
                                l = range(int(k[0]), 2*int(k[0])+1, int(j[1]))
                        else:
                            if len(k) > 1:
                                l = range(int(k[0]), int(k[1])+1)
                            else:
                                l = range(int(k[0]), 2*int(k[0])+1)
                        for i in list(l):
                            year.append(i)
                # return year[0]
                return year

    def create_next_run_value(self):
        minute = self.minute_parser()
        hour = self.hour_parser()
        month = self.month_parser()
        year = self.year_parser()

        for y in year:
            for m in month:
                for h in hour:
                    for m2 in minute:
                        for d in self.dom_parser(m, y):
                            print('{0}-{1}-{2} {3}:{4}'.format(y, m, d, h, m2))

        # dom = self.dom_parser(month[0], year[0])
        # dow = self.dow_parser()

        # _time_string = "{0}-{1}-{2}-{3}-{4}".format(year, month, dom, hour, minute)
        # _format_string = '%Y-%m-%d-%H-%M'
        # next_run_time = datetime.datetime.strptime(_time_string, _format_string)

        # print(next_run_time)

        # print('Minute: {0}'.format(minute))
        # print('Hour: {0}'.format(hour))
        # print('Month: {0}'.format(month))
        # print('Year: {0}'.format(year))
        # print('DoM: {0}'.format(dom))
        # print('DoW: {0}'.format(dow))

if __name__ == '__main__':
    # a = CronParser('4-10/3 0-4,6/6 * * ? *')
    # a = CronParser('4-10/3 0-4,6/6 31W 5 ? *')
    a.create_next_run_value()