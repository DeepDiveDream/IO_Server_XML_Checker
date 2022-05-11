from xmldiff import main, formatting
import xml.etree.ElementTree as ET
import sys
import psycopg2
from psycopg2 import Error
import json
from argparse import ArgumentParser




def connect_to_data_base():
    try:
        # Подключение к существующей базе данных
        postgre_connection = psycopg2.connect(user=postgre_user,
                                              password=postgre_pass,
                                              host=postgre_host,
                                              database=postgre_database)
        return postgre_connection

    except (Exception, Error) as connection_error:
        print("Ошибка при работе с PostgreSQL", connection_error)


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

    parser = ArgumentParser()
    parser.add_argument('configPath', type=str, help='Path to config file', default='config.json', nargs='?')
    args = parser.parse_args()
    config_path = args.configPath

    with open(config_path, 'r') as f:
        config_data = json.load(f)
        postgre_user = config_data['postgre_user']
        postgre_pass = config_data['postgre_pass']
        postgre_host = config_data['postgre_host']
        postgre_database = config_data['postgre_database']
        local_original_file_path = config_data['standart_file_path']
        local_input_file_path = config_data['input_file_path']

    mode = 0

    connection = connect_to_data_base()

    if not connection:
        sys.exit(1)

    cursor = connection.cursor()
    try:

        cursor.execute("SELECT * FROM event_source_params('ioServerXML')")
        params = cursor.fetchone()

        # print(params)

        event_source = params[0]
        param_dict = params[4]

        ip_address = param_dict["ip"]
        login = param_dict["login"]
        input_file_path = param_dict["input_file_path"]
        original_file_path = param_dict["original_file_path"]

        out = compare_xmlns(original_file_path, input_file_path, mode)
        sql = ""

        if out == '':
            cursor.execute("SELECT id From event_type where name = \'configNotChanged.ioServerXML\' ")
            event_type = cursor.fetchone()[0]

            json_data = {
                "data": 'Изменения не найдены',
                "display": {
                    "Изменения": ''
                }
            }

            data = json.dumps(json_data)

            cursor.callproc('event_new', [event_type, event_source, False, data])

            connection.commit()
            cursor.close()
            # print("No changes")
            sys.exit(0)

        if mode == 0:
            root_origin = ET.parse(original_file_path)
            root_new = ET.parse(input_file_path)
            changesResult = ""
            changesPath = ""

            cursor.execute("SELECT id From event_type where name = \'configChanged.ioServerXML\' ")
            event_type = cursor.fetchone()[0]

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
            cursor.callproc('event_new', [event_type, event_source, True, data])

            connection.commit()
        else:
            import re

            for i in out.splitlines():
                if re.search(r'\bdiff:\w+', i):
                    print(i)

    except (Exception, Error) as error:
        conn = connect_to_data_base()
        cursorException = conn.cursor()
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

        conn.commit()
        cursorException.close()
        # print(error)
        sys.exit(1)
    finally:
        if connection:
            cursor.close()
            connection.close()
