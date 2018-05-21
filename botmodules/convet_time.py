import datetime, time


def convert_to_epoch(input_value):
    input_date = input_value.split('-')

    try:
        year = int(input_date[0])
        month = int(input_date[1])
        day = int(input_date[2])
    except ValueError:
        print("Wrong Format or out of Range")
    except IndexError:
        print("Missing Year, Month or Day")

    epoch_time = datetime.datetime(year, month, day).timestamp()

    return (epoch_time)

    # Test of value is correct
    # date_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))
    # print(date_time)

def convert_to_datetime(input_value):

    return (datetime.datetime.fromtimestamp(input_value, datetime.timezone.utc))
    #return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(input_value))