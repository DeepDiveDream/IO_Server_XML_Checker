from xmldiff import main, formatting
import xml.etree.ElementTree as ET
import sys
import psycopg2


def connectToDataBase():
    from psycopg2 import Error
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
    return path_to_atrribute


def get_caption_path_to_attr(inputString):
    lines = inputString.split('/')
    tmp_path = ""
    captionPath = ""

    for line in lines:
        tmp_path += line
        elm = root.findall(tmp_path)
        captionPath += elm[0].tag
        if 'caption' in elm[0].attrib:
            captionPath += "[" + elm[0].attrib["caption"] + "]/"
        else:
            captionPath += "/"

        tmp_path += "/"

    return captionPath


def compare_xmls(observed, expected, XMLFormatMode=0):
    if XMLFormatMode == 0:
        formatter = formatting.DiffFormatter()
    else:
        formatter = formatting.XMLFormatter(normalize=formatting.WS_BOTH)

    diff = main.diff_files(observed, expected, formatter=formatter)
    return diff


# connectToDataBase()

mode = 0
out = compare_xmls("Hakas_kalina.xml", "Hakas_kalina1.xml", mode)

if out == '':
    sys.exit(0)

root = ET.parse('Hakas_kalina.xml')
for line in out.splitlines():
    path = get_path_to_original_attr(line)
    print(path)
    print(get_caption_path_to_attr(path))
    if "update-attribute" in line or "delete-attribute" in line:
        elm = root.findall(path)
        name = get_name_of_original_attr(line)
        if name in elm[0].attrib:
            print(line + " Original value: " + elm[0].attrib[name])
        else:
            print(line)
    else:
        print(line)

sys.exit(1)
