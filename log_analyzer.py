import argparse
import configparser
import collections
import datetime
import gzip
import json
import logging
import os
from pathlib import Path
import re
from statistics import median
import string
from typing import Dict, Optional, Union


CONFIG = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': './reports',
    'LOG_DIR': './log',
    'REPORT_TEMPL_PATH': './report_templ.html',
    'CRIT_ERR_PERCENT': 30,
}

LastFileData = collections.namedtuple('last_file_data', ['file_name', 'file_date'])


def main(config_file_path: str) -> None:

    # Получим настройки из файла и смержим с настройками по умолчанию
    config_dict = read_config(config_file_path, CONFIG)

    # Настроим логирование
    logging.basicConfig(
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        filename=config_dict['self_log_file'],
        filemode='a',
        level=logging.INFO,
    )

    logging.info('Начинаем обработку')

    # Отловим 'неожиданные ошибки', чтобы записать их в лог
    try:
        # Проверим, есть ли где искать
        log_dir = Path(config_dict['log_dir'])
        if log_dir.exists():

            # Ищем самый 'свежий' лог
            target_file = search_last_file(config_dict['log_dir'])

            # Если ничего не нашли, то и делать дальше нечего
            if target_file.file_name:

                log_path = log_dir / target_file.file_name
                rep_dir = Path(config_dict['rep_dir'])
                target_report_path = rep_dir / ('report-' + target_file.file_date.strftime('%Y.%m.%d') + '.html')

                # Проверим, нет ли уже сформированного отчета по этому файлу и если есть выходим
                if not target_report_path.exists():

                    # Парсим файл лога, за одно считаем общее количество записей и общую сумму времени
                    parsed_data = parse_file(log_path)
                    if not parsed_data['all_count']:
                        err_percent = 100
                    else:
                        if parsed_data['err_count'] > 0:
                            err_percent = (parsed_data['err_count'] / parsed_data['all_count']) * 100
                        else:
                            err_percent = 0

                    # Если превышено относительно количество обработанных с ошибкой записей, пишем в лог и выходим
                    if err_percent <= config_dict['crit_err_percent']:

                        # Посчитаем все необходимые значения и отсортируем по time_sum
                        calc_data = enrich_log_data(parsed_data)

                        # Берём первые rep_size записи, формируем в json формат и дампим
                        dump_json_data = generate_json(calc_data, config_dict['rep_size'])

                        # Рендерим отчет
                        create_report(dump_json_data, config_dict['report_templ_path'], target_report_path)
                        logging.info('Обработка завершена. Результат находится в {}'.format(target_report_path))

                    else:
                        logging.info(
                            'Процент ошибок {}, что превышает максимальный порог {}. Прерываем выполнение.'.format(
                                err_percent, config_dict['crit_err_percent']
                            )
                        )
                else:
                    logging.info(
                        'Файл {} уже был обработан ранее, результат в {}'.format(
                            target_file.file_name, target_report_path
                        )
                    )
            else:
                logging.info('Ни один подходящий файл в директории {} не найден'.format(config_dict['log_dir']))
        else:
            logging.info('Директория логов {} не найдена'.format(config_dict['log_dir']))

    except Exception:
        logging.exception('Непредвиденная ошибка, запишем в лог')
        raise


def read_config(
    config_file_path: str, def_config: Optional[Dict[str, Union[int, str]]] = None
) -> Dict[str, Union[int, str]]:
    """
    Читаем конфиг файл и соединяем в приоритете с дефолтными настройками
    :param config_file_path: путь до файла настройки
    :type config_file_path: str
    :param def_config: дефолтные настройки
    :type def_config: Dict[str, Union[int, str]
    :return: возвращаем словарь с параметрами
    :rtype: Dict[str, Union[int, str]
    """

    def_config = def_config or {}
    config_file = configparser.ConfigParser()
    config_file.read(config_file_path)
    res_dict = {}
    if config_file.has_option('Options', 'SELF_LOG_FILE'):
        res_dict['self_log_file'] = config_file['Options']['SELF_LOG_FILE']
    else:
        res_dict['self_log_file'] = None

    if config_file.has_option('Options', 'LOG_DIR'):
        res_dict['log_dir'] = config_file['Options']['LOG_DIR']
    else:
        res_dict['log_dir'] = def_config.get('LOG_DIR')

    if config_file.has_option('Options', 'REPORT_DIR'):
        res_dict['rep_dir'] = config_file['Options']['REPORT_DIR']
    else:
        res_dict['rep_dir'] = def_config.get('REPORT_DIR')

    if config_file.has_option('Options', 'REPORT_SIZE'):
        res_dict['rep_size'] = int(config_file['Options']['REPORT_SIZE'])
    else:
        res_dict['rep_size'] = def_config.get('REPORT_SIZE')

    if config_file.has_option('Options', 'REPORT_TEMPL_PATH'):
        res_dict['report_templ_path'] = config_file['Options']['REPORT_TEMPL_PATH']
    else:
        res_dict['report_templ_path'] = def_config.get('REPORT_TEMPL_PATH')

    if config_file.has_option('Options', 'CRIT_ERR_PERCENT'):
        res_dict['crit_err_percent'] = int(config_file['Options']['CRIT_ERR_PERCENT'])
    else:
        res_dict['crit_err_percent'] = def_config.get('CRIT_ERR_PERCENT')

    return res_dict


def search_last_file(log_dir: str) -> LastFileData:
    """
    Ищет в указанной директории последний файл лога соответствующий шаблону имени
    :param log_dir: путь до директории с файлами логов
    :type log_dir: str
    :return: возвращаем имя и дату найденного файла
    :rtype: tuple
    """

    last_date = None
    last_file_name = None
    re_search_file = re.compile(r'^nginx-access-ui.log-\d{8}.gz$|^nginx-access-ui.log-\d{8}$')
    re_get_date = re.compile(r'\d{4}\d{2}\d{2}')
    try:
        for file in os.listdir(log_dir):
            match_file = re_search_file.search(file)
            if match_file:
                match_date = re.search(re_get_date, file)
                date = datetime.datetime.strptime(match_date.group(), '%Y%m%d').date()
                if last_date is None:
                    last_date = date
                    last_file_name = file
                if last_date < date:
                    last_date = date
                    last_file_name = file
        return LastFileData(last_file_name, last_date)
    except Exception as error:
        logging.info('Ошибка поиска файла: {}'.format(error))
        return LastFileData(None, None)


def parse_file(file_path: Path) -> Dict[str, Union[Dict[str, list], int, float]]:
    """
    Читаем файл, собирая информацию по времени выполнения в разрезе каждого URL
    :param file_path: путь до файла который будем анализировать
    :type file_path: Path
    :return: возвращаем словарь с параметрами
    :rtype: Dict[str, Union[Dict[str, list], int, float]]
    """
    all_count = 0
    all_sum = 0
    err_count = 0
    parsed_dict = dict()

    if file_path.match('*.gz'):
        file = gzip.open(file_path, 'rb')
    else:
        file = open(file_path, 'rb')

    re_url = re.compile(r'GET (.+?) HTTP')
    re_timedata = re.compile(r'\d+[.]\d*$')

    open_file_gen = (st for st in file)

    for all_count, item in enumerate(open_file_gen, start=1):
        item = item.decode('UTF-8')
        try:
            url = re.search(re_url, item).group(1)
            time_data = float(re.search(re_timedata, item).group())
            all_sum += time_data
            if url not in parsed_dict:
                parsed_dict[url] = dict(time_list=[])
            parsed_dict[url]['time_list'].append(time_data)
        except Exception:
            err_count += 1
            all_count -= 1
    file.close()
    parsed_data = {'parsed_dict': parsed_dict, 'all_count': all_count, 'all_sum': all_sum, 'err_count': err_count}
    return parsed_data


def enrich_log_data(parsed_data: Dict[str, Union[Dict[str, list], int, float]]) -> list:
    """
    Высчитываем и добавляем к словарю данные необходимые для отчёта
    :param parsed_data: словарь с полученными из файла данными
    :type parsed_data: Dict[str, Union[Dict[str, list], int, float]]
    :return: возвращаем лист готовый к дампу в json
    :rtype: list
    """

    for url_str, url_data in parsed_data['parsed_dict'].items():
        local_count = len(url_data['time_list'])
        local_sum = sum(url_data['time_list'])
        # Дополним словарь расчитанными для отчета данными
        url_data['count'] = local_count
        url_data['time_avg'] = round(local_sum / local_count, 3)
        url_data['time_max'] = round(max(url_data['time_list']), 3)
        url_data['time_sum'] = round(local_sum, 3)
        url_data['url'] = url_str
        url_data['time_med'] = round(median(url_data['time_list']), 3)
        url_data['time_perc'] = round(local_sum * 100 / parsed_data['all_sum'], 3)
        url_data['count_perc'] = round(local_count * 100 / parsed_data['all_count'], 3)
        # Удалим поле со списком который нам больше не пригодится
        del url_data['time_list']

    calculated_data = sorted(parsed_data['parsed_dict'].values(), key=lambda x: x['time_sum'], reverse=True)

    return calculated_data


def generate_json(data: list, max_size: int) -> str:
    """
    Отбираем не более максимального количества записей(указывается в настройках) и дампим json
    :param data: лист с исходными данными готовыми к дампу в json
    :type data: list
    :param max_size: максимальное количество записей
    :type max_size: int
    :return: возвращаем json готовый к вставке в отчёт
    :rtype: str
    """
    if max_size < len(data):
        data = data[0:max_size]
    return json.dumps(data)


def create_report(json_data: str, report_templ_path: str, target_report_path: Path) -> None:
    """
    Рендерим отчет по шаблону с полученными данными и размещаем результат в указанной дирректории
    :param json_data: json готовый к вставке в отчёт
    :type json_data: str
    :param report_templ_path: путь до файла шаблона
    :type report_templ_path: str
    :param target_report_path: путь для размещения результирующего отчета
    :type target_report_path: Path
    :return: None
    """

    with open(report_templ_path, 'r') as report_template:
        readed_templ = string.Template(report_template.read())

    rendered_report = readed_templ.safe_substitute(table_json=json_data)

    if not target_report_path.parent.exists():
        target_report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(target_report_path, 'w') as result_report:
        result_report.write(rendered_report)
        result_report.close()


if __name__ == '__main__':
    # Обработаем полученные параметры(в частности путь до файла настрокйи)
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', type=str, dest='conf_path', default='./config.ini')
    args = arg_parser.parse_args()

    # Если не нашли файл настройки, то как по требованиям взрываемся ошибкой
    if os.path.exists(args.conf_path):
        main(args.conf_path)
    else:
        raise ValueError('Файл настройки {} не найден'.format(args.conf_path))
