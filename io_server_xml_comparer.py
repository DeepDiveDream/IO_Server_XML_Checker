#!/usr/bin/python3
from xmldiff import main, formatting
import xml.etree.ElementTree as ET
import sys
import psycopg2
from psycopg2 import Error
import json
from argparse import ArgumentParser
import configparser
from datetime import datetime
from pathlib import Path


def fields(cursor):
    results = {}
    column = 0

    for d in cursor.description:
        results[d[0]] = column
        column += 1

    return results


def connect_to_postgre(dbase, login, password, host, port):
    try:
        conn = psycopg2.connect(
            database=dbase,
            user=login,
            password=password,
            port=port,
            host=host)
        print(f"{currentScript} {datetime.now()} Соединение с БД {dbase}, сервер {host} успешно!")
        return conn
    except (Exception, Error) as connect_error:
        print(f"{currentScript} {datetime.now()} Ошибка соеденения с БД {dbase} сервер {host}: {connect_error}")


def get_name_of_deleted_tag(input_string):
    lines = input_string.split(',')
    attr_name = lines[1].lstrip()
    if attr_name[-1] == "]":
        attr_name = attr_name[:-1]

    return attr_name


def get_name_of_original_attr(input_string):
    lines = input_string.split(',')
    attr_name = lines[2].lstrip()
    if attr_name[-1] == "]":
        attr_name = attr_name[:-1]

    return attr_name


def get_path_to_original_attr(input_string):
    path_to_attribute = "."
    lines = input_string.split(',')
    tmp = lines[1].lstrip()

    if tmp.count('/') == 1:
        return path_to_attribute

    pos = tmp.find('/', tmp.find('/') + 1)
    path_to_attribute += tmp[pos:]

    if path_to_attribute[-2] == "]":
        path_to_attribute = path_to_attribute[:-1]

    return path_to_attribute


def get_caption_path_to_attr(input_string, is_original):
    tmp_lines = input_string.split('/')
    tmp_path = ""
    caption_path = ""

    for tmp_line in tmp_lines:
        tmp_path += tmp_line

        if is_original:
            elm1 = root_origin.findall(tmp_path)
        else:
            elm1 = root_new.findall(tmp_path)

        if len(elm1) > 0:
            # caption_path += elm1[0].tag

            if elm1[0].tag == "configuration":
                continue

            if elm1[0].tag == "direction":
                caption_path += "Направление -> "

            if 'caption' in elm1[0].attrib:
                caption_path += "" + elm1[0].attrib["caption"] + "/"
            else:
                caption_path += "/"
            tmp_path += "/"

    return caption_path


def compare_xmlns(observed, expected, xml_format_mode=0):
    if xml_format_mode == 0:
        formatter = formatting.DiffFormatter(normalize=formatting.WS_BOTH)
    else:
        formatter = formatting.XMLFormatter(normalize=formatting.WS_BOTH)

    diff = main.diff_files(observed, expected, formatter=formatter)
    return diff


if __name__ == "__main__":

    mode = 0

    currentScript = '[IO_Server_XML_Comparer]'

    parser = ArgumentParser()
    parser.add_argument('configPath', type=str, help='Path to config file', default='config.json', nargs='?')
    args = parser.parse_args()
    config_path = args.configPath

    with open(config_path, 'r') as f:
        config_data = json.load(f)
        ini_file_path = config_data['ini_file_path']

    config_ini = configparser.ConfigParser()
    config_ini.read(ini_file_path)

    postgre_user = config_ini.get('common', 'pguser')
    postgre_pass = config_ini.get('common', 'pgpassword')
    postgre_host = config_ini.get('common', 'pghost')
    postgre_port = config_ini.get('common', 'pgport')
    postgre_database = config_ini.get('common', 'pgdb')

    xml_dir = config_ini.get('io_server_xml_comparer', 'xml_dir')

    connection = connect_to_postgre(postgre_database, postgre_user, postgre_pass, postgre_host, postgre_port)

    if not connection:
        sys.exit(1)

    # print('Connected')

    postgre_cursor = connection.cursor()
    try:

        postgre_cursor.execute("SELECT * FROM event_source_params('ioServerXML')")

        fields_map_params = fields(postgre_cursor)
        params = postgre_cursor.fetchone()

        if params is None:
            print(f'{currentScript} {datetime.now()} Не заполнены параметры для источника ioServerXML')
            sys.exit(2)

        event_source = params[fields_map_params['id']]
        param_dict = params[fields_map_params['params']]

        if len(param_dict) == 0:
            print(f'{currentScript} {datetime.now()} Не заполнены параметры для источника ioServerXML')
            sys.exit(2)

        original_file = xml_dir + param_dict["original_file"]

        path = Path(original_file)
        if not path.is_file():
            print(f'{currentScript} {datetime.now()} Эталонный XML файл {original_file} сервера ввода-вывода не найден!')
            sys.exit(2)

        input_file = xml_dir + param_dict["input_file"]

        path = Path(input_file)
        if not path.is_file():
            print(f'{currentScript} {datetime.now()} Проверяемый XML файл {input_file} сервера ввода-вывода не найден!')
            sys.exit(2)

        out = compare_xmlns(original_file, input_file, mode)
        # out = compare_xmlns(original_file_path, input_file_path, mode)
        sql = ""

        if out == '':

            sys.exit(0)

            # postgre_cursor.execute("SELECT id From event_type where name = \'configNotChanged.ioServerXML\' ")
            # event_type = postgre_cursor.fetchone()[0]
            #
            # json_data = {
            #     "data": 'Изменения не найдены',
            #     "display": {
            #         "Изменения": ''
            #     }
            # }
            #
            # data = json.dumps(json_data)
            #
            # postgre_cursor.callproc('event_new', [event_type, event_source, False, data])
            #
            # connection.commit()
            # postgre_cursor.close()
            # # print("No changes")
            # sys.exit(0)

        if mode == 0:
            root_origin = ET.parse(original_file)
            root_new = ET.parse(input_file)
            changesResult = ""
            changesPath = ""

            postgre_cursor.execute("SELECT id From event_type where name = \'configChanged.ioServerXML\' ")
            event_type = postgre_cursor.fetchone()[0]

            for line in out.splitlines():
                path = get_path_to_original_attr(line)
                captionPath = get_caption_path_to_attr(path, True)
                splitResult = line.split(',')
                actionValue = splitResult[0][1:]

                changesPath += line + "\n"

                if "update-attribute" in line or "delete-attribute" in line:

                    elm = root_origin.findall(path)

                    name = get_name_of_original_attr(line)
                    newValue = ""
                    if len(splitResult) > 3:
                        newValue = line.split(',')[3][:-1]

                    if actionValue == "update-attribute":
                        actionValue = "<br>Обнаружено изменение значения свойства!"
                    else:
                        actionValue = "<br>Обнаружено удаление свойства!"

                    if name in elm[0].attrib:
                        changesResult += actionValue + "<br> &nbsp &nbsp &nbsp Место изменения: &nbsp " + captionPath + \
                                         "<br> &nbsp &nbsp &nbsp Свойство: &nbsp " + name + ', &nbsp Новое значение: &nbsp' + newValue + \
                                         ',&nbsp Старое значение: "' + elm[0].attrib[name] + '"<br>'
                    else:
                        changesResult += actionValue + "<br>&nbsp &nbsp &nbsp Место изменения: " + captionPath + "<br>"

                elif "insert-attribute" in line:

                    captionPath = get_caption_path_to_attr(path, False)
                    name = get_name_of_original_attr(line)
                    newValue = ""
                    if len(splitResult) > 3:
                        newValue = line.split(',')[3][:-1]

                    actionValue = "<br>Обнаружено добавление нового свойства!"

                    changesResult += actionValue + "<br> &nbsp &nbsp &nbsp Место изменения:&nbsp " + captionPath + \
                                     "<br>&nbsp &nbsp &nbsp Свойство: " + name + ",&nbsp Новое значение:" + newValue + "<br>"

                elif "insert" in line and "attribute" not in line:

                    actionValue = "<br>Обнаружено изменение структуры XML!"

                    changesResult += actionValue + "<br> &nbsp &nbsp &nbsp Путь в XML:&nbsp " + captionPath + ",&nbsp Добавлен тэг:&nbsp " \
                                     + splitResult[2].strip() + "<br>"

                elif "rename" in line and "attribute" not in line:
                    actionValue = "<br>Обнаружено изменение структуры XML!"
                    changesResult += actionValue + "<br>&nbsp &nbsp &nbspПуть в XML:&nbsp " + \
                                     captionPath + ",&nbsp Новое имя тега:&nbsp [" + splitResult[2].strip() + "<br>"

                elif "delete" in line and "attribute" not in line:

                    actionValue = "<br>Обнаружено изменение структуры XML!"

                    deleted_tag_path = splitResult[1].strip()
                    deleted_tag_pos = deleted_tag_path.rfind('/')
                    deleted_tag_name = deleted_tag_path[deleted_tag_pos + 1:]

                    deleted_tag_pos = deleted_tag_name.find('[')
                    deleted_tag_name = deleted_tag_name[:deleted_tag_pos]

                    changesResult += actionValue + "<br> &nbsp &nbsp &nbsp Путь в XML: " + captionPath + "," \
                                                                                                         "&nbsp Удаленный тег:&nbsp " + deleted_tag_name + "<br>"

                else:
                    actionValue = "<br>Обнаружено изменение структуры XML!"
                    changesResult += actionValue + "<br> &nbsp &nbsp &nbsp Путь в XML:&nbsp " + captionPath + "<br>"

            # print(changesResult)
            # print(changesPath)

            json_data = {
                "data": [changesPath],
                "display": {
                    "Изменения": changesResult
                }
            }

            data = json.dumps(json_data)
            postgre_cursor.callproc('event_new', [event_type, event_source, True, data])

            connection.commit()
        else:
            import re

            for i in out.splitlines():
                if re.search(r'\bdiff:\w+', i):
                    print(i)

    except (Exception, Error) as error:

        conn_err = connect_to_postgre(postgre_database, postgre_user, postgre_pass, postgre_host, postgre_port)

        if not conn_err:
            sys.exit(1)

        cursorException = conn_err.cursor()
        errorStr = error.args[0]
        start = errorStr.find('\n')
        errorStr = errorStr[:start]
        errorStr = errorStr.replace("\"", "")
        errorStr = errorStr.replace("\'", "")

        cursorException.execute("SELECT id From event_type where name = \'error.ioServerXML\'")
        event_type = cursorException.fetchone()[0]

        cursorException.execute("SELECT * From event_source_params('ioServerXML')")
        event_source = cursorException.fetchone()[0]

        data = json.dumps({'data': errorStr})
        cursorException.callproc('event_new', [event_type, event_source, False, data])

        conn_err.commit()
        cursorException.close()
        # print(error)
        sys.exit(1)
    finally:
        if connection:
            postgre_cursor.close()
            connection.close()
