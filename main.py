from xmldiff import main, formatting
import xml.etree.ElementTree as ET
import sys
import psycopg2
from psycopg2 import Error
from datetime import datetime, timezone
import json


def connectToDataBase():
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="latyn",
                                      # пароль, который указали при установке PostgreSQL
                                      password="nytal",
                                      host="10.3.3.67",
                                      database="elsec")

        # Курсор для выполнения операций с базой данных
        # cursor = connection.cursor()
        return connection
        # # Распечатать сведения о PostgreSQL
        # print("Информация о сервере PostgreSQL")
        # print(connection.get_dsn_parameters(), "\n")
        # # Выполнение SQL-запроса
        # cursor.execute("SELECT version();")
        # # Получить результат
        # record = cursor.fetchone()
        # print("Вы подключены к - ", record, "\n")

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)

    # finally:
    #     if connection:
    #         cursor.close()
    #         connection.close()
    #         print("Соединение с PostgreSQL закрыто")


def get_name_of_original_attr(inputString):
    lines = inputString.split(',')
    name = lines[2].lstrip()
    if name[-1] == "]":
        name = name[:-1]

    return name


def get_path_to_original_attr(inputString):
    path_to_atrribute = "."
    lines = inputString.split(',')
    tmp = lines[1].lstrip()

    if tmp.count('/') == 1:
        return path_to_atrribute

    start = tmp.find('/', tmp.find('/') + 1)
    path_to_atrribute += tmp[start:]

    if path_to_atrribute[-2] == "]":
        path_to_atrribute = path_to_atrribute[:-1]

    return path_to_atrribute


def get_caption_path_to_attr(inputString):
    tmp_lines = inputString.split('/')
    tmp_path = ""
    caption_path = ""

    for tmp_line in tmp_lines:
        tmp_path += tmp_line
        elm1 = root.findall(tmp_path)

        if len(elm1) > 0:
            caption_path += elm1[0].tag
            if 'caption' in elm1[0].attrib:
                caption_path += "[" + elm1[0].attrib["caption"] + "]/"
            else:
                caption_path += "/"
            tmp_path += "/"

    return caption_path


def compare_xmls(observed, expected, XMLFormatMode=0):
    if XMLFormatMode == 0:
        formatter = formatting.DiffFormatter(normalize=formatting.WS_BOTH)
    else:
        formatter = formatting.XMLFormatter(normalize=formatting.WS_BOTH)

    diff = main.diff_files(observed, expected, formatter=formatter)
    return diff


try:

    connection = connectToDataBase()
    if not connection:
        sys.exit(1)

    mode = 0
    cursor = connection.cursor()
    out = compare_xmls("Hakas_kalina.xml", "Hakas_kalina1.xml", mode)
    sql = ""

    if out == '':
        cursor.execute("SELECT id From event_type where name = \'configNotChanged.ioServerXML\' ")
        event_type = cursor.fetchone()[0]

        cursor.execute("SELECT id From event_source where caption = \'Хакасэнерго\' ")
        event_source = cursor.fetchone()[0]

        currentDate = datetime.now()
        data = json.dumps({'result': 'No changes found'})
        sql = "INSERT INTO event (parent, created, type, source, enduser, handledelay, handled, data)" \
              " VALUES (null, timestamp \'{}\', {}, {}, false , 0, null , \'{}\')".format(currentDate, event_type,
                                                                                          event_source, data)
        cursor.execute(sql)
        connection.commit()
        cursor.close();
        connection.close;
        sys.exit(0)

    if mode == 0:
        root = ET.parse('Hakas_kalina.xml')
        changesResult = ""
        changesPath = ""

        cursor.execute("SELECT id From event_type where name = \'configChanged.ioServerXML\' ")
        event_type = cursor.fetchone()[0]

        cursor.execute("SELECT id From event_source where caption = \'Хакасэнерго\' ")
        event_source = cursor.fetchone()[0]

        for line in out.splitlines():
            path = get_path_to_original_attr(line)
            captionPath = get_caption_path_to_attr(path)
            tmp = line.split(',')
            actionValue = tmp[0][1:]

            if "update-attribute" in line or "delete-attribute" in line:
                elm = root.findall(path)
                name = get_name_of_original_attr(line)
                newValue = ""
                if len(tmp) > 3:
                    newValue = line.split(',')[3][:-1]

                if name in elm[0].attrib:
                    changesResult += "Действие: " + actionValue + ", Путь в XML: " + captionPath + ", Атрибут: " + \
                                     name + ", Новое значение: " + newValue + ", Старое значение: " \
                                     + elm[0].attrib[name] + "\n"
                    # print("Действие: " + actionValue + ", Путь в XML: " + captionPath + ", Атрибут: " + name
                    #       + ", Новое значение: " + newValue + ", Старое значение: " + elm[0].attrib[name])
                    # print(line + " Original value: " + elm[0].attrib[name])

                else:
                    changesResult += "Действие: " + actionValue + ", Путь в XML: " + captionPath
                    # print("Действие: " + actionValue + ", Путь в XML: " + captionPath)
                    # print(line)
                changesPath += line
            else:
                changesResult += "Действие: " + actionValue + ", Путь в XML: " + captionPath
                # print("Действие: " + actionValue + ", Путь в XML: " + captionPath)
                # print(line)
                changesPath += line

        currentDate = datetime.now()
        data = json.dumps([{'result': changesResult}, {'path': changesPath}])
        sql = "INSERT INTO event (parent, created, type, source, enduser, handledelay, handled, data)" \
              " VALUES (null, timestamp \'{}\', {}, {}, true , 0, null , \'{}\')".format(currentDate, event_type,
                                                                                         event_source, data)
        cursor.execute(sql)
        connection.commit()



    else:
        import re

        for i in out.splitlines():
            if re.search(r'\bdiff:\w+', i):
                print(i.strip())

except (Exception, Error) as error:
    conn = connectToDataBase()
    cursorException = conn.cursor()
    currentDate = datetime.now()
    errorStr = error.args[0]
    # print(errorStr)
    start = errorStr.find('\n')
    errorStr = errorStr[:start]
    errorStr = errorStr.replace("\"", "")
    errorStr = errorStr.replace("\'", "")
    # print(errorStr)

    cursorException.execute("SELECT id From event_type where name = \'error.ioServerXML\' ")
    event_type = cursorException.fetchone()[0]

    cursorException.execute("SELECT id From event_source where caption = \'Хакасэнерго\' ")
    event_source = cursorException.fetchone()[0]

    data = json.dumps([{'result': errorStr}])
    # print(data)
    sql = "INSERT INTO event (parent, created, type, source, enduser, handledelay, handled, data)" \
          " VALUES (null, timestamp \'{}\', {}, {}, false , 0, null , \'{}\')".format(currentDate, event_type,
                                                                                      event_source, data)
    # print(sql)
    cursorException.execute(sql)
    conn.commit()
    cursorException.close();
    conn.close;
    # print(error)
    sys.exit(1)
finally:
    print("Finally")
    if connection:
        cursor.close()
        connection.close()
        sys.exit(0)
