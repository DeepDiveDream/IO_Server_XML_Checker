from xmldiff import main, formatting
import xml.etree.ElementTree as ET
import sys
import psycopg2
from psycopg2 import Error


def connectToDataBase():
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="latyn",
                                      # пароль, который указали при установке PostgreSQL
                                      password="nytal",
                                      host="10.3.3.67",
                                      database="elsec")

        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        return cursor
        # Распечатать сведения о PostgreSQL
        print("Информация о сервере PostgreSQL")
        print(connection.get_dsn_parameters(), "\n")
        # Выполнение SQL-запроса
        cursor.execute("SELECT version();")
        # Получить результат
        record = cursor.fetchone()
        print("Вы подключены к - ", record, "\n")

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Соединение с PostgreSQL закрыто")


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
    # Подключение к существующей базе данных
    connection = psycopg2.connect(user="latyn",
                                  # пароль, который указали при установке PostgreSQL
                                  password="nytal",
                                  host="10.3.3.67",
                                  database="elsec")

    # Курсор для выполнения операций с базой данных
    cursor = connection.cursor()

    # Распечатать сведения о PostgreSQL
    print("Информация о сервере PostgreSQL")
    print(connection.get_dsn_parameters(), "\n")
    # Выполнение SQL-запроса
    cursor.execute("SELECT version();")
    # Получить результат
    record = cursor.fetchone()
    print("Вы подключены к - ", record, "\n")

    mode = 0
    out = compare_xmls("Hakas_kalina.xml", "Hakas_kalina1.xml", mode)

    if out == '':
        sys.exit(0)

    if mode == 0:
        root = ET.parse('Hakas_kalina.xml')
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
                    print("Действие: " + actionValue + ", Путь в XML: " + captionPath + ", Атрибут: " + name
                          + ", Новое значение: " + newValue + ", Старое значение: " + elm[0].attrib[name])
                    print(line + " Original value: " + elm[0].attrib[name])
                else:
                    print("Действие: " + actionValue + ", Путь в XML: " + captionPath)
                    print(line)
            else:
                print("Действие: " + actionValue + ", Путь в XML: " + captionPath)
                print(line)
    else:
        import re

        for i in out.splitlines():
            if re.search(r'\bdiff:\w+', i):
                print(i.strip())

except (Exception, Error) as error:
    print("Ошибка при работе: ", error)
    sys.exit(1)
finally:
    if connection:
        cursor.close()
        connection.close()
        sys.exit(0)
